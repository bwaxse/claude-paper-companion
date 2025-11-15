"""
Pydantic models for request/response validation.
"""

# Session models
from .session import (
    SessionCreate,
    SessionResponse,
    SessionSummary,
    SessionList,
    SessionDetail,
    SessionDelete,
)

# Query models
from .query import (
    QueryRequest,
    QueryResponse,
    FlagRequest,
    FlagResponse,
    HighlightCreate,
    HighlightResponse,
    ConversationHistory,
)

# Metadata models
from .metadata import (
    PaperMetadata,
    InsightCategory,
    SessionInsights,
    ZoteroItem,
    ZoteroSearchResult,
    ExportData,
)

__all__ = [
    # Session models
    "SessionCreate",
    "SessionResponse",
    "SessionSummary",
    "SessionList",
    "SessionDetail",
    "SessionDelete",
    # Query models
    "QueryRequest",
    "QueryResponse",
    "FlagRequest",
    "FlagResponse",
    "HighlightCreate",
    "HighlightResponse",
    "ConversationHistory",
    # Metadata models
    "PaperMetadata",
    "InsightCategory",
    "SessionInsights",
    "ZoteroItem",
    "ZoteroSearchResult",
    "ExportData",
]
