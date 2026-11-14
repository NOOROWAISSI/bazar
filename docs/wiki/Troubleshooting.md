# Troubleshooting

## Docker cannot connect

Start Docker Desktop and select Linux containers. Check docker version, then rerun docker compose up --build -d --wait from the project directory.

## Frontend port is occupied

Set `$env:FRONTEND_PORT = '5050'` in PowerShell, start Compose and use `--base-url http://127.0.0.1:5050` before the client command. Keep the same environment for later Compose operations.

## Browser shows 404

The root / does not provide a GUI. Use /search/distributed%20systems or /info/2. A favicon.ico 404 is harmless. A book ID that does not exist returns JSON 404. When running local Python services after code changes, stop the old process with Ctrl+C and start it again.

## Purchase returns 405

A browser address bar sends GET, while purchase requires POST. Run `python client.py purchase 2` through your project environment, or use Invoke-RestMethod with -Method Post.

## Purchase returns 409

There is insufficient stock. Inspect the book and apply a real restock through Catalog if a delivery arrived. Do not repeatedly purchase to test stock on normal data; use verify_docker.py with disposable volumes.

## Request returns 503

Inspect docker compose ps and docker compose logs --no-color. A required backend may be stopped or unreachable. Restart services using docker compose up -d --wait. A failed purchase response can have an unknown outcome; do not automatically retry it.

## Stock changed after previous demonstrations

Data is intentionally persistent. Restarting does not reset it. Use the isolated verifier for clean test data. down -v removes both inventory and order history and should only be used when you intend a full reset.

## Tests and evidence

Run `python -m unittest discover -s tests -v` for 23 regression tests. verify_noor.py checks Catalog/gateway behavior using a routing double; verify_docker.py uses all three real services. The latter requires Docker, records actual output in docs and removes only its own test containers/volumes.
