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

    # Temporarily disable foreign keys for dropping
    conn.execute("PRAGMA foreign_keys = OFF")

    # Get all table names
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row[0] for row in cursor.fetchall()]

    # Drop all tables
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS {table}")

    # Drop all indexes (explicitly, though they should be dropped with tables)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    )
    indexes = [row[0] for row in cursor.fetchall()]

    for index in indexes:
        conn.execute(f"DROP INDEX IF EXISTS {index}")

    conn.commit()

    # Re-enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

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


# Schema Migration System
# ======================
# Add new migrations below as the schema evolves. Each migration is a function
# that takes a connection and applies changes to move from version N to N+1.

# Example migration (uncomment and modify when needed):
# def migrate_to_version_2(conn: sqlite3.Connection) -> None:
#     """
#     Migration from version 1 to 2
#     Example: Add a new column to papers table
#     """
#     conn.execute("ALTER TABLE papers ADD COLUMN new_field TEXT")
#     conn.execute(
#         "INSERT INTO schema_version (version, description) VALUES (?, ?)",
#         (2, "Added new_field to papers table")
#     )
#     conn.commit()


# Migration registry: maps version number to migration function
MIGRATIONS = {
    # 2: migrate_to_version_2,
    # 3: migrate_to_version_3,
    # Add more migrations as schema evolves
}


def get_target_version() -> int:
    """
    Get the target schema version (highest available migration).

    Returns:
        Target version number
    """
    if not MIGRATIONS:
        return 1  # No migrations defined yet
    return max(MIGRATIONS.keys())


def apply_migrations(conn: Optional[sqlite3.Connection] = None, target_version: Optional[int] = None) -> None:
    """
    Apply all pending database migrations.

    Migrations are applied sequentially from current version to target version.
    Each migration is executed in a transaction for safety.

    Args:
        conn: Optional database connection
        target_version: Optional target version (defaults to latest)

    Raises:
        RuntimeError: If migration fails
        ValueError: If target version is invalid
    """
    if conn is None:
        conn = get_db()

    current = get_current_schema_version(conn)

    if target_version is None:
        target_version = get_target_version()

    # Validate target version
    if target_version < current:
        raise ValueError(
            f"Cannot downgrade from version {current} to {target_version}. "
            "Downgrades are not supported."
        )

    if target_version == current:
        # Already at target version
        return

    # Check that all migrations exist
    for version in range(current + 1, target_version + 1):
        if version not in MIGRATIONS:
            raise ValueError(
                f"Migration to version {version} not found. "
                f"Cannot upgrade from {current} to {target_version}."
            )

    # Apply migrations sequentially
    for version in range(current + 1, target_version + 1):
        migration_func = MIGRATIONS[version]

        try:
            print(f"Applying migration to version {version}...")
            migration_func(conn)
            print(f"✓ Successfully migrated to version {version}")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(
                f"Migration to version {version} failed: {e}"
            ) from e


def check_migration_needed(conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Check if database needs migration.

    Args:
        conn: Optional database connection

    Returns:
        True if migrations are pending, False otherwise
    """
    if conn is None:
        conn = get_db()

    current = get_current_schema_version(conn)
    target = get_target_version()

    return current < target


def get_migration_info(conn: Optional[sqlite3.Connection] = None) -> dict:
    """
    Get information about database schema and migrations.

    Args:
        conn: Optional database connection

    Returns:
        Dictionary with version info and migration status
    """
    if conn is None:
        conn = get_db()

    current = get_current_schema_version(conn)
    target = get_target_version()

    # Get version history
    try:
        cursor = conn.execute(
            "SELECT version, applied_at, description FROM schema_version ORDER BY version"
        )
        history = [
            {
                'version': row[0],
                'applied_at': row[1],
                'description': row[2]
            }
            for row in cursor.fetchall()
        ]
    except sqlite3.OperationalError:
        history = []

    return {
        'current_version': current,
        'target_version': target,
        'migration_needed': current < target,
        'pending_migrations': list(range(current + 1, target + 1)) if current < target else [],
        'version_history': history
    }
