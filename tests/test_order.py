import importlib
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from unittest.mock import patch

import requests

from flask import Flask, jsonify, request
from werkzeug.serving import make_server


def create_catalog_mock(books, patch_requests, patch_applied):
    catalog = Flask("order_test_catalog")
    state_lock = threading.Lock()

    @catalog.get("/query/item/<int:item_id>")
    def get_book(item_id):
        with state_lock:
            book = books.get(item_id)
            book = dict(book) if book is not None else None
        if book is None:
            return jsonify(error="Book not found"), 404
        if book.get("get_delay"):
            time.sleep(book["get_delay"])
        if book.get("get_status", 200) != 200:
            return jsonify(error="Catalog test response"), book["get_status"]
        return jsonify(id=item_id, title=book["title"], price=book["price"])

    @catalog.patch("/update/<int:item_id>")
    def update_book(item_id):
        payload = request.get_json()
        stock_delta = payload.get("stock_delta") if payload else None
        if not isinstance(stock_delta, int) or isinstance(stock_delta, bool):
            return jsonify(error="Invalid stock delta"), 400

        with state_lock:
            patch_requests.append((item_id, payload))
            book = books.get(item_id)
            if book is None:
                return jsonify(error="Book not found"), 404
            patch_status = (
                book.get("restore_status", book.get("patch_status", 200))
                if stock_delta > 0
                else book.get("patch_status", 200)
            )
            if patch_status != 200:
                return jsonify(error="Catalog test response"), patch_status

            updated_quantity = book["quantity"] + stock_delta
            if updated_quantity < 0:
                return jsonify(error="Insufficient stock"), 409

            book["quantity"] = updated_quantity
            patch_delay = book.get("patch_delay", 0)
            patch_applied.set()

        if patch_delay:
            time.sleep(patch_delay)
        return jsonify(id=item_id, quantity=updated_quantity)

    return catalog


class OrderServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(
            self.temporary_directory.name, "orders.sqlite3"
        )
        self.books = {
            7: {"title": "Test Book", "price": 12.5, "quantity": 1},
        }
        self.patch_requests = []
        self.patch_applied = threading.Event()
        catalog = create_catalog_mock(
            self.books, self.patch_requests, self.patch_applied
        )
        self.catalog_server = make_server(
            "127.0.0.1", 0, catalog, threaded=True
        )
        self.catalog_thread = threading.Thread(
            target=self.catalog_server.serve_forever, daemon=True
        )
        self.catalog_thread.start()

        self.environment = patch.dict(
            os.environ,
            {
                "ORDER_DATABASE_PATH": self.database_path,
                "CATALOG_URL": (
                    f"http://127.0.0.1:{self.catalog_server.server_port}"
                ),
            },
        )
        self.environment.start()
        self.service = importlib.import_module("order")
        self.service = importlib.reload(self.service)
        self.client = self.service.app.test_client()

    def tearDown(self):
        self.catalog_server.shutdown()
        self.catalog_thread.join()
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_successful_purchase_returns_http_201(self):
        response = self.client.post("/purchase/7")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["title"], "Test Book")
        self.assertEqual(self.books[7]["quantity"], 0)

    def test_nonexistent_book_returns_http_404(self):
        response = self.client.post("/purchase/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.books[7]["quantity"], 1)

    def test_out_of_stock_book_returns_http_409(self):
        self.books[7]["quantity"] = 0

        response = self.client.post("/purchase/7")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.books[7]["quantity"], 0)

    def test_purchasing_never_makes_stock_negative(self):
        first_response = self.client.post("/purchase/7")
        second_response = self.client.post("/purchase/7")

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(self.books[7]["quantity"], 0)
        self.assertGreaterEqual(self.books[7]["quantity"], 0)

    def test_successful_order_is_saved_in_sqlite(self):
        response = self.client.post("/purchase/7")
        order_id = response.get_json()["order_id"]

        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT id, item_id, title, price FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(row, (order_id, 7, "Test Book", 12.5))

    def test_order_persists_after_service_restart(self):
        response = self.client.post("/purchase/7")
        order_id = response.get_json()["order_id"]

        self.service = importlib.reload(self.service)

        with closing(sqlite3.connect(self.service.DATABASE_PATH)) as connection:
            row = connection.execute(
                "SELECT id, item_id, title, price FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()

        self.assertEqual(row, (order_id, 7, "Test Book", 12.5))

    def test_concurrent_purchases_never_exceed_available_stock(self):
        self.books[7]["quantity"] = 4
        request_count = 12
        start_requests = threading.Barrier(request_count)

        def purchase():
            with self.service.app.test_client() as client:
                start_requests.wait()
                return client.post("/purchase/7")

        with ThreadPoolExecutor(max_workers=request_count) as executor:
            responses = list(executor.map(lambda _: purchase(), range(request_count)))

        successful_responses = [
            response for response in responses if response.status_code == 201
        ]
        self.assertEqual(len(successful_responses), 4)
        self.assertEqual(
            sum(response.status_code == 409 for response in responses), 8
        )
        self.assertEqual(self.books[7]["quantity"], 0)
        self.assertGreaterEqual(self.books[7]["quantity"], 0)
        successful_order_ids = {
            response.get_json()["order_id"] for response in successful_responses
        }
        self.assertEqual(len(successful_order_ids), len(successful_responses))

        with closing(sqlite3.connect(self.database_path)) as connection:
            saved_order_ids = {
                row[0] for row in connection.execute("SELECT id FROM orders")
            }

        self.assertEqual(saved_order_ids, successful_order_ids)

    def test_catalog_connection_failure_returns_503(self):
        with patch.object(
            self.service.requests,
            "get",
            side_effect=requests.ConnectionError("connection refused"),
        ):
            response = self.client.post("/purchase/7")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Catalog service unavailable", response.get_json()["error"])
        self.assertEqual(self.books[7]["quantity"], 1)

    def test_catalog_timeout_before_book_response_returns_503(self):
        self.books[7]["get_delay"] = 0.2
        self.service.CATALOG_TIMEOUT = (0.05, 0.05)

        response = self.client.post("/purchase/7")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Catalog service unavailable", response.get_json()["error"])
        self.assertEqual(self.books[7]["quantity"], 1)

    def test_catalog_timeout_during_stock_update_returns_unknown_outcome(self):
        self.books[7]["patch_delay"] = 0.2
        self.service.CATALOG_TIMEOUT = (0.05, 0.05)

        response = self.client.post("/purchase/7")

        self.assertTrue(self.patch_applied.wait(timeout=1))
        self.assertEqual(response.status_code, 503)
        self.assertIn("outcome is unknown", response.get_json()["error"])
        self.assertEqual(self.books[7]["quantity"], 0)

    def test_unexpected_catalog_book_response_returns_502(self):
        self.books[7]["get_status"] = 503

        response = self.client.post("/purchase/7")

        self.assertEqual(response.status_code, 502)
        self.assertIn("unexpected response", response.get_json()["error"])
        self.assertEqual(self.books[7]["quantity"], 1)

    def test_unexpected_catalog_stock_response_returns_502(self):
        self.books[7]["patch_status"] = 500

        response = self.client.post("/purchase/7")

        self.assertEqual(response.status_code, 502)
        self.assertIn("outcome may be unknown", response.get_json()["error"])
        self.assertEqual(self.books[7]["quantity"], 1)

    def test_failed_order_insert_attempts_stock_compensation(self):
        class FailingConnection:
            def __enter__(self):
                return self

            def __exit__(self, exception_type, exception, traceback):
                return False

            def execute(self, *_args):
                raise sqlite3.OperationalError("simulated insert failure")

            def close(self):
                pass

        with patch.object(
            self.service.sqlite3, "connect", return_value=FailingConnection()
        ):
            response = self.client.post("/purchase/7")

        self.assertEqual(response.status_code, 500)
        self.assertIn("stock was restored", response.get_json()["error"])
        self.assertNotIn("order_id", response.get_json())
        self.assertEqual(
            self.patch_requests,
            [(7, {"stock_delta": -1}), (7, {"stock_delta": 1})],
        )
        self.assertEqual(self.books[7]["quantity"], 1)

        with closing(sqlite3.connect(self.database_path)) as connection:
            order_count = connection.execute(
                "SELECT COUNT(*) FROM orders"
            ).fetchone()[0]
        self.assertEqual(order_count, 0)

    def test_failed_stock_compensation_returns_clear_error(self):
        class FailingConnection:
            def __enter__(self):
                return self

            def __exit__(self, exception_type, exception, traceback):
                return False

            def execute(self, *_args):
                raise sqlite3.OperationalError("simulated insert failure")

            def close(self):
                pass

        self.books[7]["restore_status"] = 500
        with patch.object(
            self.service.sqlite3, "connect", return_value=FailingConnection()
        ):
            response = self.client.post("/purchase/7")

        self.assertEqual(response.status_code, 500)
        self.assertIn("stock restoration failed", response.get_json()["error"])
        self.assertIn("compensation_error", response.get_json())
        self.assertNotIn("order_id", response.get_json())
        self.assertEqual(self.books[7]["quantity"], 0)
        self.assertEqual(
            self.patch_requests,
            [(7, {"stock_delta": -1}), (7, {"stock_delta": 1})],
        )


if __name__ == "__main__":
    unittest.main()
