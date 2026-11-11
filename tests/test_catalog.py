"""Catalog regressions: disposable storage, atomic changes and stock safety."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

import catalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_path = catalog.DATABASE_PATH
        catalog.DATABASE_PATH = Path(self.temp.name) / "catalog.db"
        catalog.initialize_database()
        self.client = catalog.app.test_client()

    def tearDown(self):
        catalog.DATABASE_PATH = self.original_path
        self.temp.cleanup()

    def test_json_errors_and_large_unknown_id(self):
        for path in ("/missing", "/query/item/999", "/query/item/99999999999999999999999"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertTrue(response.is_json)

    def test_rejected_combined_update_does_not_change_price(self):
        before = self.client.get("/query/item/2").get_json()
        response = self.client.patch("/update/2", json={"stock_delta": -99, "price": 1})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(before, self.client.get("/query/item/2").get_json())

    def test_concurrent_decrements_and_reinitialization(self):
        def decrement(_):
            with catalog.app.test_client() as client:
                return client.patch("/update/1", json={"stock_delta": -1}).status_code
        with ThreadPoolExecutor(max_workers=20) as executor:
            statuses = list(executor.map(decrement, range(30)))
        self.assertEqual(statuses.count(200), 10)
        self.assertEqual(statuses.count(409), 20)
        catalog.initialize_database()
        self.assertEqual(self.client.get("/query/item/1").get_json()["quantity"], 0)


if __name__ == "__main__":
    unittest.main()
