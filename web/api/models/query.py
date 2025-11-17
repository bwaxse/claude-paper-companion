"""
Pydantic models for query/conversation handling.
"""

from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryRequest(BaseModel):
    """
    Request model for querying a paper.
    User asks questions about the paper in a session.
    """
    query: str = Field(
        min_length=1,
        max_length=2000,
        description="User's question or query about the paper"
    )
    highlighted_text: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Optional text highlighted by user for context"
    )
    page_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional page number reference"
    )
    use_sonnet: bool = Field(
        default=True,
        description="Use Sonnet (True) or Haiku (False) for response"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and clean query text."""
        query = v.strip()
        if not query:
            raise ValueError("Query cannot be empty")
        return query

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What is the time complexity of multi-head attention?",
                "highlighted_text": "Multi-head attention allows the model to jointly attend...",
                "page_number": 5,
                "use_sonnet": True
            }
        }
    )


class QueryResponse(BaseModel):
    """
    Response model for query results.
    Contains Claude's response and metadata.
    """
    exchange_id: int = Field(description="Exchange ID for this Q&A pair")
    response: str = Field(description="Claude's response to the query")
    model_used: str = Field(description="Claude model used for response")
    usage: Dict[str, Any] = Field(
        description="Token usage statistics",
        default_factory=dict
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exchange_id": 3,
                "response": "The time complexity of multi-head attention is O(n²d)...",
                "model_used": "claude-3-5-sonnet-20241022",
                "usage": {
                    "input_tokens": 1234,
                    "output_tokens": 156,
                    "cost": 0.0045
                }
            }
        }
    )


class FlagRequest(BaseModel):
    """
    Request model for flagging an exchange.
    Users can flag important exchanges for later review.
    """
    exchange_id: int = Field(ge=1, description="Exchange ID to flag")
    note: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional note about why this was flagged"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exchange_id": 3,
                "note": "Important insight about attention mechanism"
            }
        }
    )


class FlagResponse(BaseModel):
    """
    Response model for flag operations.
    """
    success: bool = Field(description="Whether flag operation succeeded")
    message: str = Field(description="Status message")
    flag_id: Optional[int] = Field(default=None, description="Flag ID if created")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Exchange flagged successfully",
                "flag_id": 42
            }
        }
    )


class Highlight(BaseModel):
    """
    Model for a text highlight.
    """
    id: int = Field(description="Highlight ID")
    text: str = Field(description="Highlighted text")
    page_number: Optional[int] = Field(default=None, description="Page number")
    exchange_id: Optional[int] = Field(default=None, description="Associated exchange")
    created_at: str = Field(description="Creation timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 5,
                "text": "The Transformer uses multi-head attention...",
                "page_number": 3,
                "exchange_id": 2,
                "created_at": "2025-11-17T10:35:00Z"
            }
        }
    )


class HighlightList(BaseModel):
    """
    Response model for listing highlights.
    """
    highlights: list[Highlight] = Field(description="List of highlights")
    total: int = Field(description="Total number of highlights")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "highlights": [
                    {
                        "id": 1,
                        "text": "Key finding...",
                        "page_number": 5,
                        "created_at": "2025-11-17T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }
    )
