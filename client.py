"""Host command-line client. Run python client.py --help for examples."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


def positive_id(value):
    item_id = int(value)
    if item_id < 1:
        raise argparse.ArgumentTypeError("book ID must be positive")
    return item_id


def main():
    parser = argparse.ArgumentParser(description="Send requests to the Bazar Frontend API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000",
                        help="Frontend URL (default: http://127.0.0.1:5000)")
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Find books by topic")
    search.add_argument("topic", help='Use quotes around a topic with spaces')
    info = commands.add_parser("info", help="Show a book's details")
    info.add_argument("item_id", type=positive_id)
    purchase = commands.add_parser("purchase", help="Buy one copy of a book")
    purchase.add_argument("item_id", type=positive_id)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        parser.error("--base-url must be an http or https URL")

    method = "POST" if args.command == "purchase" else "GET"
    argument = quote(args.topic, safe="") if args.command == "search" else str(args.item_id)
    req = Request(f"{base_url}/{args.command}/{argument}", method=method,
                  headers={"Accept": "application/json"})
    try:
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            status = response.status
            payload = json.load(response)
    except (ValueError, UnicodeError):
        print("Error: server returned invalid JSON.", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, OSError):
        print("Error: cannot reach Frontend or request timed out.", file=sys.stderr)
        if args.command == "purchase":
            print("Purchase outcome may be unknown; do not retry automatically.", file=sys.stderr)
        return 1

    if not 200 <= status < 300:
        message = payload.get("error", payload) if isinstance(payload, dict) else payload
        print(f"Error (HTTP {status}): {message}", file=sys.stderr)
        if args.command == "purchase" and status >= 500:
            print("Purchase outcome may be unknown; do not retry automatically.", file=sys.stderr)
        return 1

    try:
        if args.command == "search":
            if not isinstance(payload, list):
                raise ValueError("Expected a list of books")
            lines = [f"{book['id']}: {book['title']}" for book in payload]
            print("Books found:" if lines else "No books found.")
            for line in lines:
                print(line)
        elif args.command == "info":
            text = (f"Book {payload['id']}: {payload['title']}\n"
                    f"Topic: {payload['topic']}\n"
                    f"Price: {payload['price']:.2f}\n"
                    f"Stock: {payload['quantity']}")
            print(text)
        else:
            # Print the lab's required wording, regardless of Order's message text.
            title, order_id = payload["title"], payload["order_id"]
            if status != 201 or not isinstance(title, str) or not title:
                raise ValueError("Invalid purchase receipt")
            print(f"bought book {title}")
            print(f"Order ID: {order_id}")
    except (KeyError, TypeError, ValueError):
        print("Error: server response does not match the expected API.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
