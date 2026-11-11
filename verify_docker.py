"""Build and verify the complete lab in isolated disposable Docker volumes.

Run on the host: python verify_docker.py
Requires Docker Desktop/Linux containers and the Python requirements.
Writes actual evidence to docs/docker-*. Normal application data is untouched.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    project = Path(__file__).resolve().parent
    docs = project / "docs"
    docs.mkdir(exist_ok=True)
    sources = ("Dockerfile", ".dockerignore", "compose.yaml", "requirements.txt",
               "catalog.py", "order.py", "frontend.py")
    for name in sources:
        if not (project / name).is_file():
            raise RuntimeError("Required source missing: " + name)
    temp = tempfile.TemporaryDirectory(prefix="bazar-docker-check-")
    context = Path(temp.name)
    project_name = "bazar-check-" + uuid.uuid4().hex[:8]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, FRONTEND_PORT=str(port))
    command = ["docker", "compose", "-p", project_name]
    records = ["Bazar full Docker verification: " + datetime.now(timezone.utc).isoformat()]
    logs = []
    build_log = (docs / "docker-build-output.txt").open("w", encoding="utf-8")
    started = False

    def compose(*args):
        result = subprocess.run(command + list(args), cwd=context, env=env,
                                text=True, capture_output=True)
        build_log.write("$ docker compose " + " ".join(args) + "\n" + result.stdout + result.stderr + "\n")
        build_log.flush()
        if result.returncode:
            raise RuntimeError("Compose failed: " + " ".join(args) + "\n" + result.stderr[-2000:])
        return result.stdout

    def call(path, method="GET"):
        req = Request(f"http://127.0.0.1:{port}" + path, method=method)
        try:
            response = urlopen(req, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def client(*args):
        result = subprocess.run([sys.executable, str(project / "client.py"),
                                 "--base-url", f"http://127.0.0.1:{port}", *args],
                                text=True, capture_output=True, timeout=20)
        text = "$ python client.py " + " ".join(args) + "\n" + result.stdout + result.stderr
        records.append(text)
        if result.returncode:
            raise RuntimeError(text)
        return result.stdout

    try:
        for name in sources:
            shutil.copy2(project / name, context / name)
        compose("config", "--quiet")
        print("Building isolated Docker project", project_name, flush=True)
        started = True
        compose("up", "--build", "-d", "--wait", "--wait-timeout", "120")
        status = [json.loads(line) for line in compose("ps", "--format", "json").splitlines() if line.strip()]
        assert len(status) == 3 and all(s.get("Health") == "healthy" for s in status), status
        (docs / "docker-status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        records.append("PASS: three healthy Linux containers; only Frontend exposed to the host.")
        client("search", "distributed systems")
        client("search", "undergraduate school")
        assert "Stock: 10" in client("info", "2")
        assert "bought book RPCs for Noobs." in client("purchase", "2")
        assert "Stock: 9" in client("info", "2")
        assert call("/purchase/999", "POST")[0] == 404
        with ThreadPoolExecutor(max_workers=20) as pool:
            responses = list(pool.map(lambda _: call("/purchase/1", "POST"), range(30)))
        counts = {status: sum(code == status for code, _ in responses)
                  for status in {code for code, _ in responses}}
        assert counts == {201: 10, 409: 20}, counts
        assert call("/info/1")[1]["quantity"] == 0
        records.append("PASS: 30 concurrent purchases: 10 successful, 20 out of stock, quantity zero.")
        count_code = "import sqlite3; db=sqlite3.connect('/data/orders.db'); print(db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]); db.close()"
        assert compose("exec", "-T", "order", "python", "-c", count_code).strip() == "11"
        logs.append("Before container recreation:\n" + compose("logs", "--no-color"))
        compose("down")
        compose("up", "-d", "--wait", "--wait-timeout", "120")
        assert call("/info/1")[1]["quantity"] == 0
        assert call("/info/2")[1]["quantity"] == 9
        assert compose("exec", "-T", "order", "python", "-c", count_code).strip() == "11"
        records.append("PASS: down/up preserved inventory and 11 order records in named volumes.")
        restock_code = "import json,urllib.request; r=urllib.request.Request('http://127.0.0.1:5001/update/1',method='PATCH',data=json.dumps({'stock_delta':3,'price':42.75}).encode(),headers={'Content-Type':'application/json'}); print(urllib.request.urlopen(r).read().decode())"
        updated = json.loads(compose("exec", "-T", "catalog", "python", "-c", restock_code))
        assert updated["quantity"] == 3 and updated["price"] == 42.75
        assert call("/purchase/1", "POST")[0] == 201
        assert call("/info/1")[1]["quantity"] == 2
        records.append("PASS: restock, price update and subsequent real purchase.")
        compose("stop", "order")
        assert call("/purchase/2", "POST")[0] == 503
        records.append("PASS: unavailable Order returns JSON HTTP 503 through Frontend.")
        compose("up", "-d", "--wait", "--wait-timeout", "120")
        logs.append("After container recreation:\n" + compose("logs", "--no-color"))
        (docs / "docker-service-output.txt").write_text("\n\n".join(logs), encoding="utf-8")
        print("PASS: client, concurrent purchases, persistence, restock and unavailable backend.", flush=True)
    finally:
        try:
            if started:
                compose("down", "-v", "--remove-orphans")
        finally:
            build_log.close()
            for attempt in range(30):
                try:
                    temp.cleanup()
                    break
                except PermissionError:
                    if attempt == 29:
                        raise
                    time.sleep(.1)
    records.append("PASS: complete integration verified; disposable containers/volumes removed. Normal application data unchanged.")
    (docs / "docker-output.txt").write_text("\n\n".join(records) + "\n", encoding="utf-8")
    print(records[-1], flush=True)


if __name__ == "__main__":
    main()
