# Contribution notes

The following notes are preserved from Sara's branch. Previously reported test counts describe that branch at its verification date; the combined audit is recorded separately.

## Sara's Contribution â€” Order, Client, and Docker

This section records Sara's Order implementation, Client integration and regression tests, and Docker integration. Noor authored the original Client and Docker reference configurations, as acknowledged in the source files; Sara integrated that work into her branch. The earlier sections are retained as Noor's original contribution and describe its verification stage.

### Order architecture and purchase processing

Order is an independent Flask service exposing `POST /purchase/<id>`. It communicates with Catalog over HTTP using the configurable `CATALOG_URL`: `GET /query/item/<id>` retrieves book details, followed by `PATCH /update/<id>` with `stock_delta=-1`. Catalog validates the decrement against current stock; missing books return HTTP 404 and insufficient stock returns HTTP 409. After a successful decrement, Order inserts a receipt into its own SQLite database and returns HTTP 201 with the generated order ID and book title.

The `orders` table stores an automatically generated ID, item ID, title, price snapshot as a SQLite REAL value, and UTC creation timestamp. Parameterized inserts execute within a database transaction, and connections are closed after use. `ORDER_DATABASE_PATH` selects the database location, defaulting to `data/orders.db`; container deployment uses `/data/orders.db`. Initialization creates missing storage without replacing existing orders.

Catalog's transactional stock update provides concurrency control; Order does not rely on a potentially stale availability lookup. The Order tests exercise twelve concurrent attempts against four copies through a controlled Catalog server, expecting four saved orders and eight conflicts. Catalog requests use connection/read timeouts of 3.05 and 5 seconds. Connection failures produce HTTP 503, invalid book details or unexpected upstream responses produce HTTP 502, and an uncertain stock-update outcome is explicitly reported without automatic retry. If saving an order raises a SQLite error, Order attempts a compensating `stock_delta=1` request and returns HTTP 500, distinguishing successful restoration from failed compensation.

### Client and container deployment

The host Python CLI provides `search <topic>`, `info <id>`, and `purchase <id>` through Frontend. Search topics are URL-encoded, book IDs must be positive, and `--base-url` selects an HTTP/HTTPS Frontend endpoint. Search and information use GET; purchase uses POST and prints `bought book <title>` and the order ID. The Client applies a ten-second timeout, reports HTTP, network and response errors, and warns against automatically retrying purchases after network or server failures.

The Dockerfile builds a Python 3.12 slim image with Flask, requests and Waitress, running services as a non-root user. Compose starts separate Catalog, Order and Frontend containers with Waitress listening on all container interfaces at ports 5001, 5002 and 5000. Services communicate through Compose DNS names (`catalog` and `order`); only Frontend is published to host loopback, using `FRONTEND_PORT` or port 5000. HTTP health checks probe Catalog book lookup, Order `/health`, and Frontend book information. Healthy dependency conditions sequence startup. Separate named volumes preserve Catalog data at `/app/data` and Order data at `/data` across container recreation, provided the volumes are retained.

### Verification results and limitations

The previously reported local execution results were: **20 automated Python tests passed** (14 Order and 6 Client tests); all three Docker services reached **Healthy** status; Client search and information requests succeeded; and purchasing book ID **2** returned Order ID **1**, reduced stock from **10 to 9**, and produced a confirmed order in **`/data/orders.db`**. The automated tests cover purchase success, missing and unavailable stock, persistence, concurrency, dependency failures, timeouts, compensation, and the principal CLI operations. Order tests use temporary SQLite databases and a controlled Catalog HTTP server; Client tests mock HTTP responses. These results are recorded as previously reported local observations, not as checks rerun during this documentation update. The final audit could not independently repeat them because Python and Docker commands were unavailable in its environment.

These observations demonstrate the reported local behavior, not production readiness. Stock decrement and order insertion remain separate transactions: a crash, ambiguous timeout or failed compensation may require manual reconciliation. There are no idempotency keys or durable recovery mechanism, so exactly-once purchases and complete distributed transaction atomicity are not guaranteed. The stored price reflects the initial lookup and may become stale during a concurrent price change. Health checks indicate endpoint responsiveness; Order's health endpoint does not validate database access or Catalog availability.
