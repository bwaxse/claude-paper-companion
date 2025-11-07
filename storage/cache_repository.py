"""
SQLite implementation of CacheRepository
"""

import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .repository import CacheRepository


class SQLiteCacheRepository(CacheRepository):
    """SQLite implementation of cache storage"""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize repository with database connection.

        Args:
            conn: SQLite connection (should have row_factory set)
        """
        self.conn = conn

    def get(self, cache_key: str) -> Optional[bytes]:
        """Get cached value, returning None if expired or not found"""
        cursor = self.conn.execute("""
            SELECT data, expires_at
            FROM cache
            WHERE cache_key = ?
        """, (cache_key,))

        row = cursor.fetchone()
        if not row:
            return None

        data, expires_at = row['data'], row['expires_at']

        # Check expiration
        if expires_at:
            expires = datetime.fromisoformat(expires_at)
            if datetime.now() > expires:
                # Expired - delete it
                self.delete(cache_key)
                return None

        # Record hit
        self.record_hit(cache_key)

        return data

    def set(
        self,
        cache_key: str,
        data: bytes,
        cache_type: str,
        ttl: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Store value in cache"""
        expires_at = None
        if ttl:
            expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

        metadata_json = json.dumps(metadata) if metadata else None

        # Use INSERT OR REPLACE to handle updates
        self.conn.execute("""
            INSERT OR REPLACE INTO cache (
                cache_key, cache_type, data, metadata, expires_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (cache_key, cache_type, data, metadata_json, expires_at))

        self.conn.commit()

    def delete(self, cache_key: str) -> bool:
        """Delete cache entry"""
        cursor = self.conn.execute(
            "DELETE FROM cache WHERE cache_key = ?",
            (cache_key,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def invalidate_expired(self) -> int:
        """Remove expired cache entries"""
        cursor = self.conn.execute("""
            DELETE FROM cache
            WHERE expires_at IS NOT NULL
              AND expires_at < CURRENT_TIMESTAMP
        """)
        self.conn.commit()
        return cursor.rowcount

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        # Total entries and size
        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total_entries,
                SUM(LENGTH(data)) as total_size,
                SUM(hit_count) as total_hits
            FROM cache
        """)
        overall_stats = dict(cursor.fetchone())

        # Stats by type
        cursor = self.conn.execute("""
            SELECT
                cache_type,
                COUNT(*) as count,
                SUM(LENGTH(data)) as size,
                SUM(hit_count) as hits,
                AVG(hit_count) as avg_hits
            FROM cache
            GROUP BY cache_type
        """)
        by_type = {row['cache_type']: dict(row) for row in cursor.fetchall()}

        # Expired entries count
        cursor = self.conn.execute("""
            SELECT COUNT(*) as expired_count
            FROM cache
            WHERE expires_at IS NOT NULL
              AND expires_at < CURRENT_TIMESTAMP
        """)
        expired_count = cursor.fetchone()[0]

        return {
            'total_entries': overall_stats['total_entries'],
            'total_size_bytes': overall_stats['total_size'] or 0,
            'total_hits': overall_stats['total_hits'] or 0,
            'expired_entries': expired_count,
            'by_type': by_type
        }

    def clear(self, cache_type: Optional[str] = None) -> int:
        """Clear cache entries"""
        if cache_type:
            cursor = self.conn.execute(
                "DELETE FROM cache WHERE cache_type = ?",
                (cache_type,)
            )
        else:
            cursor = self.conn.execute("DELETE FROM cache")

        self.conn.commit()
        return cursor.rowcount

    def record_hit(self, cache_key: str) -> None:
        """Record a cache hit"""
        self.conn.execute("""
            UPDATE cache
            SET hit_count = hit_count + 1,
                last_accessed_at = CURRENT_TIMESTAMP
            WHERE cache_key = ?
        """, (cache_key,))
        self.conn.commit()

    def get_by_type(
        self,
        cache_type: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all cache entries of a specific type.

        Args:
            cache_type: Type to filter by
            limit: Optional limit on results

        Returns:
            List of cache entry dicts (excluding data field)
        """
        query = """
            SELECT cache_key, cache_type, metadata, expires_at,
                   hit_count, created_at, last_accessed_at
            FROM cache
            WHERE cache_type = ?
            ORDER BY created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor = self.conn.execute(query, (cache_type,))
        return [dict(row) for row in cursor.fetchall()]

    def cleanup_least_used(self, cache_type: str, keep_count: int = 100) -> int:
        """
        Remove least-used cache entries of a specific type, keeping only top N.

        Args:
            cache_type: Type to clean up
            keep_count: Number of entries to keep

        Returns:
            Number of entries removed
        """
        cursor = self.conn.execute("""
            DELETE FROM cache
            WHERE cache_key IN (
                SELECT cache_key FROM cache
                WHERE cache_type = ?
                ORDER BY hit_count DESC, last_accessed_at DESC
                LIMIT -1 OFFSET ?
            )
        """, (cache_type, keep_count))

        self.conn.commit()
        return cursor.rowcount
