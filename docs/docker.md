# Three-service Docker deployment

This configuration runs three Linux containers: Catalog, Order and Frontend. Waitress serves concurrent HTTP requests on 0.0.0.0 inside each container. The host client stays outside Docker. Only Frontend is exposed to the host, bound to 127.0.0.1 for local access.

## Integration prerequisite

The integrated noor branch contains catalog.py, frontend.py, Sara's order.py and requests==2.32.5. The build uses these checked-in sources directly. No copying from another branch is required.

## Build and start

With Docker Desktop running in Linux-container mode, run from the repository directory:

```powershell
docker compose up --build -d --wait
docker compose ps
```

Frontend defaults to http://127.0.0.1:5000. If port 5000 is occupied, set another host port before starting:

```powershell
$env:FRONTEND_PORT = '5050'
docker compose up --build -d --wait
```

Use the same environment and repository directory for later Compose commands. Service-to-service addresses use Docker service names, not localhost: Catalog is http://catalog:5001 and Order is http://order:5002. Health checks and depends_on order startup; they do not provide distributed transaction guarantees.

## Run the host client

Install the requirements in your local Python environment if necessary. From the host:

```powershell
.\.venv\Scripts\python.exe client.py --base-url http://127.0.0.1:5000 search "distributed systems"
.\.venv\Scripts\python.exe client.py --base-url http://127.0.0.1:5000 info 2
.\.venv\Scripts\python.exe client.py --base-url http://127.0.0.1:5000 purchase 2
```

Change the client URL if you selected another host port. Purchase changes inventory and records a real order.

## Restock and logs

Catalog is not published on a host port. An operator can update it from its container; this example adds five copies of book 2:

```powershell
docker compose exec catalog python -c "import json,urllib.request; req=urllib.request.Request('http://127.0.0.1:5001/update/2',data=json.dumps({'stock_delta':5}).encode(),method='PATCH',headers={'Content-Type':'application/json'}); print(urllib.request.urlopen(req).read().decode())"
docker compose logs --no-color
```

The Docker build context includes only the three service files, Dockerfile and requirements. Local databases, Git history, virtual environments and unrelated folders are excluded.

## Persistence and shutdown

Catalog stores data in a named volume mounted at /app/data. Order uses a separate volume at /data. Each service owns its own SQLite file.

```powershell
docker compose restart
docker compose up -d --wait
docker compose down
```

Restarting or removing containers with down preserves the named volumes. Do not add -v unless you intentionally want to delete both inventory and order history. Local desktop databases are separate from Docker volume data.

The checked-in service entry points remain suitable for local development; Docker runs Waitress directly and supplies its own network binding. No source-code changes to Sara's Order are required by these container files.

## Local verification evidence

The isolated three-container check completed successfully. The host client searched both topics, read book 2, bought a copy and observed stock drop from ten to nine. Thirty concurrent purchases of book 1 produced ten HTTP 201 responses and twenty HTTP 409 responses. Removing and recreating the containers preserved both stock and eleven saved orders through the named volumes.

Actual records are in docker-output.txt, docker-service-output.txt, docker-status.json and docker-build-output.txt. The repeatable verify_docker.py check copies the integrated sources into a temporary build directory. Its uniquely named containers and disposable volumes were removed afterward, without touching normal application data.
