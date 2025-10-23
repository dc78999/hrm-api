import os
import sqlite3
from typing import List, Tuple, Any

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
DB_PATH = os.path.join(DATA_DIR, "users.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    department TEXT,
    location TEXT,
    position TEXT,
    salary REAL,
    ssn TEXT
);
"""

SAMPLE_ROWS = [
    ("org_1", "Alice", "Anderson", "alice@example.com", "Engineering", "NY", "Engineer", 120000, "111-11-1111"),
    ("org_1", "Bob", "Brown", "bob@example.com", "HR", "NY", "Recruiter", 90000, "222-22-2222"),
    ("org_2", "Carol", "Clark", "carol@org2.com", "Sales", "SF", "Salesperson", 100000, "333-33-3333"),
    ("org_public", "Dave", "Dawson", "dave@public.com", "Marketing", "LA", "Marketer", 95000, "444-44-4444")
]

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.executescript(SCHEMA)
        conn.commit()
        cur.execute("SELECT COUNT(1) FROM users")
        count = cur.fetchone()[0]
        if count == 0:
            cur.executemany(
                "INSERT INTO users (org_id, first_name, last_name, email, department, location, position, salary, ssn) VALUES (?,?,?,?,?,?,?,?,?)",
                SAMPLE_ROWS
            )
            conn.commit()
    finally:
        conn.close()

def query_users(org_id: str, columns: List[str], limit: int, offset: int) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    """
    Returns (columns, rows). columns should be a non-empty list.
    This constructs a safe SQL query selecting only requested columns and filtering by org_id.
    """
    if not columns:
        raise ValueError("no columns requested")
    allowed_cols = { "id","org_id","first_name","last_name","email","department","location","position","salary","ssn" }
    for c in columns:
        if c not in allowed_cols:
            raise ValueError(f"invalid column requested: {c}")
    cols_sql = ", ".join(columns)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        sql = f"SELECT {cols_sql} FROM users WHERE org_id = ? LIMIT ? OFFSET ?"
        cur.execute(sql, (org_id, limit, offset))
        rows = cur.fetchall()
        return columns, rows
    finally:
        conn.close()
