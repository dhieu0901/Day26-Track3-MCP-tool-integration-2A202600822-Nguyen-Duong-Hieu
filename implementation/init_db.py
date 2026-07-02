import os
import sqlite3

# Define the absolute database path
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "sqlite_lab.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    score REAL
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    grade TEXT,
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
);
"""

SEED_SQL = """
-- Seed students
INSERT INTO students (name, cohort, score) VALUES ('Alice Smith', 'A1', 88.5);
INSERT INTO students (name, cohort, score) VALUES ('Bob Jones', 'A1', 76.2);
INSERT INTO students (name, cohort, score) VALUES ('Charlie Brown', 'A2', 92.0);
INSERT INTO students (name, cohort, score) VALUES ('Diana Prince', 'A2', 85.0);
INSERT INTO students (name, cohort, score) VALUES ('Evan Wright', 'A1', 95.5);

-- Seed courses
INSERT INTO courses (name, credits) VALUES ('Introduction to AI', 4);
INSERT INTO courses (name, credits) VALUES ('Database Systems', 3);
INSERT INTO courses (name, credits) VALUES ('Software Engineering', 4);

-- Seed enrollments
INSERT INTO enrollments (student_id, course_id, grade) VALUES (1, 1, 'A');
INSERT INTO enrollments (student_id, course_id, grade) VALUES (1, 2, 'B+');
INSERT INTO enrollments (student_id, course_id, grade) VALUES (2, 1, 'B');
INSERT INTO enrollments (student_id, course_id, grade) VALUES (3, 1, 'A+');
INSERT INTO enrollments (student_id, course_id, grade) VALUES (3, 3, 'A');
INSERT INTO enrollments (student_id, course_id, grade) VALUES (4, 2, 'A');
INSERT INTO enrollments (student_id, course_id, grade) VALUES (4, 3, 'B-');
INSERT INTO enrollments (student_id, course_id, grade) VALUES (5, 1, 'A+');
INSERT INTO enrollments (student_id, course_id, grade) VALUES (5, 2, 'A');
"""


def create_database():
    """
    Creates tables and seeds initial data into the SQLite database.
    """
    print(f"Initializing database at: {DB_PATH}")
    # Ensure database is clean or we just recreate it
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError as e:
            print(f"Warning: could not delete existing DB file: {e}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)
        cursor.executescript(SEED_SQL)
        conn.commit()
        print("Database successfully initialized and seeded.")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise e
    finally:
        conn.close()
    return DB_PATH


if __name__ == "__main__":
    create_database()
