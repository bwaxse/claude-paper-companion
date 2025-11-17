"""
FastAPI route modules for Paper Companion API.
"""

from .sessions import router as sessions_router

__all__ = [
    "sessions_router",
]
