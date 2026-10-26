"""Database access. Configuration comes only from environment variables."""

import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT        NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    done        BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

pool: ConnectionPool | None = None


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set, e.g. postgresql://app:app@localhost:5432/app")
    return url


def open_pool() -> None:
    global pool
    pool = ConnectionPool(
        database_url(),
        min_size=1,
        max_size=int(os.environ.get("DB_POOL_SIZE", "5")),
        kwargs={"row_factory": dict_row},
        open=True,
    )
    pool.wait(timeout=30)
    with pool.connection() as conn:
        conn.execute(SCHEMA)


def close_pool() -> None:
    if pool is not None:
        pool.close()


def connection():
    if pool is None:
        raise RuntimeError("database pool is not open")
    return pool.connection()
