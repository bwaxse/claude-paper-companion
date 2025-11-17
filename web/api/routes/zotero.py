"""
FastAPI routes for Zotero integration.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ..models.zotero import (
    ZoteroSearchResponse,
    ZoteroItemSummary,
    ZoteroItem,
    ZoteroNoteRequest,
    ZoteroNoteResponse,
)
from ...services import get_zotero_service, get_session_manager, get_insight_extractor


router = APIRouter(prefix="/zotero", tags=["zotero"])


@router.get("/search", response_model=ZoteroSearchResponse)
async def search_zotero(
    query: str = Query(..., min_length=1, description="Search query (title, DOI, keywords)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return")
):
    """
    Search Zotero library for papers.

    **Capabilities:**
    - Search by title, author, DOI, or keywords
    - Returns summaries optimized for list display
    - Supports pagination with limit parameter

    **Args:**
    - query: Search query string (required)
    - limit: Maximum results (1-50, default 10)

    **Returns:**
    - ZoteroSearchResponse with matching items and total count

    **Raises:**
    - 500: If Zotero not configured or search fails

    **Example:**
    ```
    GET /zotero/search?query=attention+is+all+you+need&limit=5
    ```
    """
    try:
        service = get_zotero_service()

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Zotero is not configured. Please set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID environment variables."
            )

        items = await service.search_papers(query=query, limit=limit)

        return ZoteroSearchResponse(
            items=items,
            total=len(items)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search Zotero: {str(e)}"
        )


@router.get("/recent", response_model=List[ZoteroItemSummary])
async def list_recent_papers(
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return")
):
    """
    List recent papers from Zotero library.

    **Purpose:**
    - Browse recently added papers
    - Quick access to latest research
    - Sorted by date added (newest first)

    **Args:**
    - limit: Maximum results (1-100, default 20)

    **Returns:**
    - List of ZoteroItemSummary objects

    **Raises:**
    - 500: If Zotero not configured or fetch fails

    **Example:**
    ```
    GET /zotero/recent?limit=10
    ```
    """
    try:
        service = get_zotero_service()

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Zotero is not configured. Please set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID environment variables."
            )

        items = await service.list_recent(limit=limit)
        return items

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recent papers: {str(e)}"
        )


@router.get("/paper/{key}", response_model=ZoteroItem)
async def get_paper_details(key: str):
    """
    Get full details for a specific Zotero paper.

    **Purpose:**
    - Retrieve complete metadata for a paper
    - Get abstract, tags, publication info
    - Use before creating session or for display

    **Args:**
    - key: Zotero item key (from search results)

    **Returns:**
    - ZoteroItem with complete metadata

    **Raises:**
    - 404: If paper not found
    - 500: If Zotero not configured or fetch fails

    **Example:**
    ```
    GET /zotero/paper/ABC123XY
    ```
    """
    try:
        service = get_zotero_service()

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Zotero is not configured. Please set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID environment variables."
            )

        item = await service.get_paper_by_key(key)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper with key '{key}' not found in Zotero library"
            )

        return item

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get paper details: {str(e)}"
        )


@router.post("/save-insights", response_model=ZoteroNoteResponse)
async def save_insights_to_zotero(request: ZoteroNoteRequest):
    """
    Save session insights as a note attached to Zotero paper.

    **Workflow:**
    1. Retrieves session data (exchanges, flags, highlights)
    2. Formats insights as HTML note
    3. Attaches note to specified Zotero item
    4. Adds tags for organization

    **Args:**
    - request: Contains session_id, parent_item_key, and optional tags

    **Returns:**
    - ZoteroNoteResponse with success status and note_key

    **Raises:**
    - 404: If session not found
    - 500: If Zotero not configured or save fails

    **Example:**
    ```json
    {
      "session_id": "abc123def456",
      "parent_item_key": "ABC123XY",
      "tags": ["claude-analyzed", "critical-appraisal"]
    }
    ```

    **Note Format:**
    - Initial analysis summary
    - Flagged exchanges (Q&A marked as important)
    - Highlights with page numbers
    - Metadata (session date, model used)
    """
    try:
        # Get services
        zotero_service = get_zotero_service()
        session_manager = get_session_manager()

        if not zotero_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Zotero is not configured. Please set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID environment variables."
            )

        # Get session data
        session = await session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{request.session_id}' not found"
            )

        # Extract insights from session using InsightExtractor
        insight_service = get_insight_extractor()
        insights = await insight_service.extract_insights(request.session_id)

        # Format insights as HTML for Zotero
        note_html = insight_service.format_insights_html(insights)

        # Save note to Zotero
        success = await zotero_service.save_insights_to_note(
            parent_item_key=request.parent_item_key,
            note_html=note_html,
            tags=request.tags
        )

        if success:
            return ZoteroNoteResponse(
                success=True,
                message="Insights saved successfully to Zotero",
                note_key=None  # pyzotero doesn't return the created note key easily
            )
        else:
            return ZoteroNoteResponse(
                success=False,
                message="Failed to save note to Zotero. Check API key and item key.",
                note_key=None
            )

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
            detail=f"Failed to save insights: {str(e)}"
        )


@router.get("/related", response_model=List[ZoteroItemSummary])
async def get_related_papers(
    tags: str = Query(..., description="Comma-separated list of tags to search for"),
    limit: int = Query(5, ge=1, le=20, description="Maximum results per tag")
):
    """
    Find related papers in Zotero library based on tags.

    **Use Case:**
    - Discover papers with similar topics
    - Find related research after analyzing a paper
    - Build reading lists around themes

    **Args:**
    - tags: Comma-separated tag list (e.g., "machine-learning,nlp")
    - limit: Maximum results per tag (1-20, default 5)

    **Returns:**
    - List of ZoteroItemSummary objects with matching tags

    **Raises:**
    - 500: If Zotero not configured or search fails

    **Example:**
    ```
    GET /zotero/related?tags=transformer,attention&limit=5
    ```

    **Note:**
    - Results may contain duplicates if papers match multiple tags
    - Papers are returned in no specific order
    """
    try:
        service = get_zotero_service()

        if not service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Zotero is not configured. Please set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID environment variables."
            )

        # Parse tags from comma-separated string
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        if not tag_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one tag is required"
            )

        items = await service.get_related_papers(tags=tag_list, limit=limit)
        return items

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find related papers: {str(e)}"
        )
