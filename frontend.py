"""Public REST gateway; all service calls cross HTTP boundaries."""
import os
from urllib.parse import quote
from common import application, call
app = application('frontend')
CATALOG = os.environ.get('CATALOG_URL', 'http://127.0.0.1:5001')
ORDER = os.environ.get('ORDER_URL', 'http://127.0.0.1:5002')

@app.get('/search/<path:topic>')
def search(topic):
    return call(CATALOG+'/search/'+quote(topic, safe=''))

@app.get('/info/<int:item>')
def info(item):
    return call(f'{CATALOG}/info/{item}')

@app.post('/purchase/<int:item>')
def purchase(item):
    return call(f'{ORDER}/purchase/{item}', 'POST', {})
