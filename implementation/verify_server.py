import os
import json
from db import SQLiteAdapter, ValidationError

def run_verification():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "sqlite_lab.db")
    print(f"Loading adapter for database: {db_path}")
    adapter = SQLiteAdapter(db_path=db_path)

    print("\n--- 1. Testing list_tables ---")
    tables = adapter.list_tables()
    print("Tables in database:", tables)
    assert "students" in tables, "students table missing!"
    assert "courses" in tables, "courses table missing!"
    assert "enrollments" in tables, "enrollments table missing!"

    print("\n--- 2. Testing get_table_schema for students ---")
    student_schema = adapter.get_table_schema("students")
    print(json.dumps(student_schema, indent=2))
    assert len(student_schema) > 0, "Schema empty!"
    assert any(col["name"] == "name" for col in student_schema)

    print("\n--- 3. Testing search ---")
    # Search students in cohort A1
    a1_students = adapter.search("students", filters={"cohort": "A1"})
    print("Cohort A1 students:")
    for s in a1_students:
        print(f" - {s['name']} (Cohort: {s['cohort']}, Score: {s['score']})")
    assert len(a1_students) > 0, "No students found in cohort A1!"

    # Search with ordering and pagination
    paged_students = adapter.search("students", limit=2, offset=1, order_by="score", descending=True)
    print("Paged students (ordered by score DESC, limit 2, offset 1):")
    for s in paged_students:
         print(f" - {s['name']} (Score: {s['score']})")
    assert len(paged_students) == 2, f"Expected 2 paged students, got {len(paged_students)}"

    # Search with rich filters list
    rich_filtered = adapter.search("students", filters=[{"column": "score", "operator": ">", "value": 80.0}])
    print("Students with score > 80.0:")
    for s in rich_filtered:
         print(f" - {s['name']} (Score: {s['score']})")
    assert len(rich_filtered) > 0

    print("\n--- 4. Testing insert ---")
    new_student = {"name": "Hieu Nguyen", "cohort": "A1", "score": 98.0}
    inserted = adapter.insert("students", new_student)
    print("Inserted Row:", inserted)
    assert inserted is not None
    assert inserted["name"] == "Hieu Nguyen"
    assert inserted["id"] is not None

    print("\n--- 5. Testing aggregate ---")
    # Count students
    total_students = adapter.aggregate("students", "count")
    print("Total students count:", total_students)
    assert total_students[0]["value"] > 5, "Expected more than 5 students now!"

    # Avg score grouped by cohort
    avg_scores = adapter.aggregate("students", "avg", column="score", group_by="cohort")
    print("Average scores grouped by cohort:")
    print(json.dumps(avg_scores, indent=2))
    assert len(avg_scores) > 0

    print("\n--- 6. Testing Validations and Error Handling ---")
    # Test invalid table search
    try:
        adapter.search("non_existent_table")
        print("FAIL: Expected ValidationError for non-existent table!")
    except ValidationError as e:
        print("PASS: Caught expected error for missing table:", e)

    # Test invalid column search
    try:
        adapter.search("students", columns=["non_existent_column"])
        print("FAIL: Expected ValidationError for non-existent column in select!")
    except ValidationError as e:
        print("PASS: Caught expected error for missing column:", e)

    # Test invalid column filter
    try:
        adapter.search("students", filters={"non_existent_column": "value"})
        print("FAIL: Expected ValidationError for non-existent column in filter!")
    except ValidationError as e:
        print("PASS: Caught expected error for missing column in filter:", e)

    # Test unsupported operator
    try:
        adapter.search("students", filters=[{"column": "score", "operator": "BETWEEN", "value": (80, 90)}])
        print("FAIL: Expected ValidationError for unsupported operator!")
    except ValidationError as e:
        print("PASS: Caught expected error for unsupported operator:", e)

    # Test bad aggregate metric
    try:
        adapter.aggregate("students", "invalid_metric")
        print("FAIL: Expected ValidationError for unsupported metric!")
    except ValidationError as e:
        print("PASS: Caught expected error for unsupported metric:", e)

    print("\nVerification Completed successfully!")

if __name__ == "__main__":
    run_verification()
