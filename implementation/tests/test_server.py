import unittest
import os
import sqlite3
import shutil
from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import SCHEMA_SQL, SEED_SQL

class TestSQLiteAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We will create a separate test database in the tests folder
        cls.test_dir = os.path.dirname(os.path.abspath(__file__))
        cls.test_db_path = os.path.join(cls.test_dir, "test_sqlite_lab.db")
        cls.adapter = SQLiteAdapter(db_path=cls.test_db_path)

    def setUp(self):
        # Fresh initialization for each test
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)
        cursor.executescript(SEED_SQL)
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_list_tables(self):
        tables = self.adapter.list_tables()
        self.assertIn("students", tables)
        self.assertIn("courses", tables)
        self.assertIn("enrollments", tables)
        self.assertEqual(len(tables), 3)

    def test_get_table_schema(self):
        schema = self.adapter.get_table_schema("students")
        self.assertEqual(len(schema), 4)
        col_names = [col["name"] for col in schema]
        self.assertListEqual(col_names, ["id", "name", "cohort", "score"])

    def test_get_table_schema_invalid(self):
        with self.assertRaises(ValidationError):
            self.adapter.get_table_schema("non_existent")

    def test_search_all(self):
        results = self.adapter.search("students")
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]["name"], "Alice Smith")

    def test_search_filters_dict(self):
        results = self.adapter.search("students", filters={"cohort": "A2"})
        self.assertEqual(len(results), 2)
        names = {r["name"] for r in results}
        self.assertEqual(names, {"Charlie Brown", "Diana Prince"})

    def test_search_filters_list(self):
        # Testing score > 90
        results = self.adapter.search("students", filters=[{"column": "score", "operator": ">", "value": 90.0}])
        self.assertEqual(len(results), 2)
        names = {r["name"] for r in results}
        self.assertEqual(names, {"Charlie Brown", "Evan Wright"})

    def test_search_filters_in(self):
        results = self.adapter.search("students", filters=[{"column": "cohort", "operator": "IN", "value": ["A2"]}])
        self.assertEqual(len(results), 2)

    def test_search_filters_in_empty(self):
        results = self.adapter.search("students", filters=[{"column": "cohort", "operator": "IN", "value": []}])
        self.assertEqual(len(results), 0)

    def test_search_filters_in_invalid_type(self):
        with self.assertRaises(ValidationError):
            self.adapter.search("students", filters=[{"column": "cohort", "operator": "IN", "value": "A2"}])

    def test_search_pagination(self):
        # Order by name ASC, limit 2, offset 1
        results = self.adapter.search("students", limit=2, offset=1, order_by="name", descending=False)
        self.assertEqual(len(results), 2)
        # Sorted names: Alice Smith (1), Bob Jones (2), Charlie Brown (3), Diana Prince (4), Evan Wright (5)
        # Offset 1 means skip Alice Smith, so Bob Jones and Charlie Brown
        self.assertEqual(results[0]["name"], "Bob Jones")
        self.assertEqual(results[1]["name"], "Charlie Brown")

    def test_search_invalid_table(self):
        with self.assertRaises(ValidationError):
            self.adapter.search("invalid_table")

    def test_search_invalid_column(self):
        with self.assertRaises(ValidationError):
            self.adapter.search("students", columns=["invalid_col"])

    def test_search_invalid_filter_column(self):
        with self.assertRaises(ValidationError):
            self.adapter.search("students", filters={"invalid_col": 1})

    def test_search_invalid_filter_operator(self):
        with self.assertRaises(ValidationError):
            self.adapter.search("students", filters=[{"column": "name", "operator": "SOME_OP", "value": "x"}])

    def test_search_invalid_limit(self):
        with self.assertRaises(ValidationError):
            self.adapter.search("students", limit=-1)

    def test_search_invalid_offset(self):
        with self.assertRaises(ValidationError):
            self.adapter.search("students", offset=-5)

    def test_insert_success(self):
        new_row = {"name": "Test Student", "cohort": "B1", "score": 85.0}
        inserted = self.adapter.insert("students", new_row)
        self.assertIsNotNone(inserted)
        self.assertEqual(inserted["name"], "Test Student")
        self.assertEqual(inserted["cohort"], "B1")
        self.assertEqual(inserted["score"], 85.0)
        self.assertIsNotNone(inserted["id"])

        # Check it is in DB
        rows = self.adapter.search("students", filters={"id": inserted["id"]})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Test Student")

    def test_insert_empty(self):
        with self.assertRaises(ValidationError):
            self.adapter.insert("students", {})

    def test_insert_invalid_column(self):
        with self.assertRaises(ValidationError):
            self.adapter.insert("students", {"name": "X", "invalid_col": 1})

    def test_aggregate_count(self):
        results = self.adapter.aggregate("students", "count")
        self.assertEqual(results[0]["value"], 5)

    def test_aggregate_avg_group_by(self):
        # Avg score by cohort
        results = self.adapter.aggregate("students", "avg", column="score", group_by="cohort")
        self.assertEqual(len(results), 2)
        
        cohort_map = {r["cohort"]: r["value"] for r in results}
        # A1: Alice (88.5) + Bob (76.2) + Evan (95.5) = 260.2 / 3 = 86.7333
        # A2: Charlie (92.0) + Diana (85.0) = 177 / 2 = 88.5
        self.assertAlmostEqual(cohort_map["A2"], 88.5)
        self.assertAlmostEqual(cohort_map["A1"], 86.7333333, places=4)

    def test_aggregate_invalid_metric(self):
        with self.assertRaises(ValidationError):
            self.adapter.aggregate("students", "invalid")

    def test_aggregate_missing_column(self):
        # For non-count, column is required
        with self.assertRaises(ValidationError):
            self.adapter.aggregate("students", "avg")

    def test_aggregate_invalid_column(self):
        with self.assertRaises(ValidationError):
            self.adapter.aggregate("students", "avg", column="invalid_col")

    def test_aggregate_invalid_group_by(self):
        with self.assertRaises(ValidationError):
            self.adapter.aggregate("students", "count", group_by="invalid_col")


if __name__ == "__main__":
    unittest.main()
