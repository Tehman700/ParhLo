"""Postgres (Neon) access: one small connection pool per process, pgvector registered on each connection."""

from contextlib import contextmanager
from pathlib import Path

from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings
from app.core.errors import NotConfiguredError

_pool: ConnectionPool | None = None
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _configure(conn: Connection) -> None:
    register_vector(conn)


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        url = get_settings().database_url
        if not url:
            raise NotConfiguredError("DATABASE_URL is not set. Run `vercel env pull` at the repo root.")
        _pool = ConnectionPool(
            url,
            min_size=0,
            max_size=5,
            # Neon's pooled endpoint is PgBouncer (transaction mode): no server-side prepared statements.
            kwargs={"row_factory": dict_row, "prepare_threshold": None, "autocommit": True},
            configure=_configure,
            open=True,
        )
    return _pool


@contextmanager
def db():
    with pool().connection() as conn:
        yield conn


def init_schema() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    url = get_settings().database_url
    # Run the extension/schema on a plain connection first so `vector` exists before pools register it.
    import psycopg

    with psycopg.connect(url, autocommit=True, prepare_threshold=None) as conn:
        conn.execute(sql)
