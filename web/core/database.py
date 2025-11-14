"""
Database connection management for Paper Companion.
Provides async SQLite connection with schema initialization and transaction support.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiosqlite

from .config import get_settings


class DatabaseManager:
    """
    Manages async SQLite database connections.

    Features:
    - Automatic schema initialization
    - Connection lifecycle management
    - Transaction context managers
    - Foreign key enforcement
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file. If None, uses settings.
        """
        self._db_path = db_path or get_settings().database_path
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    @property
    def db_path(self) -> str:
        """Get database file path."""
        return self._db_path

    async def initialize(self) -> None:
        """
        Initialize database with schema.
        Creates tables and indexes if they don't exist.
        """
        # Ensure database directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Read schema file
        schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        schema_sql = schema_path.read_text()

        # Execute schema
        async with self.get_connection() as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")

            # Execute schema (split by semicolon for multiple statements)
            await db.executescript(schema_sql)
            await db.commit()

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """
        Get a database connection with proper lifecycle management.

        Yields:
            aiosqlite.Connection: Database connection

        Example:
            async with db_manager.get_connection() as db:
                cursor = await db.execute("SELECT * FROM sessions")
                rows = await cursor.fetchall()
        """
        conn = await aiosqlite.connect(self._db_path)

        # Enable foreign keys
        await conn.execute("PRAGMA foreign_keys = ON")

        # Enable row factory for dict-like access
        conn.row_factory = aiosqlite.Row

        try:
            yield conn
        finally:
            await conn.close()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """
        Transaction context manager with automatic commit/rollback.

        Yields:
            aiosqlite.Connection: Database connection in transaction

        Example:
            async with db_manager.transaction() as db:
                await db.execute("INSERT INTO sessions ...")
                await db.execute("INSERT INTO metadata ...")
                # Auto-commits on success, rolls back on exception
        """
        async with self.get_connection() as conn:
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    async def execute_query(
        self,
        query: str,
        parameters: tuple = ()
    ) -> list[aiosqlite.Row]:
        """
        Execute a SELECT query and return all rows.

        Args:
            query: SQL SELECT query
            parameters: Query parameters

        Returns:
            List of rows as Row objects (dict-like access)
        """
        async with self.get_connection() as db:
            cursor = await db.execute(query, parameters)
            rows = await cursor.fetchall()
            return rows

    async def execute_one(
        self,
        query: str,
        parameters: tuple = ()
    ) -> Optional[aiosqlite.Row]:
        """
        Execute a SELECT query and return first row.

        Args:
            query: SQL SELECT query
            parameters: Query parameters

        Returns:
            First row as Row object, or None if no results
        """
        async with self.get_connection() as db:
            cursor = await db.execute(query, parameters)
            row = await cursor.fetchone()
            return row

    async def execute_insert(
        self,
        query: str,
        parameters: tuple = ()
    ) -> int:
        """
        Execute an INSERT query and return last row ID.

        Args:
            query: SQL INSERT query
            parameters: Query parameters

        Returns:
            Last inserted row ID
        """
        async with self.transaction() as db:
            cursor = await db.execute(query, parameters)
            return cursor.lastrowid

    async def execute_update(
        self,
        query: str,
        parameters: tuple = ()
    ) -> int:
        """
        Execute an UPDATE/DELETE query and return affected rows.

        Args:
            query: SQL UPDATE/DELETE query
            parameters: Query parameters

        Returns:
            Number of affected rows
        """
        async with self.transaction() as db:
            cursor = await db.execute(query, parameters)
            return cursor.rowcount

    async def health_check(self) -> bool:
        """
        Verify database is accessible and functional.

        Returns:
            True if database is healthy
        """
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("SELECT 1")
                result = await cursor.fetchone()
                return result is not None and result[0] == 1
        except Exception:
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance (singleton pattern).

    Returns:
        DatabaseManager: Database manager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def init_database() -> None:
    """
    Initialize database with schema.
    Should be called during application startup.
    """
    db_manager = get_db_manager()
    await db_manager.initialize()


# Convenience function for FastAPI dependency injection
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    FastAPI dependency for getting database connection.

    Usage:
        @app.get("/sessions")
        async def list_sessions(db: aiosqlite.Connection = Depends(get_db)):
            cursor = await db.execute("SELECT * FROM sessions")
            return await cursor.fetchall()
    """
    db_manager = get_db_manager()
    async with db_manager.get_connection() as conn:
        yield conn
