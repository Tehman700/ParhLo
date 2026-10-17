import re
from typing import Annotated

from pydantic import Field

from app.core import db
from app.tools.registry import tool

MAX_ROWS = 100


@tool(description="List tables in the SQLite database with their columns. Call this before writing SQL.")
def list_tables() -> dict:
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    out = {}
    for t in tables:
        cols = db.query(f"PRAGMA table_info('{t['name']}')")
        out[t["name"]] = [f"{c['name']} {c['type']}" for c in cols]
    return out


@tool(description="Run a read-only SQL SELECT query on the SQLite database and return rows (max 100).")
def query_database(
    sql: Annotated[str, Field(description="A single SELECT (or WITH ... SELECT) statement")],
) -> dict:
    statement = sql.strip().rstrip(";")
    if not re.match(r"^(select|with)\b", statement, re.IGNORECASE) or ";" in statement:
        raise ValueError("Only a single SELECT statement is allowed")
    rows = db.query(statement)  # connection is opened read-only
    return {"row_count": len(rows), "rows": rows[:MAX_ROWS], "truncated": len(rows) > MAX_ROWS}
