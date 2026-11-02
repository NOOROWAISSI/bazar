# Verification - 2026-11-02

The source was imported from the existing local Lab1-Bazar package, then reviewed and corrected in this repository. No development history was fabricated.

## Executed successfully

- Three independent host processes communicating over real HTTP, with disposable SQLite databases.
- Both topic searches, unknown topic, info, successful purchase, invalid book ID.
- Restock, price changes, rejection of negative prices, excessive stock deltas, booleans, fractional-cent prices and unknown update fields.
- Thirty concurrent purchases for ten copies: exactly ten successes, twenty conflicts, zero remaining stock.
- Catalog and order restart persistence: stock, price and eleven order records preserved.
- Unavailable order service returns JSON HTTP 503.
- Docker Compose built and started three Linux containers. Host client searched, inspected, purchased and observed stock fall from ten to nine.

See output.txt, service-output.txt, docker-client-output.txt, docker-service-output.txt and docker-status.json for captured evidence. docker-persistence.txt records the separate real-container restart check.

## Limitations

The stock decrement and order insert are not one distributed transaction. A crash between them can require reconciliation. Purchases are not idempotent and should not be blindly retried after ambiguous timeouts. These limitations and possible reservation-based improvements are discussed in the three-page design report.
