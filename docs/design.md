# Bazar.com design notes - Noor's contribution

This is a draft covering Catalog and Frontend. It must be combined with Sara's Order, client and Docker description before producing the final lab report. It does not claim that the whole assignment has been integrated or deployed.

## Architecture and request flow

Catalog and Frontend are independent Flask applications. Frontend is the public REST entry point: it accepts user requests and calls a backend over HTTP. It does not read SQLite directly, manage inventory, or record orders. Its configurable backend URLs allow integration without embedding another service's storage location.

Search flows from Client to Frontend GET /search/<topic>, then to Catalog GET /query/topic/<topic>. Catalog returns IDs and titles matching the topic. Information flows from Client to Frontend GET /info/<id>, then to Catalog GET /query/item/<id>. The response includes title, topic, quantity and price.

Purchase forwarding goes from Frontend POST /purchase/<id> to Order POST /purchase/<id>. Sara's service is expected to query Catalog, request a decrement and persist a successful order. The real Order behavior must be verified during integration; Frontend implements routing only.

## Data model and persistence

Catalog owns a SQLite books table with a unique integer ID, non-null title and topic, integer price_cents and integer quantity. Database checks prevent negative prices and stock. The initial titles are the four books from the lab. Books 1 and 2 are distributed systems books; books 3 and 4 belong to undergraduate school. Initial quantities of ten and prices of 40, 50, 35 and 25 are implementation choices, not values prescribed by the assignment.

Money is stored in cents to avoid storing approximate binary floating-point values. API prices are returned in ordinary units, for example 5000 cents becomes 50.0. Incoming prices must be JSON numbers, nonnegative and representable with at most two decimal places. Decimal validates their conversion before integer storage.

Catalog creates its database beside the source in data/catalog.db. INSERT OR IGNORE inserts missing seed rows without overwriting existing IDs. Repeated startup therefore preserves normal stock and price changes. Each operation opens and closes its own database connection. Local data is excluded from version control.

## Updates and concurrent requests

PATCH /update/<id> accepts a signed integer stock_delta and/or a price. A positive delta restocks a book; a negative delta subtracts copies. Booleans, fractional stock, unknown fields, empty or malformed requests and unsupported integer ranges are rejected. Missing books produce 404, inadequate stock 409 and invalid input 400. Successful updates return the exact values written by that transaction.

The update begins with BEGIN IMMEDIATE before reading stock. SQLite acquires a write reservation, so another updater must wait rather than checking the same old quantity concurrently. The transaction reads the current stock, checks the proposed result, updates quantity and price, and commits together. Rejection leaves both fields unchanged. Connections wait up to fifteen seconds for SQLite locks.

This is important even when Order performs an earlier availability check. That earlier check may become outdated; Catalog must validate the actual decrement inside the write transaction. A disposable-database check sent thirty concurrent decrements for ten copies and observed exactly ten successes, twenty conflicts and zero remaining stock.

## Gateway responses and failures

Frontend forwards each request once with a five-second connection/read timeout setting and preserves backend JSON and status, including 404 and 409 results. It percent-encodes topic values when building backend URLs. Invalid backend JSON produces a gateway 502 response, while connection or timeout failures produce JSON 503. Local HTTP errors such as an unknown route or a disallowed method also return JSON. Request method, path and status are logged.

A purchase is not automatically retried. An unavailable connection or timeout does not always establish that the backend made no changes: it may have committed before the response was lost. Users must not assume an ambiguous purchase is safe to repeat. The timeout setting limits socket waits; it is not an end-to-end distributed transaction deadline.

## Tradeoffs and remaining limitations

SQLite keeps this small assignment lightweight, but it serializes writers and can time out under heavy write contention. The database should remain owned by Catalog rather than shared as a file between services. Prices in responses use JSON numbers, while stored prices remain integer cents.

The current local programs use Flask's development server and bind to 127.0.0.1. The deployment stage must provide suitable interface binding, concurrent serving and persistent Docker volumes. Real Order integration and Docker execution are not complete in this contribution.

A stock decrement and an Order database insert are separate transactions in different services. Catalog's stock safety does not guarantee an all-or-nothing distributed purchase. A failure between these operations can require reconciliation. A future design could add purchase identifiers, durable reservations and a reconciliation process so retries can identify prior outcomes safely.

There is no authentication, TLS, payment, cancellation or shipping implementation. Backend inventory updates should remain restricted to trusted callers during deployment. There are no load-balanced replicas; Frontend routes requests by operation.

## Verification and next integration work

Real-HTTP checks covered Catalog lookups through Frontend, both topic categories, empty results, unknown IDs, method/path errors and unavailable services. Update checks covered input validation, combined changes, no partial writes on rejection, persistence and concurrent decrements. Test inventory was disposable and did not change the normal database.

A simulated Order verified routing and backend status handling only. Next, both developers should start the real services, purchase a book through Frontend, verify that stock falls by one and inspect the persisted Order record. They should then verify out-of-stock behavior, concurrent purchases, service restarts and three-container deployment. Actual client/component output and the final combined two-to-three-page report belong in docs for submission.

The README provides local setup, API paths, examples and expected error behavior. It should be updated after Docker and the real Order service are integrated.
