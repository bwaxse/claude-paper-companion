"""
Pydantic models for query/conversation API.
"""

from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """
    Request model for querying about the paper.
    """

    query: str = Field(
        description="User's question about the paper",
        min_length=1,
        max_length=5000,
        examples=["What is the main finding?", "How does the attention mechanism work?"]
    )

    highlighted_text: Optional[str] = Field(
        default=None,
        description="Text highlighted by user (provides context)",
        max_length=10000,
        examples=["The self-attention mechanism computes..."]
    )

    page: Optional[int] = Field(
        default=None,
        description="Page number reference (1-indexed)",
        ge=1,
        examples=[5]
    )

    use_sonnet: bool = Field(
        default=True,
        description="Use Sonnet (True) or Haiku (False) model"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What are the main limitations of this approach?",
                    "highlighted_text": None,
                    "page": None,
                    "use_sonnet": True
                },
                {
                    "query": "Can you explain this section?",
                    "highlighted_text": "The scaled dot-product attention is computed as...",
                    "page": 3,
                    "use_sonnet": True
                }
            ]
        }
    }


class QueryResponse(BaseModel):
    """
    Response model for query results.
    """

    exchange_id: int = Field(
        description="Unique exchange identifier",
        ge=1,
        examples=[42]
    )

    response: str = Field(
        description="Claude's response to the query",
        examples=["The main limitation is that the model requires..."]
    )

    model_used: str = Field(
        description="Claude model used for the response",
        examples=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
    )

    # Token usage statistics
    input_tokens: int = Field(
        description="Number of input tokens used",
        ge=0
    )

    output_tokens: int = Field(
        description="Number of output tokens used",
        ge=0
    )

    cost: float = Field(
        description="Estimated cost in USD",
        ge=0,
        examples=[0.0023]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "exchange_id": 42,
                    "response": "The main limitations are: 1) Quadratic complexity...",
                    "model_used": "claude-3-5-sonnet-20241022",
                    "input_tokens": 1500,
                    "output_tokens": 250,
                    "cost": 0.0082
                }
            ]
        }
    }


class FlagRequest(BaseModel):
    """
    Request model for flagging an exchange.
    """

    exchange_id: int = Field(
        description="Exchange ID to flag",
        ge=1
    )

    note: Optional[str] = Field(
        default=None,
        description="Optional note about why this was flagged",
        max_length=1000,
        examples=["Important insight about methodology"]
    )


class FlagResponse(BaseModel):
    """
    Response model for flag operations.
    """

    flag_id: int = Field(
        description="Unique flag identifier",
        ge=1
    )

    exchange_id: int = Field(
        description="Exchange that was flagged",
        ge=1
    )

    flagged: bool = Field(
        description="Whether the exchange is now flagged"
    )

    message: str = Field(
        description="Status message",
        examples=["Exchange flagged successfully"]
    )


class HighlightCreate(BaseModel):
    """
    Request model for creating a highlight.
    """

    text: str = Field(
        description="Highlighted text from the paper",
        min_length=1,
        max_length=10000
    )

    page_number: Optional[int] = Field(
        default=None,
        description="Page number where highlight appears",
        ge=1
    )

    exchange_id: Optional[int] = Field(
        default=None,
        description="Associated conversation exchange",
        ge=1
    )

    note: Optional[str] = Field(
        default=None,
        description="Optional note about the highlight",
        max_length=1000
    )


class HighlightResponse(BaseModel):
    """
    Response model for highlight operations.
    """

    highlight_id: int = Field(
        description="Unique highlight identifier",
        ge=1
    )

    text: str = Field(
        description="Highlighted text"
    )

    page_number: Optional[int] = None
    exchange_id: Optional[int] = None
    note: Optional[str] = None
    created_at: str = Field(
        description="Creation timestamp"
    )


class ConversationHistory(BaseModel):
    """
    Model for conversation history.
    """

    session_id: str
    exchanges: list[dict] = Field(
        default_factory=list,
        description="List of conversation exchanges"
    )

    total_exchanges: int = Field(
        ge=0,
        description="Total number of exchanges"
    )

    total_cost: float = Field(
        default=0.0,
        ge=0,
        description="Total estimated cost for this session"
    )
