"""Sara's isolated regression tests for Noor's host client implementation."""

import io
import json
import sys
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

import client


class FakeResponse(io.BytesIO):
    def __init__(self, payload, status=200):
        super().__init__(json.dumps(payload).encode("utf-8"))
        self.status = status


class ClientTests(unittest.TestCase):
    def run_client(self, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["client.py", *args]), \
             patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            result = client.main()
        return result, stdout.getvalue(), stderr.getvalue()

    def test_search_by_topic_encodes_topic_and_displays_books(self):
        with patch("client.urlopen", return_value=FakeResponse([
            {"id": 1, "title": "Distributed Systems"},
            {"id": 2, "title": "RPCs for Noobs"},
        ])) as open_url:
            result, stdout, stderr = self.run_client("search", "distributed systems")

        self.assertEqual(result, 0)
        self.assertIn("1: Distributed Systems", stdout)
        self.assertIn("2: RPCs for Noobs", stdout)
        self.assertEqual(stderr, "")
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:5000/search/distributed%20systems")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(open_url.call_args.kwargs["timeout"], 10)

    def test_book_information(self):
        book = {"id": 2, "title": "RPCs for Noobs", "topic": "distributed systems",
                "price": 50.0, "quantity": 10}
        with patch("client.urlopen", return_value=FakeResponse(book)):
            result, stdout, stderr = self.run_client("info", "2")

        self.assertEqual(result, 0)
        self.assertIn("Book 2: RPCs for Noobs", stdout)
        self.assertIn("Topic: distributed systems", stdout)
        self.assertIn("Price: 50.00", stdout)
        self.assertIn("Stock: 10", stdout)
        self.assertEqual(stderr, "")

    def test_successful_purchase_posts_and_displays_receipt(self):
        with patch("client.urlopen", return_value=FakeResponse(
                {"title": "RPCs for Noobs", "order_id": 42}, status=201)) as open_url:
            result, stdout, stderr = self.run_client("purchase", "2")

        self.assertEqual(result, 0)
        self.assertIn("bought book RPCs for Noobs", stdout)
        self.assertIn("Order ID: 42", stdout)
        self.assertEqual(stderr, "")
        self.assertEqual(open_url.call_args.args[0].get_method(), "POST")

    def test_http_error_statuses_are_reported(self):
        cases = ((404, {"error": "Book not found"}, "Book not found"),
                 (409, {"error": "Insufficient stock"}, "Insufficient stock"))
        for status, payload, message in cases:
            with self.subTest(status=status):
                error = HTTPError("http://127.0.0.1:5000/purchase/2", status,
                                  "error", {}, io.BytesIO(json.dumps(payload).encode()))
                with patch("client.urlopen", side_effect=error):
                    result, _stdout, stderr = self.run_client("purchase", "2")
                self.assertEqual(result, 1)
                self.assertIn(f"HTTP {status}", stderr)
                self.assertIn(message, stderr)

    def test_connection_failure_and_timeout_are_reported_without_retry(self):
        for failure in (URLError("connection refused"), TimeoutError("timed out")):
            with self.subTest(failure=type(failure).__name__):
                with patch("client.urlopen", side_effect=failure) as open_url:
                    result, _stdout, stderr = self.run_client("purchase", "2")
                self.assertEqual(result, 1)
                self.assertIn("cannot reach Frontend or request timed out", stderr)
                self.assertIn("outcome may be unknown", stderr)
                self.assertEqual(open_url.call_count, 1)

    def test_invalid_arguments_are_rejected_before_http_call(self):
        for args in (("info", "0"), ("purchase", "-1"), ("unknown",)):
            with self.subTest(args=args):
                with patch("client.urlopen") as open_url:
                    with patch.object(sys, "argv", ["client.py", *args]):
                        with self.assertRaises(SystemExit) as raised:
                            client.main()
                self.assertEqual(raised.exception.code, 2)
                open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
