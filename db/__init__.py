"""
Database connection and initialization for Paper Companion
"""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# Default database location
DEFAULT_DB_PATH = Path.home() / '.paper_companion' / 'paper_companion.db'

# Global connection (for simple use cases)
_connection: Optional[sqlite3.Connection] = None


def get_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Get database connection with row factory configured.

    Args:
        db_path: Path to database file (default: ~/.paper_companion/paper_companion.db)

    Returns:
        sqlite3.Connection with row_factory set to sqlite3.Row
    """
    global _connection

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Create parent directory if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Reuse connection if it exists and points to same database
    if _connection is not None:
        try:
            # Test if connection is alive
            _connection.execute("SELECT 1")
            return _connection
        except sqlite3.Error:
            _connection = None

    # Create new connection
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Enable foreign keys (not enabled by default in SQLite)
    conn.execute("PRAGMA foreign_keys = ON")

    # Performance optimizations
    conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
    conn.execute("PRAGMA synchronous = NORMAL")  # Faster writes
    conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY")  # Temp tables in memory

    _connection = conn
    return conn


@contextmanager
def transaction(conn: Optional[sqlite3.Connection] = None):
    """
    Context manager for database transactions.

    Usage:
        with transaction() as conn:
            conn.execute("INSERT INTO ...")
            conn.execute("UPDATE ...")
        # Auto-commits on success, rolls back on exception

    Args:
        conn: Optional connection (creates new one if None)

    Yields:
        sqlite3.Connection
    """
    if conn is None:
        conn = get_db()

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def close_db():
    """Close the global database connection"""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def dict_factory(cursor, row):
    """
    Alternative row factory that returns dictionaries instead of Row objects.

    Usage:
        conn.row_factory = dict_factory
    """
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
