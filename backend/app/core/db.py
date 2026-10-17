"""SQLite helper with a small seeded sample database (used by the database tool)."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core.config import get_settings

SEED_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT, segment TEXT, joined DATE
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT, price REAL, stock INTEGER
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id), quantity INTEGER, order_date DATE
);
"""

CUSTOMERS = [
    (1, "Ayesha Khan", "Lahore", "Consumer", "2024-01-14"),
    (2, "Bilal Ahmed", "Karachi", "Corporate", "2024-02-03"),
    (3, "Sara Malik", "Islamabad", "Consumer", "2024-03-21"),
    (4, "Usman Tariq", "Lahore", "Small Business", "2024-04-10"),
    (5, "Hina Raza", "Peshawar", "Corporate", "2024-05-18"),
    (6, "Omar Farooq", "Karachi", "Consumer", "2024-06-02"),
]
PRODUCTS = [
    (1, "Laptop Pro 14", "Electronics", 1899.0, 12),
    (2, "Wireless Mouse", "Accessories", 29.0, 140),
    (3, "4K Monitor", "Electronics", 449.0, 25),
    (4, "Mechanical Keyboard", "Accessories", 119.0, 60),
    (5, "Noise-Cancel Headphones", "Audio", 299.0, 33),
    (6, "USB-C Hub", "Accessories", 59.0, 90),
]
ORDERS = [
    (1, 1, 1, 1, "2025-01-05"), (2, 2, 3, 4, "2025-01-09"), (3, 3, 2, 2, "2025-01-15"),
    (4, 4, 4, 3, "2025-02-01"), (5, 5, 1, 2, "2025-02-11"), (6, 6, 5, 1, "2025-02-19"),
    (7, 1, 6, 2, "2025-03-02"), (8, 2, 2, 10, "2025-03-08"), (9, 3, 5, 1, "2025-03-17"),
    (10, 4, 3, 1, "2025-03-25"), (11, 5, 4, 5, "2025-04-04"), (12, 6, 1, 1, "2025-04-12"),
]


def db_path() -> Path:
    return get_settings().db_path


@contextmanager
def connect(read_only: bool = False):
    path = db_path()
    if read_only:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and seed sample rows if empty. Safe to call on every startup."""
    with connect() as conn:
        conn.executescript(SEED_SQL)
        if conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
            conn.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", CUSTOMERS)
            conn.executemany("INSERT INTO products VALUES (?,?,?,?,?)", PRODUCTS)
            conn.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", ORDERS)


def query(sql: str, params: tuple = (), read_only: bool = True) -> list[dict]:
    with connect(read_only=read_only) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
