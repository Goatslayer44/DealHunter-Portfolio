import sqlite3
import unittest
from unittest.mock import patch

import database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        # Use a fresh in-memory SQLite database for each test.
        self.connection = sqlite3.connect(":memory:")

        self.patcher = patch.object(
            database,
            "DATABASE_NAME",
            ":memory:"
        )

        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.connection.close()

    def test_save_product(self):
        with patch.object(
            database,
            "DATABASE_NAME",
            "file:test_save?mode=memory&cache=shared"
        ):
            original_connect = sqlite3.connect

            keeper = original_connect(
                database.DATABASE_NAME,
                uri=True
            )

            try:
                with patch.object(
                    database.sqlite3,
                    "connect",
                    side_effect=lambda name: original_connect(
                        name, uri=True
                    )
                ):
                    database.create_database()

                    profit = database.save_product(
                        "Test Gaming Controller",
                        40, 100, 10, 15
                    )

                    self.assertEqual(profit, 35)

                    count = keeper.execute(
                        "SELECT COUNT(*) FROM products"
                    ).fetchone()[0]

                    self.assertEqual(count, 1)
            finally:
                keeper.close()

    def test_invalid_input_rejected_before_saving(self):
        with self.assertRaises(ValueError):
            database.save_product("", 40, 100, 10, 15)
        with self.assertRaises(ValueError):
            database.save_product("Test Item", -5, 100, 10, 15)
        with self.assertRaises(TypeError):
            database.save_product("Test Item", "40", 100, 10, 15)

    def test_prevent_duplicates(self):
        with patch.object(
            database,
            "DATABASE_NAME",
            "file:test_duplicates?mode=memory&cache=shared"
        ):
            original_connect = sqlite3.connect

            keeper = original_connect(
                database.DATABASE_NAME,
                uri=True
            )

            try:
                with patch.object(
                    database.sqlite3,
                    "connect",
                    side_effect=lambda name: original_connect(
                        name, uri=True
                    )
                ):
                    database.create_database()

                    database.save_product(
                        "Test Laptop",
                        200, 450, 20, 50
                    )

                    database.save_product(
                        "Test Laptop",
                        200, 450, 20, 50
                    )

                    count = keeper.execute(
                        "SELECT COUNT(*) FROM products"
                    ).fetchone()[0]

                    self.assertEqual(count, 1)
            finally:
                keeper.close()


if __name__ == "__main__":
    unittest.main()