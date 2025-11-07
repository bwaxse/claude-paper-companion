"""
Storage layer for Paper Companion

Provides repository pattern abstractions for database operations.
"""

from .repository import PaperRepository, SessionRepository, CacheRepository
from .paper_repository import SQLitePaperRepository
from .session_repository import SQLiteSessionRepository
from .cache_repository import SQLiteCacheRepository

__all__ = [
    'PaperRepository',
    'SessionRepository',
    'CacheRepository',
    'SQLitePaperRepository',
    'SQLiteSessionRepository',
    'SQLiteCacheRepository'
]
