"""Run: python verify_noor.py. Tests Noor's services, not Sara's real Order.

Uses random local ports and a disposable database. Normal inventory is untouched.
An explicit Order test double checks gateway routing, not purchase correctness.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
import json
import logging
from pathlib import Path
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from flask import Flask, jsonify
from werkzeug.serving import make_server

import catalog
import frontend


@contextmanager
def running_server(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
        if thread.is_alive():
            raise RuntimeError("Test server did not stop")


def call(base, path, method="GET", data=None):
    body = None if data is None else json.dumps(data).encode()
    req = Request(base + path, data=body, method=method,
                  headers={"Content-Type": "application/json"})
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        if response.headers.get_content_type() != "application/json":
            raise AssertionError("Expected JSON: " + path)
        return response.status, json.load(response)


def expect(base, path, status=200, method="GET", data=None):
    actual, payload = call(base, path, method, data)
    if actual != status:
        raise AssertionError((path, actual, payload))
    print(method, path, "->", actual, json.dumps(payload, sort_keys=True))
    return payload


def main():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    frontend.app.logger.setLevel(logging.ERROR)
    original = catalog.DATABASE_PATH, frontend.CATALOG_URL, frontend.ORDER_URL
    try:
        with tempfile.TemporaryDirectory() as temp:
            catalog.DATABASE_PATH = Path(temp) / "catalog.db"
            catalog.initialize_database()
            order_double = Flask("order_test_double")
            order_calls = []

            @order_double.post("/purchase/<int:item>")
            def fake_purchase(item):
                order_calls.append(item)
                if item == 3:
                    return jsonify(error="Out of stock"), 409
                if item == 999:
                    return jsonify(error="Book not found"), 404
                if item == 4:
                    return "invalid JSON", 200
                return jsonify(order_id=1, item=item,
                               message="Test Order double: no real purchase recorded"), 201

            with ExitStack() as servers:
                catalog_url = servers.enter_context(running_server(catalog.app))
                order_url = servers.enter_context(running_server(order_double))
                frontend.CATALOG_URL, frontend.ORDER_URL = catalog_url, order_url
                gateway = servers.enter_context(running_server(frontend.app))

                for topic, ids in [("distributed%20systems", [1, 2]),
                                   ("undergraduate%20school", [3, 4]),
                                   ("DISTRIBUTED%20SYSTEMS", [1, 2]), ("unknown", [])]:
                    books = expect(gateway, "/search/" + topic)
                    assert [b["id"] for b in books] == ids
                for item in range(1, 5):
                    assert expect(gateway, f"/info/{item}")["id"] == item
                expect(gateway, "/info/999", 404)

                book = expect(catalog_url, "/update/2", method="PATCH",
                              data={"stock_delta": 5, "price": 42.75})
                assert book["quantity"] == 15 and book["price"] == 42.75
                expect(catalog_url, "/update/2", 409, "PATCH",
                       {"stock_delta": -99, "price": 1})
                assert expect(gateway, "/info/2") == book
                for invalid in [{}, {"stock_delta": True}, {"stock_delta": 1.5},
                                {"price": -1}, {"price": 1.001}, {"price": "45"},
                                {"unexpected": 1}, {"stock_delta": 10**100}]:
                    expect(catalog_url, "/update/2", 400, "PATCH", invalid)
                expect(catalog_url, "/update/999", 404, "PATCH", {"stock_delta": 1})

                with ThreadPoolExecutor(max_workers=20) as pool:
                    results = list(pool.map(
                        lambda _: call(catalog_url, "/update/1", "PATCH", {"stock_delta": -1}),
                        range(30)))
                successes = sum(status == 200 for status, _ in results)
                conflicts = sum(status == 409 for status, _ in results)
                assert (successes, conflicts) == (10, 20)
                assert expect(gateway, "/info/1")["quantity"] == 0
                print("PASS: thirty concurrent stock decrements: ten successes, twenty conflicts")
                catalog.initialize_database()
                assert expect(gateway, "/info/1")["quantity"] == 0
                assert expect(gateway, "/info/2") == book
                print("PASS: initialization preserves saved stock and price")

                print("Order test double below checks routing only; Sara's real Order is pending.")
                for item, status in [(2, 201), (3, 409), (999, 404), (4, 502)]:
                    expect(gateway, f"/purchase/{item}", status, "POST")
                assert order_calls == [2, 3, 999, 4]
                assert expect(gateway, "/info/2") == book
                expect(gateway, "/purchase/2", 405)
                expect(gateway, "/missing", 404)

                # Close each backend before checking connection-failure responses.
                servers.close()
                with running_server(frontend.app) as isolated_gateway:
                    expect(isolated_gateway, "/info/2", 503)
                    expect(isolated_gateway, "/purchase/2", 503, "POST")
            print("PASS: all Catalog/Frontend checks; normal inventory unchanged.")
    finally:
        catalog.DATABASE_PATH, frontend.CATALOG_URL, frontend.ORDER_URL = original


if __name__ == "__main__":
    main()
