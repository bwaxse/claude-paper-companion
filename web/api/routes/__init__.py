"""
FastAPI route modules for Paper Companion API.
"""

from .sessions import router as sessions_router
from .queries import router as queries_router
from .zotero import router as zotero_router

__all__ = [
    "sessions_router",
    "queries_router",
    "zotero_router",
]
