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
    LinkedInPostEndings,
    LinkedInPostResponse,
)

from .query import (
    QueryRequest,
    QueryResponse,
    FlagRequest,
    FlagResponse,
    Highlight,
    HighlightList,
)

from .zotero import (
    ZoteroItem,
    ZoteroItemSummary,
    ZoteroItemData,
    ZoteroCreator,
    ZoteroTag,
    ZoteroSearchRequest,
    ZoteroSearchResponse,
    ZoteroNoteRequest,
    ZoteroNoteResponse,
)

from .notion import (
    NotionAuthResponse,
    NotionProject,
    NotionProjectList,
    NotionProjectContext,
    NotionRelevanceResponse,
    NotionContentResponse,
    NotionExportResponse,
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
    "LinkedInPostEndings",
    "LinkedInPostResponse",
    # Query models
    "QueryRequest",
    "QueryResponse",
    "FlagRequest",
    "FlagResponse",
    "Highlight",
    "HighlightList",
    # Zotero models
    "ZoteroItem",
    "ZoteroItemSummary",
    "ZoteroItemData",
    "ZoteroCreator",
    "ZoteroTag",
    "ZoteroSearchRequest",
    "ZoteroSearchResponse",
    "ZoteroNoteRequest",
    "ZoteroNoteResponse",
    # Notion models
    "NotionAuthResponse",
    "NotionProject",
    "NotionProjectList",
    "NotionProjectContext",
    "NotionRelevanceResponse",
    "NotionContentResponse",
    "NotionExportResponse",
]
