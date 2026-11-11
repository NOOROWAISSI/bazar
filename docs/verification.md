# Final verification status

Verified on 2026-11-11 after merging Sara's Order implementation into noor.

| Check | Result | Evidence |
| --- | --- | --- |
| Catalog and Order regression suite | 17 passed | test-output.txt |
| Catalog/Frontend verifier | Passed; Order is an explicit routing double in this check | output-noor.txt |
| Host CLI | Real searches, details, purchase, saved receipt and stock decrement passed | client-output.txt; docker-output.txt |
| Three real Linux containers | All healthy under Docker Compose | docker-status.json; docker-build-output.txt |
| Concurrent real purchases | 30 requests, 10 successes, 20 conflicts, no negative stock | docker-output.txt |
| Container recreation | Stock and 11 orders persisted after down/up | docker-output.txt |
| Restock and price change | Update followed by a real purchase passed | docker-output.txt |
| Unavailable Order | Gateway returned JSON HTTP 503 | docker-output.txt |
| Component messages | HTTP request outcomes and bought book messages captured | docker-service-output.txt |
| Final report | Three pages, rendered and visually reviewed | design.pdf; design.md |

Run `python -m unittest discover -s tests -v`, `python verify_noor.py`, and (with Docker running) `python verify_docker.py` from the repository directory. Use the project's Python environment if necessary.

The Docker verifier uses copies of the integrated source in a unique temporary Compose project. Its test containers and disposable volumes were removed after success. Normal local databases and unrelated Docker projects were not changed.

Known failure cases remain documented: cross-service purchase/crash windows, ambiguous timeouts, failed compensation and no idempotency keys. The project does not claim exactly-once distributed transactions. The main branch is unchanged; this delivery is on noor.
