"""
Pydantic models for Paper Companion API.
"""

from .session import (
    SessionCreate,
    SessionResponse,
    SessionListItem,
    SessionList,
    SessionDetail,
    ConversationMessage,
    SessionMetadata,
)

from .query import (
    QueryRequest,
    QueryResponse,
    FlagRequest,
    FlagResponse,
    Highlight,
    HighlightList,
)

__all__ = [
    # Session models
    "SessionCreate",
    "SessionResponse",
    "SessionListItem",
    "SessionList",
    "SessionDetail",
    "ConversationMessage",
    "SessionMetadata",
    # Query models
    "QueryRequest",
    "QueryResponse",
    "FlagRequest",
    "FlagResponse",
    "Highlight",
    "HighlightList",
]
