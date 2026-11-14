"""REST gateway: route user requests to Catalog or Order over HTTP."""

import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


app = Flask(__name__)
app.logger.setLevel(logging.INFO)
CATALOG_URL = os.environ.get("CATALOG_URL", "http://127.0.0.1:5001").rstrip("/")
ORDER_URL = os.environ.get("ORDER_URL", "http://127.0.0.1:5002").rstrip("/")


def forward_request(url, method="GET"):
    """Forward once, preserving JSON and status; never retry a purchase."""
    upstream_request = Request(url, method=method, headers={"Accept": "application/json"})
    try:
        try:
            response = urlopen(upstream_request, timeout=5)
        except HTTPError as error:
            # A 404 or 409 is a valid backend result, not a connection failure.
            response = error
        with response:
            payload = json.load(response)
            return jsonify(payload), response.status
    except (ValueError, UnicodeError):
        return jsonify(error="Backend returned an invalid JSON response"), 502
    except (URLError, TimeoutError, OSError):
        return jsonify(
            error="Backend service unavailable. A purchase outcome may be unknown; do not retry automatically."
        ), 503


@app.get("/search/<topic>")
def search(topic):
    # Encode spaces and other URL characters before contacting Catalog.
    return forward_request(CATALOG_URL + "/query/topic/" + quote(topic, safe=""))


@app.get("/info/<int:item_id>")
def info(item_id):
    return forward_request(f"{CATALOG_URL}/query/item/{item_id}")


@app.post("/purchase/<int:item_id>")
def purchase(item_id):
    return forward_request(f"{ORDER_URL}/purchase/{item_id}", method="POST")


@app.errorhandler(HTTPException)
def json_error(error):
    return jsonify(error=error.description), error.code


@app.after_request
def log_request(response):
    app.logger.info("%s %s -> %s", request.method, request.path, response.status_code)
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
