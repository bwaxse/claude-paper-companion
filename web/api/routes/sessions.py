"""
FastAPI routes for session management.
"""

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from ..models import (
    SessionCreate,
    SessionResponse,
    SessionList,
    SessionDetail,
)
from ...services import (
    get_session_manager,
    create_session_from_pdf as service_create_from_pdf,
    get_session as service_get_session,
    list_sessions as service_list_sessions,
    delete_session as service_delete_session,
)
from ...core.pdf_processor import PDFProcessor
from ...services.insight_extractor import get_insight_extractor
from ...core.database import get_db_manager


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/new", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    file: Optional[UploadFile] = File(None),
    zotero_key: Optional[str] = Form(None)
):
    """
    Create a new session from PDF upload or Zotero.

    **Two modes:**
    1. PDF Upload: Provide `file` parameter with PDF
    2. Zotero: Provide `zotero_key` parameter

    **Process:**
    - Extracts full text from PDF
    - Generates initial analysis with Claude (Haiku)
    - Stores session in database
    - Returns session info with initial analysis

    **Args:**
    - file: PDF file upload (multipart/form-data)
    - zotero_key: Zotero item key (alternative to file)

    **Returns:**
    - SessionResponse with session_id, filename, initial_analysis, etc.

    **Raises:**
    - 400: If neither file nor zotero_key provided, or both provided
    - 400: If file is not a PDF
    - 404: If Zotero item not found
    - 500: If processing fails
    """
    # Validate input
    if file and zotero_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'file' or 'zotero_key', not both"
        )

    if not file and not zotero_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'file' or 'zotero_key'"
        )

    session_manager = get_session_manager()

    try:
        # Create from PDF upload
        if file:
            session = await session_manager.create_session_from_pdf(file)
            return session

        # Create from Zotero
        else:
            session = await session_manager.create_session_from_zotero(zotero_key)
            return session

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("", response_model=SessionList)
async def list_all_sessions(
    limit: int = 50,
    offset: int = 0
):
    """
    List all sessions with pagination.

    **Args:**
    - limit: Maximum number of sessions to return (default: 50, max: 100)
    - offset: Number of sessions to skip (default: 0)

    **Returns:**
    - SessionList with sessions array and total count

    **Example:**
    ```
    GET /sessions?limit=20&offset=0
    ```
    """
    # Validate pagination params
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be non-negative"
        )

    try:
        sessions = await service_list_sessions(limit=limit, offset=offset)
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(session_id: str):
    """
    Get full session details including conversation history.

    **Args:**
    - session_id: Session identifier

    **Returns:**
    - SessionDetail with full conversation history

    **Raises:**
    - 404: If session not found

    **Use case:**
    - Restore session for "pick up where you left off"
    - View complete conversation history
    - Export session data
    """
    try:
        session = await service_get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )

        return session

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session_endpoint(session_id: str):
    """
    Delete a session and all associated data.

    **Args:**
    - session_id: Session identifier

    **Deletes:**
    - Session record
    - All conversation messages
    - All flags and highlights
    - Metadata
    - PDF file (if stored locally)

    **Raises:**
    - 404: If session not found

    **Returns:**
    - 204 No Content on success
    """
    try:
        deleted = await service_delete_session(session_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/{session_id}/export")
async def export_session(session_id: str):
    """
    Export session data as JSON.

    **Args:**
    - session_id: Session identifier

    **Returns:**
    - Complete session data in JSON format
    - Includes: metadata, conversation history, flags, highlights

    **Raises:**
    - 404: If session not found

    **Use case:**
    - Download session for backup
    - Share analysis with colleagues
    - Import into other tools
    """
    try:
        session = await service_get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )

        # Return session data as JSON
        # FastAPI automatically serializes Pydantic models
        return session

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export session: {str(e)}"
        )


@router.get("/{session_id}/pdf")
async def get_session_pdf(session_id: str):
    """
    Serve the PDF file for browser viewing.

    **Args:**
    - session_id: Session identifier

    **Returns:**
    - PDF file with appropriate content-type header

    **Raises:**
    - 404: If session or PDF file not found

    **Use case:**
    - Display PDF in browser using PDF.js
    - Enable text selection and highlighting in frontend
    - Direct PDF access for multi-page rendering
    """
    try:
        # Get session from database to retrieve pdf_path
        db = get_db_manager()
        session_row = await db.execute_one(
            "SELECT id, filename, pdf_path FROM sessions WHERE id = ?",
            (session_id,)
        )

        if not session_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )

        # Get PDF path
        pdf_path = dict(session_row).get("pdf_path")
        if not pdf_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF file path not found for session: {session_id}"
            )

        # Check if file exists
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF file not found at path: {pdf_path}"
            )

        # Return PDF file with proper content type
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=dict(session_row).get("filename", "paper.pdf")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve PDF: {str(e)}"
        )


@router.get("/{session_id}/outline")
async def get_session_outline(session_id: str):
    """
    Get extracted table of contents / document outline.

    **Args:**
    - session_id: Session identifier

    **Returns:**
    - List of outline items with level, title, and page number
    - Example:
      ```json
      [
        {"level": 1, "title": "Introduction", "page": 1},
        {"level": 2, "title": "Background", "page": 2},
        {"level": 1, "title": "Methods", "page": 5}
      ]
      ```

    **Raises:**
    - 404: If session or PDF file not found

    **Use case:**
    - Display navigation tree in Outline tab
    - Enable quick jump to sections
    - Show document structure
    """
    try:
        # Get session from database to retrieve pdf_path
        db = get_db_manager()
        session_row = await db.execute_one(
            "SELECT id, pdf_path FROM sessions WHERE id = ?",
            (session_id,)
        )

        if not session_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )

        # Get PDF path
        pdf_path = dict(session_row).get("pdf_path")
        if not pdf_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF file path not found for session: {session_id}"
            )

        # Check if file exists
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF file not found at path: {pdf_path}"
            )

        # Extract outline using PDFProcessor
        outline = await PDFProcessor.extract_outline(pdf_path)

        return {"outline": outline}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract outline: {str(e)}"
        )


@router.get("/{session_id}/concepts")
async def get_session_concepts(session_id: str, force: bool = False, cache_only: bool = False):
    """
    Get key concepts and insights from the conversation.

    **Args:**
    - session_id: Session identifier
    - force: If true, re-extract even if no new exchanges
    - cache_only: If true, only return cached insights (don't extract if not cached)

    **Returns:**
    - Structured insights including:
      - strengths: Paper's genuine strengths
      - weaknesses: Methodological/conceptual weaknesses
      - methodological_notes: Technical insights
      - theoretical_contributions: Conceptual advances
      - empirical_findings: Key results discussed
      - key_quotes: Most insightful exchanges
      - And more thematic categories
      - _cache_info: Contains no_new_exchanges flag if applicable

    **Raises:**
    - 404: If session not found

    **Use case:**
    - Display key concepts in Concepts tab
    - Show organized insights from conversation
    - Enable quick review of important points
    """
    try:
        # Check if session exists
        session = await service_get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )

        db = get_db_manager()
        async with db.get_connection() as conn:
            # Get current exchange count
            result = await conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE session_id = ? AND role = 'user'",
                (session_id,)
            )
            row = await result.fetchone()
            current_exchange_count = row[0] if row else 0

            # Check for cached insights
            cached = await conn.execute(
                "SELECT insights_json, exchange_count FROM insights WHERE session_id = ?",
                (session_id,)
            )
            cached_row = await cached.fetchone()

            if cached_row and not force:
                cached_insights = json.loads(cached_row[0])
                cached_exchange_count = cached_row[1]

                # If no new exchanges, return cached with warning
                if current_exchange_count <= cached_exchange_count:
                    cached_insights["_cache_info"] = {
                        "no_new_exchanges": True,
                        "cached_at": cached_insights.get("metadata", {}).get("extracted_at"),
                        "exchange_count": cached_exchange_count
                    }
                    return cached_insights

                # If cache_only, return cached even if there are new exchanges
                if cache_only:
                    return cached_insights

            # If cache_only and no cache, return null
            if cache_only:
                return None

            # Extract fresh insights
            extractor = get_insight_extractor()
            insights = await extractor.extract_insights(session_id)

            # Save to database
            insights_json = json.dumps(insights)
            await conn.execute(
                """
                INSERT INTO insights (session_id, insights_json, exchange_count)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    insights_json = excluded.insights_json,
                    exchange_count = excluded.exchange_count,
                    extracted_at = CURRENT_TIMESTAMP
                """,
                (session_id, insights_json, current_exchange_count)
            )
            await conn.commit()

        return insights

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract concepts: {str(e)}"
        )
