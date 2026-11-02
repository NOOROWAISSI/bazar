"""Persistent catalog. Conditional stock updates serialize competing purchases."""
import os
from contextlib import contextmanager
import sqlite3
from pathlib import Path
from flask import request, abort
from common import application

DB = os.environ.get('CATALOG_DB', 'data/catalog.db')
Path(DB).parent.mkdir(parents=True, exist_ok=True)
@contextmanager
def connect():
    """Commit or roll back each transaction, then release its file handle."""
    db = sqlite3.connect(DB, timeout=15)
    try:
        with db:
            yield db
    finally:
        db.close()

with connect() as db:
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY, title TEXT, topic TEXT, quantity INTEGER CHECK(quantity>=0), price_cents INTEGER CHECK(price_cents>=0))')
    db.executemany('INSERT OR IGNORE INTO books VALUES (?,?,?,?,?)', [
        (1, 'How to get a good grade in DOS in 40 minutes a day.', 'distributed systems', 10, 4000),
        (2, 'RPCs for Noobs.', 'distributed systems', 10, 5000),
        (3, 'Xen and the Art of Surviving Undergraduate School.', 'undergraduate school', 10, 3500),
        (4, 'Cooking for the Impatient Undergrad.', 'undergraduate school', 10, 2500)])

app = application('catalog')
def book(item):
    with connect() as db:
        row = db.execute('SELECT * FROM books WHERE id=?', (item,)).fetchone()
    if row is None:
        abort(404, 'Unknown item')
    return dict(id=row[0], title=row[1], topic=row[2], quantity=row[3], price=row[4]/100)

@app.get('/search/<path:topic>')
@app.get('/query/topic/<path:topic>')
def search(topic):
    with connect() as db:
        rows = db.execute('SELECT id,title FROM books WHERE lower(topic)=lower(?) ORDER BY id', (topic,)).fetchall()
    return [dict(id=r[0], title=r[1]) for r in rows]

@app.get('/info/<int:item>')
@app.get('/query/item/<int:item>')
def info(item):
    return book(item)

@app.patch('/update/<int:item>')
def update(item):
    from decimal import Decimal, InvalidOperation
    data = request.get_json()
    if not isinstance(data, dict) or not data or set(data)-{'stock_delta', 'price'}:
        abort(400, 'Provide stock_delta and/or price')
    delta = data.get('stock_delta', 0)
    if type(delta) is not int or abs(delta) > 1000000000:
        abort(400, 'stock_delta must be an integer between -1000000000 and 1000000000')
    cents = None
    if 'price' in data:
        try:
            value = Decimal(str(data['price'])) * 100
            if not value.is_finite() or value < 0 or value != value.to_integral_value() or value > 100000000:
                raise ValueError()
            cents = int(value)
        except (InvalidOperation, ValueError):
            abort(400, 'price must be nonnegative with at most two decimal places')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT quantity FROM books WHERE id=?', (item,)).fetchone()
        if row is None:
            abort(404, 'Unknown item')
        if row[0]+delta > 1000000000:
            abort(400, 'Stock limit exceeded')
        if row[0]+delta < 0:
            abort(409, 'Out of stock')
        db.execute('UPDATE books SET quantity=quantity+?, price_cents=COALESCE(?,price_cents) WHERE id=?', (delta,cents,item))
    return book(item)
