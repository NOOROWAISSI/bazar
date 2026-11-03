# Bazar.com - Catalog and Frontend

This branch contains Noor's part of the bookstore lab: a persistent Catalog API and a Frontend REST gateway. Frontend routes HTTP requests; it does not provide a graphical interface.

Order, the host client, Dockerfiles and Docker Compose are Sara's assigned work. They are not included here yet. Real purchases require her Order service.

## Local setup

Requirements: Python 3.11 or newer. Run these commands from this repository's directory.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `python` is not on PATH, use the full path of your Python interpreter for the first command. The remaining commands use the project's environment directly, so activation is not required.

## Run the services

Open two terminals in the repository directory. Keep both running.

Terminal 1 - Catalog on port 5001:

```powershell
.\.venv\Scripts\python.exe catalog.py
```

Terminal 2 - Frontend on port 5000:

```powershell
.\.venv\Scripts\python.exe frontend.py
```

Press Ctrl+C in each terminal to stop it. Restart the affected service after editing its source; automatic reloading is not enabled. These commands use Flask's local development server. Container/production server configuration is a separate integration task.

## Try the gateway

Open in a browser:

- http://127.0.0.1:5000/search/distributed%20systems
- http://127.0.0.1:5000/search/undergraduate%20school
- http://127.0.0.1:5000/search/unknown
- http://127.0.0.1:5000/info/2
- http://127.0.0.1:5000/info/999

The first two requests return books 1/2 and 3/4, respectively. An unknown topic returns an empty list with HTTP 200. An unknown book returns a JSON error with HTTP 404. `%20` encodes a space in a URL. The root `/` is not an implemented route.

## REST interfaces

| Service | Method and path | Purpose |
| --- | --- | --- |
| Frontend | GET /search/<topic> | Forward topic search to Catalog |
| Frontend | GET /info/<id> | Forward book lookup to Catalog |
| Frontend | POST /purchase/<id> | Forward purchase to Order |
| Catalog | GET /query/topic/<topic> | Return matching IDs and titles |
| Catalog | GET /query/item/<id> | Return book details |
| Catalog | PATCH /update/<id> | Change stock and/or price |

Book details contain `id`, `title`, `topic`, `price` and `quantity`. An update accepts `stock_delta`, `price`, or both, and returns the updated book. `stock_delta` is a change, not an absolute quantity.

In a third PowerShell terminal, this example adds five copies to book 2 and changes its price to 45. It modifies your local database:

```powershell
$body = @{ stock_delta = 5; price = 45 } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:5001/update/2' -Method Patch -ContentType 'application/json' -Body $body
```

To subtract one copy, send `{"stock_delta": -1}`. Invalid updates return 400, an unknown book returns 404, and insufficient stock returns 409. Failed updates do not partially change the book.

After Sara starts Order on port 5002, test a purchase with:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/purchase/2' -Method Post
```

Until Order is available, purchase forwarding returns JSON HTTP 503. Opening a purchase URL in a browser sends GET and returns 405; purchase requires POST.

## Configuration and persistence

Frontend reads `CATALOG_URL` and `ORDER_URL` when it starts. Defaults are `http://127.0.0.1:5001` and `http://127.0.0.1:5002`. To change them, set environment variables in the Frontend terminal before starting it:

```powershell
$env:CATALOG_URL = 'http://127.0.0.1:5001'
$env:ORDER_URL = 'http://127.0.0.1:5002'
.\.venv\Scripts\python.exe frontend.py
```

Catalog creates `data/catalog.db` relative to catalog.py. It inserts missing seed books without resetting existing stock or prices. The database and virtual environment are ignored by Git; another developer gets a fresh database on first startup.

The current services bind to loopback for local development. Binding to a reachable interface and configuring service URLs and volumes for Docker is still required during integration. Do not point another service directly at Catalog's SQLite file.

## Verification status

Completed locally over real HTTP:

- Both topic searches, unknown topics and case-insensitive matching.
- All four book lookups and unknown-book JSON 404 responses.
- Frontend responses match the real Catalog responses.
- JSON errors for unavailable backends and incorrect routes/methods.

Catalog update verification used a disposable database: restock, decrement, price changes, combined updates, invalid inputs, persistence and concurrent stock safety. Thirty concurrent decrements for ten copies produced ten successful updates and twenty conflicts.

Purchase routing was previously verified using an explicitly simulated Order service, including backend status forwarding and invalid JSON handling. This is not a test of Sara's real Order implementation. Real purchase integration and three-container Docker verification remain pending.

See [design notes](docs/design.md) for the design and known limitations.
