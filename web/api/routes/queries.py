"""
FastAPI routes for querying papers with Claude.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Body

from ..models import (
    QueryRequest,
    QueryResponse,
    FlagResponse,
    Highlight,
    HighlightList,
)
from ...services import get_query_service


router = APIRouter(prefix="/sessions", tags=["queries"])


@router.post("/{session_id}/query", response_model=QueryResponse)
async def query_paper(
    session_id: str,
    request: QueryRequest
):
    """
    Ask a question about the paper.

    **Process:**
    - Retrieves full paper text and conversation history
    - Sends question to Claude with context
    - Stores both question and answer in conversation history
    - Returns Claude's response with usage stats

    **Args:**
    - session_id: Session identifier
    - request: Query request with question and optional context

    **Returns:**
    - QueryResponse with exchange_id, response text, model used, and usage stats

    **Raises:**
    - 404: If session not found
    - 500: If query processing fails

    **Example:**
    ```json
    {
      "query": "What is the main contribution of this paper?",
      "use_sonnet": true
    }
    ```
    """
    try:
        service = get_query_service()
        response = await service.query_paper(session_id, request)
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


@router.post("/{session_id}/exchanges/{exchange_id}/flag", response_model=FlagResponse)
async def flag_exchange(
    session_id: str,
    exchange_id: int,
    note: Optional[str] = Body(None, embed=True)
):
    """
    Flag an exchange for later review.

    **Purpose:**
    - Mark important or interesting exchanges
    - Add optional note explaining why flagged
    - Use for building insights, export, or review

    **Args:**
    - session_id: Session identifier
    - exchange_id: Exchange ID to flag
    - note: Optional note about why this exchange is important

    **Returns:**
    - FlagResponse with success status and flag_id

    **Raises:**
    - 404: If session or exchange not found

    **Example:**
    ```json
    {
      "note": "Key insight about methodology"
    }
    ```
    """
    try:
        service = get_query_service()
        response = await service.flag_exchange(session_id, exchange_id, note)
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to flag exchange: {str(e)}"
        )


@router.delete("/{session_id}/exchanges/{exchange_id}/flag", response_model=FlagResponse)
async def unflag_exchange(
    session_id: str,
    exchange_id: int
):
    """
    Remove flag from an exchange.

    **Args:**
    - session_id: Session identifier
    - exchange_id: Exchange ID to unflag

    **Returns:**
    - FlagResponse with success status

    **Note:**
    - Returns success=false if exchange was not flagged
    """
    try:
        service = get_query_service()
        response = await service.unflag_exchange(session_id, exchange_id)
        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unflag exchange: {str(e)}"
        )


@router.get("/{session_id}/highlights", response_model=HighlightList)
async def get_highlights(session_id: str):
    """
    Get all highlights for a session.

    **Returns:**
    - HighlightList with all highlights, sorted by creation time (newest first)

    **Use case:**
    - Review important passages
    - Build insights from highlighted text
    - Export annotations
    """
    try:
        service = get_query_service()
        highlights = await service.get_highlights(session_id)
        return highlights

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get highlights: {str(e)}"
        )


@router.post("/{session_id}/highlights", response_model=Highlight, status_code=status.HTTP_201_CREATED)
async def add_highlight(
    session_id: str,
    text: str = Body(..., min_length=1, max_length=5000, embed=True),
    page_number: Optional[int] = Body(None, embed=True),
    exchange_id: Optional[int] = Body(None, embed=True)
):
    """
    Add a text highlight to the session.

    **Purpose:**
    - Mark important passages for later reference
    - Optionally associate with a specific page or exchange
    - Build collection of key quotes

    **Args:**
    - session_id: Session identifier
    - text: The highlighted text (required)
    - page_number: Optional page number where text appears
    - exchange_id: Optional exchange ID if highlight relates to a Q&A

    **Returns:**
    - Highlight with ID and timestamp

    **Raises:**
    - 404: If session not found
    - 400: If text is empty or too long

    **Example:**
    ```json
    {
      "text": "Our method achieves state-of-the-art results on benchmark X",
      "page_number": 5,
      "exchange_id": 3
    }
    ```
    """
    try:
        service = get_query_service()
        highlight = await service.add_highlight(
            session_id=session_id,
            text=text,
            page_number=page_number,
            exchange_id=exchange_id
        )
        return highlight

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add highlight: {str(e)}"
        )


@router.delete("/{session_id}/highlights/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_highlight(
    session_id: str,
    highlight_id: int
):
    """
    Delete a highlight.

    **Args:**
    - session_id: Session identifier
    - highlight_id: Highlight ID to delete

    **Returns:**
    - 204 No Content on success

    **Raises:**
    - 404: If highlight not found
    """
    try:
        service = get_query_service()
        deleted = await service.delete_highlight(session_id, highlight_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Highlight {highlight_id} not found in session {session_id}"
            )

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete highlight: {str(e)}"
        )
