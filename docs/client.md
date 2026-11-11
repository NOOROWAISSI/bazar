# Host command-line client

Run client.py on the host while Frontend, Catalog and (for purchases) Order are running. It uses Python's standard library and needs no additional packages.

From the repository directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe client.py --help
.\.venv\Scripts\python.exe client.py search "distributed systems"
.\.venv\Scripts\python.exe client.py search "undergraduate school"
.\.venv\Scripts\python.exe client.py info 2
.\.venv\Scripts\python.exe client.py purchase 2
```

Purchase buys one real copy. It is never run automatically when the client starts, and requests are never automatically retried. A successful purchase prints `bought book book_name` with the actual title and displays the order ID. Search shows IDs and titles; info shows topic, price and stock.

To use another Frontend address, place the option before the command:

```powershell
.\.venv\Scripts\python.exe client.py --base-url http://127.0.0.1:5000 info 2
```

Successful commands exit with code 0. Server/network/response errors exit with code 1, and invalid command-line arguments exit with code 2. Backend errors are displayed with their HTTP status. A failed or timed-out purchase can have an ambiguous outcome; do not automatically retry it.

The integrated noor branch includes Sara's real Order service. Start all three services locally or use Docker Compose before purchasing. See ../README.md for the complete setup.

`client-output.txt` records actual execution against copies of all three services using disposable databases. It does not change normal inventory.
