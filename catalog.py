"""Step 1: create and seed the bookstore's persistent catalog."""

import sqlite3
from contextlib import closing
from pathlib import Path


# Resolve relative to this file so running from another folder uses the same DB.
DATABASE_PATH = Path(__file__).resolve().parent / "data" / "catalog.db"

# Initial quantities and prices are sample choices; the lab does not fix them.
# Store money in integer cents: 4000 cents means a price of 40.00.
BOOKS = [
    (1, "How to get a good grade in DOS in 40 minutes a day.", "distributed systems", 4000, 10),
    (2, "RPCs for Noobs.", "distributed systems", 5000, 10),
    (3, "Xen and the Art of Surviving Undergraduate School.", "undergraduate school", 3500, 10),
    (4, "Cooking for the Impatient Undergrad.", "undergraduate school", 2500, 10),
]


def initialize_database():
    """Create missing storage and insert books without resetting existing data."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # closing releases the file handle; 'with connection' commits or rolls back.
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
                    quantity INTEGER NOT NULL CHECK (quantity >= 0)
                )
            """)

            # Each ID is unique. Existing books keep their current price/stock.
            connection.executemany("""
                INSERT OR IGNORE INTO books
                    (id, title, topic, price_cents, quantity)
                VALUES (?, ?, ?, ?, ?)
            """, BOOKS)


if __name__ == "__main__":
    initialize_database()
    print(f"Catalog database ready: {DATABASE_PATH}")
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        books = connection.execute(
            "SELECT id, title, topic, price_cents, quantity FROM books ORDER BY id"
        ).fetchall()

    for book_id, title, topic, price_cents, quantity in books:
        print(f"{book_id}. {title}")
        print(f"   Topic: {topic} | Price: {price_cents / 100:.2f} | Stock: {quantity}")
