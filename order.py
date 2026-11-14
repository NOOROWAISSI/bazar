"""Order service with persistent SQLite storage."""

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


DATABASE_PATH = Path(
    os.environ.get(
        "ORDER_DATABASE_PATH",
        Path(__file__).resolve().parent / "data" / "orders.db",
    )
)
CATALOG_URL = os.environ.get("CATALOG_URL", "http://127.0.0.1:5001").rstrip("/")
CATALOG_TIMEOUT = (3.05, 5)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)


@app.errorhandler(HTTPException)
def json_error(error):
    return jsonify(error=error.description), error.code


@app.after_request
def log_request(response):
    app.logger.info("%s %s -> %s", request.method, request.path, response.status_code)
    return response


def initialize_database():
    """Create the orders database and table when they do not exist."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(DATABASE_PATH, timeout=15)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    price REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/purchase/<int:item_id>")
def purchase(item_id):
    try:
        book_response = requests.get(
            f"{CATALOG_URL}/query/item/{item_id}", timeout=CATALOG_TIMEOUT
        )
    except requests.RequestException:
        return jsonify(error="Catalog service unavailable"), 503

    if book_response.status_code == 404:
        return jsonify(error="Book not found"), 404
    if book_response.status_code != 200:
        return jsonify(error="Catalog returned an unexpected response"), 502

    try:
        book = book_response.json()
        title = book["title"]
        price = book["price"]
        if (not isinstance(title, str) or not title
                or isinstance(price, bool) or not isinstance(price, (int, float))):
            raise ValueError("Invalid book details")
    except (ValueError, KeyError, TypeError):
        return jsonify(error="Catalog returned invalid book details"), 502

    try:
        reservation = requests.patch(
            f"{CATALOG_URL}/update/{item_id}",
            json={"stock_delta": -1},
            timeout=CATALOG_TIMEOUT,
        )
    except requests.RequestException:
        return jsonify(
            error="Catalog update outcome is unknown; do not retry automatically"
        ), 503

    if reservation.status_code == 409:
        return jsonify(error="Insufficient stock"), 409
    if reservation.status_code == 404:
        return jsonify(error="Book not found"), 404
    if reservation.status_code != 200:
        return jsonify(
            error="Catalog returned an unexpected response; purchase outcome may be unknown"
        ), 502

    try:
        with closing(sqlite3.connect(DATABASE_PATH, timeout=15)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO orders (item_id, title, price, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (item_id, title, price, datetime.now(timezone.utc).isoformat()),
                )
                order_id = cursor.lastrowid
    except sqlite3.Error:
        try:
            compensation = requests.patch(
                f"{CATALOG_URL}/update/{item_id}",
                json={"stock_delta": 1},
                timeout=CATALOG_TIMEOUT,
            )
            if compensation.status_code != 200:
                raise RuntimeError(f"Catalog returned HTTP {compensation.status_code}")
        except (requests.RequestException, RuntimeError) as error:
            return jsonify(
                error="Could not save the order and stock restoration failed",
                compensation_error=str(error),
            ), 500
        return jsonify(error="Could not save the order; stock was restored"), 500

    app.logger.info("bought book %s", title)
    return jsonify(
        order_id=order_id,
        item=item_id,
        title=title,
        message="bought book " + title,
    ), 201


initialize_database()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002)
