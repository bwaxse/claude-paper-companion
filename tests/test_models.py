"""
Tests for Pydantic models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from web.api.models import (
    # Session models
    SessionCreate,
    SessionResponse,
    SessionSummary,
    SessionList,
    SessionDetail,
    SessionDelete,
    # Query models
    QueryRequest,
    QueryResponse,
    FlagRequest,
    FlagResponse,
    HighlightCreate,
    HighlightResponse,
    ConversationHistory,
    # Metadata models
    PaperMetadata,
    InsightCategory,
    SessionInsights,
    ZoteroItem,
    ZoteroSearchResult,
    ExportData,
)


class TestSessionModels:
    """Test session-related models."""

    def test_session_create_with_zotero(self):
        """Test SessionCreate with Zotero key."""
        data = {
            "zotero_key": "ABC123XY",
            "filename": None
        }
        model = SessionCreate(**data)
        assert model.zotero_key == "ABC123XY"
        assert model.filename is None

    def test_session_create_with_filename(self):
        """Test SessionCreate with filename."""
        data = {
            "zotero_key": None,
            "filename": "my_paper.pdf"
        }
        model = SessionCreate(**data)
        assert model.zotero_key is None
        assert model.filename == "my_paper.pdf"

    def test_session_create_invalid_zotero_key(self):
        """Test that invalid Zotero key is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SessionCreate(zotero_key="ABC")
        assert "at least 6 characters" in str(exc_info.value)

    def test_session_response(self):
        """Test SessionResponse model."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "filename": "paper.pdf",
            "initial_analysis": "Analysis text here",
            "created_at": datetime.now(),
            "zotero_key": "ABC123XY"
        }
        model = SessionResponse(**data)
        assert model.session_id == data["session_id"]
        assert model.filename == data["filename"]
        assert model.zotero_key == "ABC123XY"

    def test_session_summary(self):
        """Test SessionSummary model."""
        data = {
            "session_id": "550e8400",
            "filename": "paper.pdf",
            "created_at": datetime.now(),
            "exchange_count": 10,
            "flag_count": 2
        }
        model = SessionSummary(**data)
        assert model.exchange_count == 10
        assert model.flag_count == 2

    def test_session_list(self):
        """Test SessionList model."""
        summary = SessionSummary(
            session_id="550e8400",
            filename="paper.pdf",
            created_at=datetime.now(),
            exchange_count=5,
            flag_count=1
        )
        data = {
            "sessions": [summary],
            "total": 1,
            "limit": 10,
            "offset": 0
        }
        model = SessionList(**data)
        assert len(model.sessions) == 1
        assert model.total == 1

    def test_session_detail(self):
        """Test SessionDetail model."""
        data = {
            "session_id": "550e8400",
            "filename": "paper.pdf",
            "initial_analysis": "Analysis",
            "created_at": datetime.now(),
            "exchanges": [{"user": "question", "assistant": "answer"}],
            "flags": [],
            "highlights": [],
            "total_exchanges": 1,
            "total_flags": 0,
            "total_highlights": 0
        }
        model = SessionDetail(**data)
        assert model.total_exchanges == 1
        assert len(model.exchanges) == 1

    def test_session_delete(self):
        """Test SessionDelete model."""
        data = {
            "session_id": "550e8400",
            "deleted": True,
            "message": "Session deleted"
        }
        model = SessionDelete(**data)
        assert model.deleted is True


class TestQueryModels:
    """Test query-related models."""

    def test_query_request_basic(self):
        """Test basic QueryRequest."""
        data = {
            "query": "What is the main finding?",
            "use_sonnet": True
        }
        model = QueryRequest(**data)
        assert model.query == "What is the main finding?"
        assert model.use_sonnet is True
        assert model.highlighted_text is None
        assert model.page is None

    def test_query_request_with_context(self):
        """Test QueryRequest with highlighted text and page."""
        data = {
            "query": "Explain this",
            "highlighted_text": "The attention mechanism...",
            "page": 5,
            "use_sonnet": False
        }
        model = QueryRequest(**data)
        assert model.highlighted_text == "The attention mechanism..."
        assert model.page == 5
        assert model.use_sonnet is False

    def test_query_request_empty_query(self):
        """Test that empty query is rejected."""
        with pytest.raises(ValidationError):
            QueryRequest(query="")

    def test_query_request_invalid_page(self):
        """Test that page < 1 is rejected."""
        with pytest.raises(ValidationError):
            QueryRequest(query="test", page=0)

    def test_query_response(self):
        """Test QueryResponse model."""
        data = {
            "exchange_id": 42,
            "response": "The main limitation is...",
            "model_used": "claude-3-5-sonnet-20241022",
            "input_tokens": 1500,
            "output_tokens": 250,
            "cost": 0.0082
        }
        model = QueryResponse(**data)
        assert model.exchange_id == 42
        assert model.input_tokens == 1500
        assert model.cost == 0.0082

    def test_flag_request(self):
        """Test FlagRequest model."""
        data = {
            "exchange_id": 10,
            "note": "Important insight"
        }
        model = FlagRequest(**data)
        assert model.exchange_id == 10
        assert model.note == "Important insight"

    def test_flag_response(self):
        """Test FlagResponse model."""
        data = {
            "flag_id": 1,
            "exchange_id": 10,
            "flagged": True,
            "message": "Exchange flagged"
        }
        model = FlagResponse(**data)
        assert model.flagged is True

    def test_highlight_create(self):
        """Test HighlightCreate model."""
        data = {
            "text": "Important passage to highlight",
            "page_number": 3,
            "exchange_id": 5,
            "note": "Key finding"
        }
        model = HighlightCreate(**data)
        assert model.text == "Important passage to highlight"
        assert model.page_number == 3

    def test_highlight_create_minimal(self):
        """Test HighlightCreate with minimal data."""
        data = {
            "text": "Highlighted text"
        }
        model = HighlightCreate(**data)
        assert model.text == "Highlighted text"
        assert model.page_number is None
        assert model.exchange_id is None

    def test_highlight_response(self):
        """Test HighlightResponse model."""
        data = {
            "highlight_id": 1,
            "text": "Highlighted text",
            "page_number": 3,
            "created_at": "2025-11-15T10:30:00Z"
        }
        model = HighlightResponse(**data)
        assert model.highlight_id == 1

    def test_conversation_history(self):
        """Test ConversationHistory model."""
        data = {
            "session_id": "550e8400",
            "exchanges": [
                {"user": "question 1", "assistant": "answer 1"},
                {"user": "question 2", "assistant": "answer 2"}
            ],
            "total_exchanges": 2,
            "total_cost": 0.015
        }
        model = ConversationHistory(**data)
        assert len(model.exchanges) == 2
        assert model.total_cost == 0.015


class TestMetadataModels:
    """Test metadata-related models."""

    def test_paper_metadata(self):
        """Test PaperMetadata model."""
        data = {
            "title": "Attention Is All You Need",
            "authors": "Vaswani et al.",
            "doi": "10.48550/arXiv.1706.03762",
            "arxiv_id": "1706.03762",
            "publication_date": "2017",
            "journal": "NeurIPS"
        }
        model = PaperMetadata(**data)
        assert model.title == "Attention Is All You Need"
        assert model.arxiv_id == "1706.03762"

    def test_paper_metadata_minimal(self):
        """Test PaperMetadata with minimal data."""
        model = PaperMetadata()
        assert model.title is None
        assert model.authors is None

    def test_insight_category(self):
        """Test InsightCategory model."""
        data = {
            "category": "strengths",
            "items": ["Strong methodology", "Novel approach"]
        }
        model = InsightCategory(**data)
        assert model.category == "strengths"
        assert len(model.items) == 2

    def test_session_insights(self):
        """Test SessionInsights model."""
        data = {
            "session_id": "550e8400",
            "strengths": ["Good design"],
            "weaknesses": ["Limited sample size"],
            "methodological_notes": ["Used RCT"],
            "key_findings": ["Finding 1"],
            "open_questions": ["Question 1"],
            "applications": ["Can be applied to X"],
            "total_exchanges": 15,
            "flagged_exchanges": 3,
            "extracted_at": "2025-11-15T10:30:00Z"
        }
        model = SessionInsights(**data)
        assert len(model.strengths) == 1
        assert model.total_exchanges == 15

    def test_zotero_item(self):
        """Test ZoteroItem model."""
        data = {
            "key": "ABC123XY",
            "title": "Paper Title",
            "item_type": "journalArticle",
            "creators": [{"firstName": "John", "lastName": "Doe"}],
            "publication_title": "Nature",
            "tags": ["ML", "AI"]
        }
        model = ZoteroItem(**data)
        assert model.key == "ABC123XY"
        assert len(model.tags) == 2

    def test_zotero_search_result(self):
        """Test ZoteroSearchResult model."""
        item = ZoteroItem(
            key="ABC123",
            title="Test Paper",
            item_type="journalArticle",
            creators=[]
        )
        data = {
            "items": [item],
            "total": 1,
            "query": "machine learning"
        }
        model = ZoteroSearchResult(**data)
        assert model.total == 1
        assert model.query == "machine learning"

    def test_export_data(self):
        """Test ExportData model."""
        data = {
            "session": {"session_id": "550e8400"},
            "conversation": [{"user": "q", "assistant": "a"}],
            "flags": [],
            "highlights": [],
            "export_format": "json",
            "exported_at": "2025-11-15T10:30:00Z"
        }
        model = ExportData(**data)
        assert model.export_format == "json"
        assert len(model.conversation) == 1


class TestModelValidation:
    """Test model validation rules."""

    def test_negative_values_rejected(self):
        """Test that negative values are rejected where appropriate."""
        # Negative page number
        with pytest.raises(ValidationError):
            QueryRequest(query="test", page=-1)

        # Negative exchange_id
        with pytest.raises(ValidationError):
            FlagRequest(exchange_id=-1)

        # Negative total
        with pytest.raises(ValidationError):
            SessionList(sessions=[], total=-1, limit=10)

    def test_string_length_validation(self):
        """Test string length limits."""
        # Query too long
        with pytest.raises(ValidationError):
            QueryRequest(query="x" * 10000)

        # Filename too long
        with pytest.raises(ValidationError):
            SessionCreate(filename="x" * 500)

    def test_required_fields(self):
        """Test that required fields are enforced."""
        # QueryRequest requires query
        with pytest.raises(ValidationError):
            QueryRequest()

        # SessionResponse requires multiple fields
        with pytest.raises(ValidationError):
            SessionResponse(session_id="123")  # Missing other required fields


class TestModelSerialization:
    """Test model serialization to JSON."""

    def test_session_response_json(self):
        """Test SessionResponse serialization."""
        model = SessionResponse(
            session_id="550e8400",
            filename="paper.pdf",
            initial_analysis="Analysis",
            created_at=datetime(2025, 11, 15, 10, 30, 0)
        )
        json_data = model.model_dump()
        assert json_data["session_id"] == "550e8400"
        assert "created_at" in json_data

    def test_query_request_json(self):
        """Test QueryRequest serialization."""
        model = QueryRequest(
            query="What is the finding?",
            page=5
        )
        json_data = model.model_dump()
        assert json_data["query"] == "What is the finding?"
        assert json_data["page"] == 5
        assert json_data["highlighted_text"] is None

    def test_model_json_schema(self):
        """Test that models generate valid JSON schemas."""
        schema = QueryRequest.model_json_schema()
        assert "properties" in schema
        assert "query" in schema["properties"]
