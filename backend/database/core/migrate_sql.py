import os
import hashlib
import logging
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")

_TRACKING_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS _applied_migrations (
    filename VARCHAR(255) PRIMARY KEY,
    content_hash VARCHAR(64),
    applied_at TIMESTAMP DEFAULT NOW()
);
"""

_ENSURE_HASH_COLUMN = """
ALTER TABLE _applied_migrations
    ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
"""


def _file_hash(filepath: str) -> str:
    with open(filepath, "r") as f:
        return hashlib.sha256(f.read().encode()).hexdigest()


def run_sql_migrations(conn: Connection) -> None:
    """Execute all .sql files from database/migrations/ in alphabetical order.

    Roda na conexão recebida, dentro da transação de quem chamou e no schema
    para o qual o search_path dela aponta (há um controle por conta).

    Each file is tracked by filename + content hash.
    If a file's content changes, it is re-executed (use IF NOT EXISTS / IF EXISTS).
    """
    if not os.path.isdir(MIGRATIONS_DIR):
        logger.info("No migrations directory found, skipping.")
        return

    sql_files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    if not sql_files:
        logger.info("No SQL migration files found.")
        return

    conn.execute(text(_TRACKING_TABLE_SQL))
    conn.execute(text(_ENSURE_HASH_COLUMN))

    for filename in sql_files:
        filepath = os.path.join(MIGRATIONS_DIR, filename)
        current_hash = _file_hash(filepath)

        row = conn.execute(
            text("SELECT content_hash FROM _applied_migrations WHERE filename = :f"),
            {"f": filename},
        ).fetchone()

        if row and row[0] == current_hash:
            continue

        logger.info(f"Applying migration: {filename}")

        with open(filepath, "r") as f:
            sql_content = f.read().strip()

        if sql_content:
            for statement in sql_content.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))

            if row:
                conn.execute(
                    text("UPDATE _applied_migrations SET content_hash = :h, applied_at = NOW() WHERE filename = :f"),
                    {"h": current_hash, "f": filename},
                )
            else:
                conn.execute(
                    text("INSERT INTO _applied_migrations (filename, content_hash) VALUES (:f, :h)"),
                    {"f": filename, "h": current_hash},
                )
            logger.info(f"Migration applied: {filename}")
