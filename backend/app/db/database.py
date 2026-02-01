"""
SQLite DB init and connection. Uses aiosqlite for async.
"""
import aiosqlite
import os
from pathlib import Path

DB_PATH = os.environ.get("PANTRY_DB_PATH", "pantry.db")


def get_db_path() -> str:
    return DB_PATH


async def init_db() -> None:
    """Create DB file and run schema if needed."""
    path = get_db_path()
    schema_path = Path(__file__).parent / "schema.sql"
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        with open(schema_path) as f:
            await db.executescript(f.read())
        await db.commit()


async def get_connection():
    """Yield a connection for request scope or job. Caller must close."""
    db = await aiosqlite.connect(get_db_path())
    db.row_factory = aiosqlite.Row
    return db
