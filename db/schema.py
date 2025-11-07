"""
Database schema initialization and versioning for Paper Companion
"""

import sqlite3
from pathlib import Path
from typing import Optional

from . import get_db


def get_current_schema_version(conn: sqlite3.Connection) -> int:
    """
    Get the current schema version from database.

    Args:
        conn: Database connection

    Returns:
        Current schema version (0 if not initialized)
    """
    try:
        cursor = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        )
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0
    except sqlite3.OperationalError:
        # Table doesn't exist, database not initialized
        return 0


def init_schema(conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Initialize database schema from schema.sql file.

    This function is idempotent - it's safe to call multiple times.

    Args:
        conn: Optional database connection (creates new one if None)
    """
    if conn is None:
        conn = get_db()

    # Get current version
    current_version = get_current_schema_version(conn)

    if current_version >= 1:
        # Schema already initialized
        return

    # Read and apply schema
    schema_path = Path(__file__).parent / 'schema.sql'
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    # Execute schema in a transaction
    try:
        conn.executescript(schema_sql)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to initialize schema: {e}") from e


def ensure_schema(conn: Optional[sqlite3.Connection] = None) -> sqlite3.Connection:
    """
    Ensure database schema is initialized and up to date.

    Convenience function that gets a connection and initializes schema if needed.

    Args:
        conn: Optional database connection

    Returns:
        Database connection with schema initialized
    """
    if conn is None:
        conn = get_db()

    init_schema(conn)
    return conn


def reset_database(conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Drop all tables and reinitialize schema.

    WARNING: This will delete all data!

    Args:
        conn: Optional database connection
    """
    if conn is None:
        conn = get_db()

    # Get all table names
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row[0] for row in cursor.fetchall()]

    # Drop all tables
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS {table}")

    # Drop all indexes
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    )
    indexes = [row[0] for row in cursor.fetchall()]

    for index in indexes:
        conn.execute(f"DROP INDEX IF EXISTS {index}")

    conn.commit()

    # Reinitialize schema
    init_schema(conn)


def vacuum_database(conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Vacuum database to reclaim space and optimize.

    Args:
        conn: Optional database connection
    """
    if conn is None:
        conn = get_db()

    conn.execute("VACUUM")
    conn.commit()


# Future: Schema migration functions would go here
# def migrate_to_version_2(conn: sqlite3.Connection) -> None:
#     """Migrate from version 1 to version 2"""
#     pass
#
# MIGRATIONS = {
#     2: migrate_to_version_2,
#     # Add more migrations as schema evolves
# }
#
# def apply_migrations(conn: sqlite3.Connection) -> None:
#     """Apply all pending migrations"""
#     current = get_current_schema_version(conn)
#     target = max(MIGRATIONS.keys())
#
#     for version in range(current + 1, target + 1):
#         if version in MIGRATIONS:
#             MIGRATIONS[version](conn)
