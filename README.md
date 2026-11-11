# Bazar.com - Distributed Bookstore

Three Python microservices communicate over HTTP REST and JSON: Frontend routes user requests, Catalog owns books and inventory, and Order records purchases. SQLite persists catalog and order data separately. A host command-line client prints readable results and `bought book book_name` on success.

The complete integrated project is on branch **noor**. Noor implemented Catalog/Frontend and the host client; Sara's Order service and tests are merged with their original commits preserved.

## Get the project

```powershell
git clone --branch noor https://github.com/NOOROWAISSI/bazar.git
cd bazar
```

## Run with Docker Compose

Start Docker Desktop with Linux containers, then run from the project directory:

```powershell
docker compose up --build -d --wait
docker compose ps
```

Only Frontend is published, at http://127.0.0.1:5000. Three containers run Waitress on 0.0.0.0 internally. Health checks order startup. Separate named volumes preserve the two databases.

If port 5000 is occupied, set another host port before starting:

```powershell
$env:FRONTEND_PORT = '5050'
docker compose up --build -d --wait
```

Use the corresponding port in client URLs. For stop/start without deleting data:

```powershell
docker compose down
docker compose up -d --wait
```

`down` preserves volumes. Adding `-v` deliberately deletes inventory and order history.

## Run the client on the host

Python 3.11 or newer is needed for the supplied host scripts. Use your full Python executable path for the first command if `python` is not on PATH. Activation is optional because the commands call the environment directly.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe client.py search "distributed systems"
.\.venv\Scripts\python.exe client.py search "undergraduate school"
.\.venv\Scripts\python.exe client.py info 2
.\.venv\Scripts\python.exe client.py purchase 2
```

Purchase buys one real copy. It is never run automatically. For a different host port:

```powershell
.\.venv\Scripts\python.exe client.py --base-url http://127.0.0.1:5050 info 2
```

Search displays book IDs and titles, info displays topic/price/quantity, and purchase prints the title and order ID. Unknown IDs produce 404, insufficient stock 409, and unavailable dependencies 503. A timeout can leave a purchase outcome unknown; the client does not automatically retry.

## REST contracts

| Service | Method and route | Purpose |
| --- | --- | --- |
| Frontend | GET /search/<topic> | Topic search through Catalog |
| Frontend | GET /info/<id> | Book details through Catalog |
| Frontend | POST /purchase/<id> | Purchase through Order |
| Catalog | GET /query/topic/<topic> | IDs and titles |
| Catalog | GET /query/item/<id> | id, title, topic, price, quantity |
| Catalog | PATCH /update/<id> | stock_delta and/or price |
| Order | POST /purchase/<id> | Decrement stock and persist receipt |
| Order | GET /health | Process availability |

Example browser request: http://127.0.0.1:5000/search/distributed%20systems. `%20` encodes a space. The root `/` has no GUI. Purchase requires POST; opening its URL in a browser sends GET and returns 405.

Catalog update accepts e.g. `{"stock_delta": 5, "price": 45}`. A delta changes stock rather than setting it. Prices are nonnegative JSON numbers with at most two decimal places. Stock deltas are integers. Invalid updates return JSON 400; rejected combined changes do not partially update the book.

Catalog is internal to Docker. To restock book 2:

```powershell
docker compose exec catalog python -c "import json,urllib.request; r=urllib.request.Request('http://127.0.0.1:5001/update/2',data=json.dumps({'stock_delta':5}).encode(),method='PATCH',headers={'Content-Type':'application/json'}); print(urllib.request.urlopen(r).read().decode())"
```

Restock explicitly when deliveries arrive; no artificial automatic stock source is assumed.

## Local three-process alternative

After installing requirements, open three terminals in this directory:

```powershell
# Terminal 1
.\.venv\Scripts\python.exe catalog.py
# Terminal 2
.\.venv\Scripts\python.exe order.py
# Terminal 3
.\.venv\Scripts\python.exe frontend.py
```

These entry points use Flask's local development server. Restart the affected service after code edits. Docker uses Waitress instead. Local databases live in data/catalog.db and data/orders.db; local and Docker data are independent.

Frontend reads CATALOG_URL and ORDER_URL at startup. Order reads CATALOG_URL and ORDER_DATABASE_PATH; Catalog reads CATALOG_DATABASE_PATH. Docker sets backend URLs to service names (`http://catalog:5001`, `http://order:5002`). To run across machines, use reachable addresses and a server binding such as `waitress-serve --listen=0.0.0.0:5001 catalog:app` after installing Waitress. Each backend owns its database; do not share SQLite files across hosts.

## Tests and actual output

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe verify_noor.py
.\.venv\Scripts\python.exe verify_docker.py
```

The last command requires running Docker. It builds copies of the current sources in a temporary context with a unique Compose project, random host port and disposable volumes. It runs the host client, thirty concurrent real purchases, restock/price updates, unavailable-service handling and container-recreation persistence. It removes only its test containers/volumes. Your normal inventory stays unchanged.

Evidence: docs/test-output.txt (17 regression tests), docs/output-noor.txt (Catalog/gateway checks), docs/client-output.txt (host CLI), docs/docker-output.txt (full real integration), docs/docker-service-output.txt (component logs), docs/docker-status.json and docs/docker-build-output.txt. verify_noor.py uses an explicit Order test double for routing; verify_docker.py uses the real Order service.

Inspect live logs with `docker compose logs --no-color`. All services log HTTP method/path/status; Order also logs successful book titles. The design report is [docs/design.pdf](docs/design.pdf), with editable text in [docs/design.md](docs/design.md). More examples are in docs/client.md and docs/docker.md.

## Known limitations

Catalog serializes stock writes, but decrementing stock and inserting an order are not one distributed transaction. Order attempts to restore stock when local order storage fails. Crashes, ambiguous network outcomes or failed compensation can still need reconciliation. There are no idempotency keys, authentication or payment/shipping workflows. These cases and possible improvements are explained in the report.
