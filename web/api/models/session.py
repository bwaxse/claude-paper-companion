"""
Pydantic models for session management API.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SessionCreate(BaseModel):
    """
    Request model for creating a new session.

    Supports two modes:
    1. PDF Upload: Provide file via multipart/form-data
    2. Zotero: Provide zotero_key to load from Zotero library
    """

    # Zotero mode
    zotero_key: Optional[str] = Field(
        default=None,
        description="Zotero item key to load PDF from library",
        examples=["ABC123XY"]
    )

    # Optional filename override (for uploaded PDFs)
    filename: Optional[str] = Field(
        default=None,
        description="Custom filename for the session",
        max_length=255
    )

    @field_validator("zotero_key")
    @classmethod
    def validate_zotero_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Zotero key format if provided."""
        if v and len(v) < 6:
            raise ValueError("Zotero key must be at least 6 characters")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "zotero_key": "ABC123XY",
                    "filename": None
                },
                {
                    "zotero_key": None,
                    "filename": "my_paper.pdf"
                }
            ]
        }


class SessionResponse(BaseModel):
    """
    Response model for a single session.
    """

    session_id: str = Field(
        description="Unique session identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    filename: str = Field(
        description="Original PDF filename",
        examples=["paper.pdf"]
    )

    initial_analysis: str = Field(
        description="Claude's initial analysis of the paper",
        examples=["This paper presents a novel approach to..."]
    )

    created_at: datetime = Field(
        description="Session creation timestamp"
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp"
    )

    zotero_key: Optional[str] = Field(
        default=None,
        description="Associated Zotero item key"
    )

    pdf_path: Optional[str] = Field(
        default=None,
        description="Path to PDF file (if stored locally)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "filename": "transformer_paper.pdf",
                    "initial_analysis": "- [INNOVATION]: Introduces self-attention mechanism...",
                    "created_at": "2025-11-15T10:30:00Z",
                    "updated_at": "2025-11-15T10:35:00Z",
                    "zotero_key": "ABC123XY",
                    "pdf_path": "/data/pdfs/550e8400.pdf"
                }
            ]
        }
    }


class SessionSummary(BaseModel):
    """
    Summary model for listing sessions (lightweight).
    """

    session_id: str = Field(
        description="Unique session identifier"
    )

    filename: str = Field(
        description="PDF filename"
    )

    created_at: datetime = Field(
        description="Creation timestamp"
    )

    zotero_key: Optional[str] = Field(
        default=None,
        description="Associated Zotero item key"
    )

    exchange_count: int = Field(
        default=0,
        description="Number of conversation exchanges"
    )

    flag_count: int = Field(
        default=0,
        description="Number of flagged exchanges"
    )


class SessionList(BaseModel):
    """
    Response model for listing multiple sessions.
    """

    sessions: List[SessionSummary] = Field(
        default_factory=list,
        description="List of session summaries"
    )

    total: int = Field(
        description="Total number of sessions",
        ge=0
    )

    limit: int = Field(
        description="Number of sessions returned",
        ge=0
    )

    offset: int = Field(
        default=0,
        description="Offset for pagination",
        ge=0
    )


class SessionDetail(BaseModel):
    """
    Detailed session model including conversation history.
    """

    session_id: str
    filename: str
    initial_analysis: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    zotero_key: Optional[str] = None

    # Conversation data
    exchanges: List[dict] = Field(
        default_factory=list,
        description="Conversation exchanges"
    )

    flags: List[dict] = Field(
        default_factory=list,
        description="Flagged exchanges"
    )

    highlights: List[dict] = Field(
        default_factory=list,
        description="User highlights"
    )

    # Statistics
    total_exchanges: int = Field(default=0, ge=0)
    total_flags: int = Field(default=0, ge=0)
    total_highlights: int = Field(default=0, ge=0)


class SessionDelete(BaseModel):
    """
    Response model for session deletion.
    """

    session_id: str = Field(
        description="ID of deleted session"
    )

    deleted: bool = Field(
        description="Whether deletion was successful"
    )

    message: str = Field(
        description="Deletion status message"
    )
