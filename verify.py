"""Integration test: three real HTTP processes, isolated SQLite databases."""
import concurrent.futures
from contextlib import contextmanager, closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from common import call

@contextmanager
def temporary_databases():
    # Windows virus scanners may briefly retain a recently closed SQLite file.
    directory = tempfile.TemporaryDirectory()
    try:
        yield directory.name
    finally:
        for attempt in range(30):
            try:
                directory.cleanup()
                break
            except PermissionError:
                if attempt == 29:
                    raise
                time.sleep(0.1)


def main():
    processes = []
    ports = {'catalog': 15501, 'order': 15502, 'frontend': 15500}
    root = Path(__file__).resolve().parent
    with temporary_databases() as temp:
        env = dict(os.environ, CATALOG_DB=temp+'/catalog.db', ORDER_DB=temp+'/orders.db',
                   CATALOG_URL='http://127.0.0.1:15501', ORDER_URL='http://127.0.0.1:15502')
        log = open(root/'docs/service-output.txt', 'w', encoding='utf-8')
        def start(name):
            p = subprocess.Popen([sys.executable,'-m','waitress',f'--listen=127.0.0.1:{ports[name]}', '--threads=8',name+':app'], cwd=root,env=env,stdout=log,stderr=log)
            processes.append(p)
            for _ in range(100):
                if p.poll() is not None:
                    raise RuntimeError(name+' failed to start')
                if call(f'http://127.0.0.1:{ports[name]}/health')[1] == 200:
                    return p
                time.sleep(.1)
            raise RuntimeError(name+' startup timeout')
        def check(path, status=200, method='GET', data=None, catalog=False):
            result, code = call(('http://127.0.0.1:15501' if catalog else 'http://127.0.0.1:15500')+path,method,data)
            print(method,path,'->',code, json.dumps(result,indent=2))
            assert code == status, (code,result)
            return result
        try:
            start('catalog'); start('order'); start('frontend')
            assert len(check('/search/distributed%20systems')) == 2
            assert len(check('/search/undergraduate%20school')) == 2
            assert check('/search/unknown') == []
            assert check('/info/2')['quantity'] == 10
            assert 'bought book' in check('/purchase/2',201,'POST')['message']
            assert check('/info/2')['quantity'] == 9
            check('/info/99',404)
            check('/purchase/99',404,'POST')
            check('/update/2',400,'PATCH',{'stock_delta':1.5},True)
            check('/update/2',400,'PATCH',{'price':-1},True)
            check('/update/2',400,'PATCH',{'stock_delta':10**100},True)
            check('/update/2',400,'PATCH',{'stock_delta':True},True)
            check('/update/2',400,'PATCH',{'price':1.001},True)
            check('/update/2',400,'PATCH',{'unexpected':1},True)
            check('/update/2',409,'PATCH',{'stock_delta':-100},True)
            assert check('/update/2',200,'PATCH',{'stock_delta':3,'price':42.75},True)['quantity'] == 12
            assert check('/info/2')['price'] == 42.75
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
                results = list(pool.map(lambda _: call('http://127.0.0.1:15500/purchase/1','POST'), range(30)))
            successes = sum(status==201 for _,status in results)
            conflicts = sum(status==409 for _,status in results)
            print(f'Concurrency: 30 requests, {successes} purchases, {conflicts} out-of-stock responses')
            assert (successes, conflicts) == (10,20)
            assert check('/info/1')['quantity'] == 0
            check('/purchase/1',409,'POST')
            processes[0].terminate(); processes[0].wait()
            start('catalog')
            assert check('/info/1')['quantity'] == 0
            assert check('/info/2')['price'] == 42.75
            processes[1].terminate(); processes[1].wait()
            start('order')
            with closing(sqlite3.connect(temp+'/orders.db')) as db:
                count = db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
            assert count == 11
            print('Restart persistence: stock, price and 11 order records preserved')
            processes[-1].terminate(); processes[-1].wait()
            check('/purchase/2',503,'POST')
            print('PASS: search, info, purchase, stock/price updates, validation, concurrent stock safety, persistence, unavailable upstream')
        finally:
            for p in processes:
                if p.poll() is None:
                    p.terminate(); p.wait()
            log.close()

if __name__ == '__main__':
    main()
