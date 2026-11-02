# Lab 1 — Bazar.com

Three Flask microservices, HTTP REST, SQLite persistence, concurrent request handling, and three Linux containers managed by Docker Compose.

## Run with Docker (recommended)

Install Docker Desktop and select Linux containers. From this folder:

```sh
docker compose -p bazar up --build -d
docker compose -p bazar ps
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python client.py
docker compose -p bazar logs --no-color
docker compose -p bazar stop
```

The frontend is available at http://localhost:5000. Catalog and order are reachable only inside the Compose network. Data survives restarts in named volumes. `docker compose -p bazar down` removes containers but preserves data; `docker compose -p bazar down -v` deliberately erases catalog and order databases.

## Public endpoints

| Method | Path | Result |
| --- | --- | --- |
| GET | /search/distributed%20systems | IDs and titles of books 1 and 2 |
| GET | /search/undergraduate%20school | IDs and titles of books 3 and 4 |
| GET | /info/2 | Book details, quantity, price |
| POST | /purchase/2 | One purchase, 201 receipt or 409 out of stock |
| GET | /health | Process health |

Example host requests (use `curl.exe` in Windows PowerShell):

```sh
curl "http://localhost:5000/search/distributed%20systems"
curl http://localhost:5000/info/2
curl -X POST http://localhost:5000/purchase/2
```

Catalog additionally exposes GET `/query/topic/<topic>`, GET `/query/item/<id>` and PATCH `/update/<id>`. Send JSON with `stock_delta` (positive restock, negative decrement) and/or `price` (nonnegative, up to two decimal places). Example from inside the catalog container:

```sh
docker compose -p bazar exec catalog python -c "from common import call; print(call('http://localhost:5001/update/2','PATCH',{'stock_delta':5,'price':45.5}))"
```

Restock is explicit; invoke it whenever new stock arrives. There is no invented automatic inventory source.

## Local alternative and verification

After installing requirements, run these in three separate terminals from this directory:

```sh
python -m waitress --listen=127.0.0.1:5001 catalog:app
python -m waitress --listen=127.0.0.1:5002 order:app
python -m waitress --listen=127.0.0.1:5000 frontend:app
```

Then `python client.py`. Run `python verify.py` for isolated integration checks with three real processes on ports 15500–15502. It uses disposable databases and does not modify normal inventory. Save results using `python verify.py > docs/output.txt 2>&1`; component logs are written to `docs/service-output.txt`.

For separate machines, set `CATALOG_URL` on frontend and order, and `ORDER_URL` on frontend to routable backend addresses. Bind Waitress to `0.0.0.0` on the appropriate ports. Each service owns its database; do not share a SQLite file across hosts.

## Submission

The design report is `docs/design.html` (open in a browser; print to PDF if needed). Actual integration output is in `docs/output.txt`, with component messages in `docs/service-output.txt`. `docs/verification.md` distinguishes executed checks from deployment work still required.

Repository: https://github.com/NOOROWAISSI/bazar

Clone and run:

```sh
git clone https://github.com/NOOROWAISSI/bazar.git
cd bazar
docker compose -p bazar up --build -d --wait
```

The frontend is an API gateway, not a graphical UI or a load balancer. It routes requests by operation; it does not distribute traffic across replicas.

This implementation reuses an existing local lab package. Commits record its import, validation fixes and newly executed verification; they do not represent a fabricated development history.
