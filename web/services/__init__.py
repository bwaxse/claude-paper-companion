"""
Business logic services for Paper Companion.
"""

from .session_manager import (
    SessionManager,
    get_session_manager,
    create_session_from_pdf,
    get_session,
    list_sessions,
    delete_session,
)

from .zotero_service import (
    ZoteroService,
    get_zotero_service,
    search_papers,
    get_paper_by_key,
    list_recent,
)

__all__ = [
    # Session management
    "SessionManager",
    "get_session_manager",
    "create_session_from_pdf",
    "get_session",
    "list_sessions",
    "delete_session",
    # Zotero integration
    "ZoteroService",
    "get_zotero_service",
    "search_papers",
    "get_paper_by_key",
    "list_recent",
]
