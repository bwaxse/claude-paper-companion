"""
Query service for handling conversations with Claude.
Manages question/answer exchanges, flags, and highlights.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from ..core.database import get_db_manager
from ..core.claude import get_claude_client
from ..api.models import (
    QueryRequest,
    QueryResponse,
    FlagResponse,
    Highlight,
    HighlightList,
)


class QueryService:
    """
    Manages conversational queries with Claude.

    Handles:
    - Sending queries to Claude with paper context
    - Storing conversation exchanges
    - Flagging important exchanges
    - Managing text highlights
    """

    def __init__(self, db_manager=None, claude_client=None):
        """
        Initialize query service.

        Args:
            db_manager: Database manager (optional)
            claude_client: Claude client (optional)
        """
        self.db = db_manager or get_db_manager()
        self.claude = claude_client or get_claude_client()

    async def query_paper(
        self,
        session_id: str,
        request: QueryRequest
    ) -> QueryResponse:
        """
        Ask a question about the paper.

        Args:
            session_id: Session identifier
            request: Query request with question and optional context

        Returns:
            QueryResponse with Claude's answer

        Raises:
            ValueError: If session not found
        """
        # Get session and full text
        async with self.db.get_connection() as db:
            # Verify session exists and get text
            cursor = await db.execute(
                "SELECT full_text FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = await cursor.fetchone()

            if not row:
                raise ValueError(f"Session not found: {session_id}")

            full_text = row[0]

            # Get conversation history
            cursor = await db.execute(
                """
                SELECT role, content FROM conversations
                WHERE session_id = ? AND exchange_id > 0
                ORDER BY exchange_id, id
                """,
                (session_id,)
            )
            history_rows = await cursor.fetchall()

        # Build conversation context
        messages = []
        for role, content in history_rows:
            messages.append({
                "role": role,
                "content": content
            })

        # Add current query
        query_content = request.query
        if request.highlighted_text:
            query_content = f"{request.query}\n\nHighlighted text: {request.highlighted_text}"
        if request.page_number:
            query_content += f"\n(Page {request.page_number})"

        messages.append({
            "role": "user",
            "content": query_content
        })

        # Get response from Claude
        response_text, usage_stats = await self.claude.query(
            messages=messages,
            paper_text=full_text,
            use_sonnet=request.use_sonnet
        )

        # Get next exchange ID
        async with self.db.transaction() as db:
            cursor = await db.execute(
                "SELECT MAX(exchange_id) FROM conversations WHERE session_id = ?",
                (session_id,)
            )
            row = await cursor.fetchone()
            next_exchange_id = (row[0] or 0) + 1

            # Store user query
            await db.execute(
                """
                INSERT INTO conversations
                (session_id, exchange_id, role, content, highlighted_text, page_number, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    next_exchange_id,
                    "user",
                    request.query,
                    request.highlighted_text,
                    request.page_number,
                    datetime.utcnow()
                )
            )

            # Store assistant response
            await db.execute(
                """
                INSERT INTO conversations
                (session_id, exchange_id, role, content, model, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    next_exchange_id,
                    "assistant",
                    response_text,
                    usage_stats['model'],
                    datetime.utcnow()
                )
            )

            # Update session timestamp
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.utcnow(), session_id)
            )

        return QueryResponse(
            exchange_id=next_exchange_id,
            response=response_text,
            model_used=usage_stats['model'],
            usage=usage_stats
        )

    async def flag_exchange(
        self,
        session_id: str,
        exchange_id: int,
        note: Optional[str] = None
    ) -> FlagResponse:
        """
        Flag an exchange for later review.

        Args:
            session_id: Session identifier
            exchange_id: Exchange ID to flag
            note: Optional note about why flagged

        Returns:
            FlagResponse with success status

        Raises:
            ValueError: If session or exchange not found
        """
        async with self.db.transaction() as db:
            # Verify exchange exists
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM conversations
                WHERE session_id = ? AND exchange_id = ?
                """,
                (session_id, exchange_id)
            )
            count = (await cursor.fetchone())[0]

            if count == 0:
                raise ValueError(f"Exchange {exchange_id} not found in session {session_id}")

            # Check if already flagged
            cursor = await db.execute(
                """
                SELECT id FROM flags
                WHERE session_id = ? AND exchange_id = ?
                """,
                (session_id, exchange_id)
            )
            existing = await cursor.fetchone()

            if existing:
                # Already flagged, update note if provided
                if note is not None:
                    await db.execute(
                        "UPDATE flags SET note = ? WHERE id = ?",
                        (note, existing[0])
                    )
                return FlagResponse(
                    success=True,
                    message="Exchange already flagged, note updated",
                    flag_id=existing[0]
                )

            # Create new flag
            cursor = await db.execute(
                """
                INSERT INTO flags (session_id, exchange_id, note, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, exchange_id, note, datetime.utcnow())
            )

            flag_id = cursor.lastrowid

        return FlagResponse(
            success=True,
            message="Exchange flagged successfully",
            flag_id=flag_id
        )

    async def unflag_exchange(
        self,
        session_id: str,
        exchange_id: int
    ) -> FlagResponse:
        """
        Remove flag from an exchange.

        Args:
            session_id: Session identifier
            exchange_id: Exchange ID to unflag

        Returns:
            FlagResponse with success status
        """
        async with self.db.transaction() as db:
            # Delete flag
            cursor = await db.execute(
                """
                DELETE FROM flags
                WHERE session_id = ? AND exchange_id = ?
                """,
                (session_id, exchange_id)
            )

            if cursor.rowcount == 0:
                return FlagResponse(
                    success=False,
                    message="Exchange was not flagged",
                    flag_id=None
                )

        return FlagResponse(
            success=True,
            message="Flag removed successfully",
            flag_id=None
        )

    async def add_highlight(
        self,
        session_id: str,
        text: str,
        page_number: Optional[int] = None,
        exchange_id: Optional[int] = None
    ) -> Highlight:
        """
        Add a text highlight.

        Args:
            session_id: Session identifier
            text: Highlighted text
            page_number: Optional page number
            exchange_id: Optional associated exchange

        Returns:
            Highlight with ID and timestamp

        Raises:
            ValueError: If session not found
        """
        async with self.db.transaction() as db:
            # Verify session exists
            cursor = await db.execute(
                "SELECT COUNT(*) FROM sessions WHERE id = ?",
                (session_id,)
            )
            if (await cursor.fetchone())[0] == 0:
                raise ValueError(f"Session not found: {session_id}")

            # Insert highlight
            now = datetime.utcnow()
            cursor = await db.execute(
                """
                INSERT INTO highlights (session_id, text, page_number, exchange_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, text, page_number, exchange_id, now)
            )

            highlight_id = cursor.lastrowid

        return Highlight(
            id=highlight_id,
            text=text,
            page_number=page_number,
            exchange_id=exchange_id,
            created_at=now.isoformat()
        )

    async def get_highlights(
        self,
        session_id: str
    ) -> HighlightList:
        """
        Get all highlights for a session.

        Args:
            session_id: Session identifier

        Returns:
            HighlightList with all highlights
        """
        async with self.db.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT id, text, page_number, exchange_id, created_at
                FROM highlights
                WHERE session_id = ?
                ORDER BY created_at DESC
                """,
                (session_id,)
            )
            rows = await cursor.fetchall()

            highlights = []
            for row in rows:
                highlights.append(Highlight(
                    id=row[0],
                    text=row[1],
                    page_number=row[2],
                    exchange_id=row[3],
                    created_at=row[4] if row[4] else datetime.utcnow().isoformat()
                ))

            return HighlightList(
                highlights=highlights,
                total=len(highlights)
            )

    async def delete_highlight(
        self,
        session_id: str,
        highlight_id: int
    ) -> bool:
        """
        Delete a highlight.

        Args:
            session_id: Session identifier
            highlight_id: Highlight ID

        Returns:
            True if deleted, False if not found
        """
        async with self.db.transaction() as db:
            cursor = await db.execute(
                """
                DELETE FROM highlights
                WHERE id = ? AND session_id = ?
                """,
                (highlight_id, session_id)
            )

            return cursor.rowcount > 0


# Global instance
_query_service: Optional[QueryService] = None


def get_query_service() -> QueryService:
    """Get global query service instance (singleton)."""
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service
