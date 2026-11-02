"""Shared HTTP transport and JSON error handling."""
import json
import logging
import urllib.request
import urllib.error
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def application(name):
    app = Flask(name)
    @app.errorhandler(HTTPException)
    def error(exc):
        return jsonify(error=exc.description), exc.code
    @app.get('/health')
    def health():
        return jsonify(status='ok', service=name)
    @app.after_request
    def log(response):
        from flask import request
        logging.info('%s %s %s -> %s', name, request.method, request.path, response.status_code)
        return response
    return app

def call(url, method='GET', data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response), response.status
    except urllib.error.HTTPError as exc:
        return json.load(exc), exc.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return {'error': 'Upstream service unavailable; do not blindly retry a purchase.'}, 503
