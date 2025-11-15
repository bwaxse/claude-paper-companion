"""
Pydantic models for paper metadata and insights.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    """
    Metadata about the paper (extracted from PDF or Zotero).
    """

    title: Optional[str] = Field(
        default=None,
        description="Paper title",
        max_length=500
    )

    authors: Optional[str] = Field(
        default=None,
        description="Author names (comma-separated or JSON)",
        max_length=1000
    )

    doi: Optional[str] = Field(
        default=None,
        description="Digital Object Identifier",
        max_length=100
    )

    arxiv_id: Optional[str] = Field(
        default=None,
        description="ArXiv identifier",
        max_length=50
    )

    publication_date: Optional[str] = Field(
        default=None,
        description="Publication date (YYYY-MM-DD or YYYY)",
        max_length=50
    )

    journal: Optional[str] = Field(
        default=None,
        description="Journal or conference name",
        max_length=200
    )

    abstract: Optional[str] = Field(
        default=None,
        description="Paper abstract",
        max_length=5000
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Attention Is All You Need",
                    "authors": "Vaswani et al.",
                    "doi": "10.48550/arXiv.1706.03762",
                    "arxiv_id": "1706.03762",
                    "publication_date": "2017",
                    "journal": "NeurIPS",
                    "abstract": "The dominant sequence transduction models..."
                }
            ]
        }
    }


class InsightCategory(BaseModel):
    """
    Categorized insights from conversation.
    """

    category: str = Field(
        description="Insight category",
        examples=["strengths", "weaknesses", "methodological_notes"]
    )

    items: List[str] = Field(
        default_factory=list,
        description="List of insights in this category"
    )


class SessionInsights(BaseModel):
    """
    Extracted insights from a session.
    """

    session_id: str

    # Thematic insights
    strengths: List[str] = Field(
        default_factory=list,
        description="Paper strengths identified"
    )

    weaknesses: List[str] = Field(
        default_factory=list,
        description="Weaknesses and limitations"
    )

    methodological_notes: List[str] = Field(
        default_factory=list,
        description="Notes about methodology"
    )

    key_findings: List[str] = Field(
        default_factory=list,
        description="Key findings discussed"
    )

    open_questions: List[str] = Field(
        default_factory=list,
        description="Unresolved questions"
    )

    applications: List[str] = Field(
        default_factory=list,
        description="Potential applications"
    )

    # User-specific insights
    user_interests: List[str] = Field(
        default_factory=list,
        description="User's specific interests and interpretations"
    )

    highlight_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested passages to highlight"
    )

    # Metadata
    total_exchanges: int = Field(default=0, ge=0)
    flagged_exchanges: int = Field(default=0, ge=0)
    extracted_at: str = Field(
        description="Timestamp when insights were extracted"
    )


class ZoteroItem(BaseModel):
    """
    Zotero item information.
    """

    key: str = Field(
        description="Zotero item key",
        examples=["ABC123XY"]
    )

    title: str = Field(
        description="Item title"
    )

    item_type: str = Field(
        description="Item type",
        examples=["journalArticle", "conferencePaper"]
    )

    creators: List[dict] = Field(
        default_factory=list,
        description="Authors/creators"
    )

    publication_title: Optional[str] = Field(
        default=None,
        description="Journal or conference name"
    )

    date: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ZoteroSearchResult(BaseModel):
    """
    Zotero search results.
    """

    items: List[ZoteroItem] = Field(
        default_factory=list,
        description="Found items"
    )

    total: int = Field(
        ge=0,
        description="Total number of results"
    )

    query: str = Field(
        description="Search query used"
    )


class ExportData(BaseModel):
    """
    Complete session export data.
    """

    session: dict = Field(
        description="Session information"
    )

    metadata: Optional[PaperMetadata] = None

    conversation: List[dict] = Field(
        default_factory=list,
        description="Full conversation history"
    )

    flags: List[dict] = Field(
        default_factory=list,
        description="Flagged exchanges"
    )

    highlights: List[dict] = Field(
        default_factory=list,
        description="User highlights"
    )

    insights: Optional[SessionInsights] = None

    export_format: str = Field(
        default="json",
        description="Export format",
        examples=["json", "markdown"]
    )

    exported_at: str = Field(
        description="Export timestamp"
    )
