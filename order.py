"""Order service: query catalog, atomically decrement, persist receipt."""
import os
from contextlib import closing
import sqlite3
import logging
from pathlib import Path
from common import application, call

CATALOG = os.environ.get('CATALOG_URL', 'http://127.0.0.1:5001')
DB = os.environ.get('ORDER_DB', 'data/orders.db')
Path(DB).parent.mkdir(parents=True, exist_ok=True)
with closing(sqlite3.connect(DB)) as db:
    db.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, item INTEGER, title TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
app = application('order')

@app.post('/purchase/<int:item>')
def purchase(item):
    details, status = call(f'{CATALOG}/info/{item}')
    if status != 200:
        return details, status
    if details['quantity'] <= 0:
        return {'error': 'Out of stock'}, 409
    result, status = call(f'{CATALOG}/update/{item}', 'PATCH', {'stock_delta': -1})
    if status != 200:
        return result, status
    try:
        with closing(sqlite3.connect(DB, timeout=15)) as db, db:
            cur = db.execute('INSERT INTO orders(item,title) VALUES (?,?)', (item,details['title']))
            receipt = cur.lastrowid
    except sqlite3.Error:
        logging.exception('Stock decremented but order write failed for item %s; reconciliation required', item)
        return {'error': 'Order recording failed; manual reconciliation required. Do not retry.'}, 503
    logging.info('bought book %s', details['title'])
    return {'order_id': receipt, 'item': item, 'title': details['title'], 'message': 'bought book '+details['title']}, 201
