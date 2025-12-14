"""
FastAPI routes for Notion integration.
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from ..models.notion import (
    NotionAuthResponse,
    NotionProjectList,
    NotionProjectContext,
    NotionRelevanceResponse,
    NotionContentResponse,
    NotionExportRequest,
    NotionExportResponse,
)
from ...services import (
    get_notion_client,
    get_notion_exporter,
    get_session_manager,
)
from ...core.database import get_db_manager

router = APIRouter(prefix="/notion", tags=["notion"])


@router.get("/auth-url")
async def get_notion_auth_url(state: Optional[str] = Query(None)):
    """
    Get Notion OAuth authorization URL.

    **Args:**
    - state: Optional CSRF state parameter

    **Returns:**
    - Authorization URL to redirect user to

    **Raises:**
    - 500: If Notion OAuth not configured

    **Example:**
    ```
    GET /notion/auth-url
    ```
    """
    try:
        client = get_notion_client()

        if not client.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Notion OAuth not configured. Set NOTION_CLIENT_ID, NOTION_CLIENT_SECRET, and NOTION_REDIRECT_URI in .env"
            )

        auth_url = client.get_authorization_url(state=state)

        return {"auth_url": auth_url}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate authorization URL: {str(e)}"
        )


@router.get("/callback")
async def notion_oauth_callback(
    code: str = Query(..., description="Authorization code from Notion"),
    state: Optional[str] = Query(None, description="CSRF state parameter")
):
    """
    Handle Notion OAuth callback.

    **Args:**
    - code: Authorization code from Notion
    - state: Optional CSRF state parameter

    **Returns:**
    - Redirects to frontend with success/error

    **Process:**
    - Exchanges code for access token
    - Stores token in environment (for single-user setup)
    - Redirects back to frontend

    **Example:**
    ```
    GET /notion/callback?code=abc123&state=xyz
    ```
    """
    try:
        client = get_notion_client()
        token_data = await client.exchange_code_for_token(code)

        # For single-user setup, user should manually add token to .env
        # Display instructions or redirect with token
        return NotionAuthResponse(
            success=True,
            access_token=token_data["access_token"],
            workspace_name=token_data.get("workspace_name"),
            message="Authentication successful! Add NOTION_ACCESS_TOKEN to your .env file and restart the server."
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.get("/projects", response_model=NotionProjectList)
async def list_notion_projects(
    query: Optional[str] = Query(None, description="Optional search query")
):
    """
    List user's Notion pages (potential research projects).

    **Args:**
    - query: Optional search query

    **Returns:**
    - List of Notion pages with {id, title, url}

    **Raises:**
    - 401: If not authenticated with Notion
    - 500: If fetch fails

    **Example:**
    ```
    GET /notion/projects
    GET /notion/projects?query=research
    ```
    """
    try:
        client = get_notion_client()

        if not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion. Please complete OAuth flow first."
            )

        projects = await client.search_projects(query=query)

        return NotionProjectList(projects=projects, total=len(projects))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/project/{page_id}/context", response_model=NotionProjectContext)
async def get_project_context(
    page_id: str,
    force_refresh: bool = Query(False, description="Force refresh cached context")
):
    """
    Get project context (hypothesis, themes, etc.).

    **Args:**
    - page_id: Notion page ID
    - force_refresh: If True, bypass cache and re-fetch

    **Returns:**
    - Project context with title, hypothesis, themes, raw_content

    **Raises:**
    - 401: If not authenticated
    - 404: If page not found
    - 500: If fetch fails

    **Caching:**
    - Contexts are cached for 24 hours
    - Use force_refresh=true to clear cache

    **Example:**
    ```
    GET /notion/project/abc123/context
    GET /notion/project/abc123/context?force_refresh=true
    ```
    """
    try:
        client = get_notion_client()

        if not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion"
            )

        exporter = get_notion_exporter()
        context = await exporter.get_project_context(
            page_id=page_id,
            force_refresh=force_refresh
        )

        return NotionProjectContext(**context)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project context: {str(e)}"
        )


@router.post("/generate-relevance", response_model=NotionRelevanceResponse)
async def generate_relevance(
    session_id: str = Query(..., description="Session ID"),
    page_id: str = Query(..., description="Notion page ID")
):
    """
    Generate proposed relevance statement and theme suggestion.

    **Args:**
    - session_id: Session ID with insights
    - page_id: Notion project page ID

    **Returns:**
    - Suggested theme and relevance statement

    **Requirements:**
    - Session must have extracted insights
    - Project context must be fetchable

    **Uses:**
    - Claude Haiku for speed
    - Bennett's voice from bjw-voice-modeling skill

    **Example:**
    ```
    POST /notion/generate-relevance?session_id=abc123&page_id=xyz789
    ```
    """
    try:
        # Check authentication
        client = get_notion_client()
        if not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion"
            )

        # Get session insights
        db = get_db_manager()
        async with db.get_connection() as conn:
            result = await conn.execute(
                "SELECT insights_json FROM insights WHERE session_id = ?",
                (session_id,)
            )
            row = await result.fetchone()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No insights found for session. Please extract insights first."
                )

            insights = json.loads(row[0])

        # Get project context
        exporter = get_notion_exporter()
        project_context = await exporter.get_project_context(page_id)

        # Generate relevance
        relevance_data = await exporter.generate_relevance(
            session_insights=insights,
            project_context=project_context
        )

        return NotionRelevanceResponse(**relevance_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate relevance: {str(e)}"
        )


@router.post("/generate-content", response_model=NotionContentResponse)
async def generate_export_content(
    session_id: str = Query(..., description="Session ID"),
    page_id: str = Query(..., description="Notion page ID"),
    theme: str = Query(..., description="Theme name"),
    relevance: str = Query(..., description="Relevance statement"),
    include_session_notes: bool = Query(True, description="Include session notes")
):
    """
    Generate full export content for Notion.

    **Args:**
    - session_id: Session ID with insights
    - page_id: Notion project page ID
    - theme: Confirmed theme (can be "NEW: Theme Name")
    - relevance: Confirmed relevance statement
    - include_session_notes: Whether to include collapsed session notes

    **Returns:**
    - Formatted content ready for export

    **Uses:**
    - Claude Sonnet for quality
    - Bennett's voice characteristics

    **Example:**
    ```
    POST /notion/generate-content?session_id=abc&page_id=xyz&theme=Autoencoders&relevance=...
    ```
    """
    try:
        # Check authentication
        client = get_notion_client()
        if not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion"
            )

        # Get session insights and metadata
        db = get_db_manager()
        async with db.get_connection() as conn:
            result = await conn.execute(
                "SELECT insights_json FROM insights WHERE session_id = ?",
                (session_id,)
            )
            row = await result.fetchone()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No insights found for session"
                )

            insights = json.loads(row[0])

            # Get metadata from database (more reliable than Claude extraction)
            metadata_result = await conn.execute(
                "SELECT title, authors, publication_date FROM metadata WHERE session_id = ?",
                (session_id,)
            )
            metadata_row = await metadata_result.fetchone()

            # Merge database metadata with insights (prefer database)
            if metadata_row and metadata_row[0]:
                if "bibliographic" not in insights:
                    insights["bibliographic"] = {}
                insights["bibliographic"]["title"] = metadata_row[0]
                if metadata_row[1]:
                    insights["bibliographic"]["authors"] = metadata_row[1]
                if metadata_row[2]:
                    # Extract year from publication_date
                    pub_date = metadata_row[2]
                    # Try to extract year (might be "2023", "2023-01-01", etc.)
                    import re
                    year_match = re.search(r'\d{4}', pub_date)
                    if year_match:
                        insights["bibliographic"]["year"] = year_match.group(0)

        # Get project context
        exporter = get_notion_exporter()
        project_context = await exporter.get_project_context(page_id)

        # Generate content
        content = await exporter.generate_export_content(
            session_insights=insights,
            project_context=project_context,
            confirmed_theme=theme,
            confirmed_relevance=relevance,
            include_session_notes=include_session_notes
        )

        return NotionContentResponse(content=content)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate content: {str(e)}"
        )


@router.post("/export", response_model=NotionExportResponse)
async def export_to_notion(request: NotionExportRequest):
    """
    Export content to Notion page.

    **Args:**
    - request: NotionExportRequest with session_id, page_id, theme, content, literature_review_heading

    **Returns:**
    - Success status and Notion page URL

    **Raises:**
    - 401: If not authenticated
    - 404: If Literature Review heading not found
    - 500: If export fails

    **Example:**
    ```
    POST /notion/export
    {
      "session_id": "abc",
      "page_id": "xyz",
      "theme": "Autoencoders",
      "content": "...",
      "literature_review_heading": "Literature Review"
    }
    ```
    """
    try:
        # Check authentication
        client = get_notion_client()
        if not client.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Notion"
            )

        # Export to Notion
        exporter = get_notion_exporter()
        url = await exporter.export_to_notion(
            page_id=request.page_id,
            theme=request.theme,
            content=request.content,
            literature_review_heading=request.literature_review_heading
        )

        return NotionExportResponse(
            success=True,
            page_url=url,
            message="Successfully exported to Notion"
        )

    except ValueError as e:
        # Literature Review heading not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export to Notion: {str(e)}"
        )
