import importlib
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from unittest.mock import patch

from flask import Flask, jsonify, request
from werkzeug.serving import make_server


def create_catalog_mock(books):
    catalog = Flask("order_test_catalog")

    @catalog.get("/query/item/<int:item_id>")
    def get_book(item_id):
        book = books.get(item_id)
        if book is None:
            return jsonify(error="Book not found"), 404
        return jsonify(id=item_id, title=book["title"], price=book["price"])

    @catalog.patch("/update/<int:item_id>")
    def update_book(item_id):
        book = books.get(item_id)
        if book is None:
            return jsonify(error="Book not found"), 404

        payload = request.get_json()
        stock_delta = payload.get("stock_delta") if payload else None
        if not isinstance(stock_delta, int) or isinstance(stock_delta, bool):
            return jsonify(error="Invalid stock delta"), 400

        updated_quantity = book["quantity"] + stock_delta
        if updated_quantity < 0:
            return jsonify(error="Insufficient stock"), 409

        book["quantity"] = updated_quantity
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
        catalog = create_catalog_mock(self.books)
        self.catalog_server = make_server("127.0.0.1", 0, catalog)
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


if __name__ == "__main__":
    unittest.main()
