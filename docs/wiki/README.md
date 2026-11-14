# Bazar project Wiki

This guide lives inside the repository, so it is available with the code and does not require GitHub's separate Wiki service.

## Start here

1. Follow the [main README](../../README.md) to clone main and start Docker Compose.
2. Run the [host client](../client.md) for search, info and purchase.
3. Review the [architecture](Architecture.md) to understand the three services and database ownership.
4. Use [troubleshooting](Troubleshooting.md) if a request or startup fails.

## References

- [Docker setup, restock and persistence](../docker.md)
- [Design report - PDF](../design.pdf)
- [Editable design report](../design.md)
- [Contributor notes](../contributions.md)
- [Verification summary](../verification.md)
- [Regression output](../test-output.txt)
- [Real Docker execution](../docker-output.txt)
- [Component logs](../docker-service-output.txt)

## Demonstration checklist

Start three healthy containers. Search both categories, request a book's details, buy one copy and observe stock decrease. Inspect the Order record and component messages. Use the disposable verifier to demonstrate concurrency and container-recreation persistence without exhausting normal inventory.

Commands and expected statuses are documented in the main README. Purchases are explicit POST requests and are never retried automatically.
