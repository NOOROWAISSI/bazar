# Bazar.com

Distributed and Operating Systems - Lab 1
Noor and Sara

A small bookstore with three services:
- Catalog stores the four books, prices and stock.
- Order handles purchases and saves orders.
- Frontend receives requests and sends them to Catalog or Order.

The services use Flask, HTTP/JSON and SQLite. There is no GUI.

## Run

Install Docker Desktop with Linux containers, then run:

```powershell
git clone https://github.com/NOOROWAISSI/bazar.git
cd bazar
docker compose up --build -d --wait
```

Frontend runs at http://127.0.0.1:5000. To use the client on your computer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe client.py search "distributed systems"
.\.venv\Scripts\python.exe client.py info 2
.\.venv\Scripts\python.exe client.py purchase 2
```

A purchase buys one copy. If port 5000 is busy, set `$env:FRONTEND_PORT = '5050'` before starting Compose and add `--base-url http://127.0.0.1:5050` before the client command.

## API

| Service | Request |
| --- | --- |
| Frontend | GET /search/<topic> |
| Frontend | GET /info/<id> |
| Frontend | POST /purchase/<id> |
| Catalog | GET /query/topic/<topic> |
| Catalog | GET /query/item/<id> |
| Catalog | PATCH /update/<id> |
| Order | POST /purchase/<id> |

Catalog updates accept `{"stock_delta": 5}` to add stock, `{"stock_delta": -1}` to remove a copy, or `{"price": 45}` to change the price. Catalog and Order are internal to Docker. For example, restock from the Catalog container:

```powershell
docker compose exec catalog python -c "import json,urllib.request; r=urllib.request.Request('http://127.0.0.1:5001/update/2',data=json.dumps({'stock_delta':5}).encode(),method='PATCH',headers={'Content-Type':'application/json'}); print(urllib.request.urlopen(r).read().decode())"
```

A missing book returns 404, insufficient stock returns 409, and invalid update data returns 400.

## Tests and files

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

There are 23 tests. `verify_docker.py` also checks the real services, concurrent purchases and saved data in temporary containers. Detailed test files go into the ignored `.verification` directory.

The [report](docs/design.pdf) explains the design and limitations. [output.txt](docs/output.txt) contains actual client output, sample service logs and test results.

To see logs, run `docker compose logs --no-color`. To stop, run `docker compose down`. Data stays in named volumes. Adding `-v` deletes both databases, so only use it for an intentional reset.

Stock updates are protected against concurrent requests. A crash between reducing stock and saving an order may still need manual checking; the report explains this case.
