"""
Session management service for Paper Companion.
Handles session creation, retrieval, and lifecycle management.
"""

import secrets
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile
import shutil

from fastapi import UploadFile

from ..core.database import get_db_manager
from ..core.pdf_processor import PDFProcessor
from ..core.claude import get_claude_client
from ..api.models import (
    SessionResponse,
    SessionListItem,
    SessionList,
    SessionDetail,
    ConversationMessage,
    SessionMetadata,
)
from .zotero_service import get_zotero_service


class SessionManager:
    """
    Manages paper analysis sessions.

    Handles:
    - Session creation from PDF uploads or Zotero
    - PDF text extraction and initial analysis
    - Session storage and retrieval
    - Conversation history management
    - Session deletion
    """

    def __init__(self, db_manager=None, pdf_processor=None, claude_client=None):
        """
        Initialize session manager with database and services.

        Args:
            db_manager: Database manager (optional, uses default if not provided)
            pdf_processor: PDF processor (optional, uses default if not provided)
            claude_client: Claude client (optional, uses default if not provided)
        """
        self.db = db_manager or get_db_manager()
        self.pdf_processor = pdf_processor or PDFProcessor()
        self.claude = claude_client or get_claude_client()

    def _generate_session_id(self) -> str:
        """Generate unique session identifier."""
        return secrets.token_urlsafe(16)

    async def create_session_from_pdf(
        self,
        file: UploadFile,
        save_pdf: bool = True
    ) -> SessionResponse:
        """
        Create a new session from PDF upload.

        Args:
            file: Uploaded PDF file
            save_pdf: Whether to save PDF to disk (default: True)

        Returns:
            SessionResponse with session info and initial analysis

        Raises:
            ValueError: If file is not a PDF or processing fails
        """
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise ValueError("File must be a PDF")

        # Generate session ID
        session_id = self._generate_session_id()

        # Save PDF temporarily for processing
        temp_pdf_path = None
        saved_pdf_path = None

        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                # Copy uploaded file to temp
                shutil.copyfileobj(file.file, temp_file)
                temp_pdf_path = temp_file.name

            # Extract PDF content
            full_text = await self.pdf_processor.extract_text(temp_pdf_path)
            metadata = await self.pdf_processor.extract_metadata(temp_pdf_path)
            page_count = metadata.get('page_count', 0)

            # Get initial analysis from Claude (Haiku)
            initial_analysis, usage_stats = await self.claude.initial_analysis(
                pdf_path=temp_pdf_path,
                pdf_text=full_text
            )

            # Save PDF to permanent location if requested
            if save_pdf:
                pdf_dir = Path("data/pdfs")
                pdf_dir.mkdir(parents=True, exist_ok=True)
                saved_pdf_path = str(pdf_dir / f"{session_id}.pdf")
                shutil.copy2(temp_pdf_path, saved_pdf_path)

            # Store session in database
            now = datetime.utcnow()
            async with self.db.transaction() as db:
                # Insert session
                await db.execute(
                    """
                    INSERT INTO sessions (id, filename, pdf_path, full_text, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, file.filename, saved_pdf_path, full_text, now, now)
                )

                # Store initial analysis as first conversation message
                await db.execute(
                    """
                    INSERT INTO conversations (session_id, exchange_id, role, content, model, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, 0, "assistant", initial_analysis, usage_stats['model'], now)
                )

                # Store PDF metadata if available
                if metadata.get('title') or metadata.get('author'):
                    await db.execute(
                        """
                        INSERT INTO metadata (session_id, title, authors)
                        VALUES (?, ?, ?)
                        """,
                        (session_id, metadata.get('title'), metadata.get('author'))
                    )

            # Return session response
            return SessionResponse(
                session_id=session_id,
                filename=file.filename,
                initial_analysis=initial_analysis,
                created_at=now,
                updated_at=now,
                page_count=page_count
            )

        finally:
            # Clean up temp file
            if temp_pdf_path and Path(temp_pdf_path).exists():
                Path(temp_pdf_path).unlink()

    async def create_session_from_zotero(
        self,
        zotero_key: str
    ) -> SessionResponse:
        """
        Create a new session from Zotero library item.

        Args:
            zotero_key: Zotero item key

        Returns:
            SessionResponse with session info and initial analysis

        Raises:
            ValueError: If Zotero item not found or no PDF attached
        """
        # Get Zotero service
        zotero = get_zotero_service()

        if not zotero.is_configured():
            raise ValueError("Zotero is not configured. Please provide API key and library ID in settings.")

        # Get Zotero item
        item = await zotero.get_paper_by_key(zotero_key)
        if not item:
            raise ValueError(f"Zotero item not found: {zotero_key}")

        # Get PDF path
        pdf_path = await zotero.get_pdf_path(zotero_key)
        if not pdf_path:
            raise ValueError(f"No PDF attachment found for Zotero item: {zotero_key}")

        # Generate session ID
        session_id = self._generate_session_id()

        # Extract PDF content
        full_text = await self.pdf_processor.extract_text(pdf_path)
        metadata = await self.pdf_processor.extract_metadata(pdf_path)
        page_count = metadata.get('page_count', 0)

        # Get initial analysis from Claude (Haiku)
        initial_analysis, usage_stats = await self.claude.initial_analysis(
            pdf_path=pdf_path,
            pdf_text=full_text
        )

        # Store session in database
        now = datetime.utcnow()
        async with self.db.transaction() as db:
            # Insert session
            await db.execute(
                """
                INSERT INTO sessions (id, filename, zotero_key, pdf_path, full_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, item.data.title or "Untitled", zotero_key, pdf_path, full_text, now, now)
            )

            # Store initial analysis
            await db.execute(
                """
                INSERT INTO conversations (session_id, exchange_id, role, content, model, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, 0, "assistant", initial_analysis, usage_stats['model'], now)
            )

            # Store Zotero metadata if available
            if item.data.title or item.data.DOI:
                # Format authors as JSON string
                authors_json = None
                if item.data.creators:
                    authors_list = [
                        f"{c.lastName}, {c.firstName}" if c.lastName and c.firstName
                        else c.name or c.lastName or c.firstName or "Unknown"
                        for c in item.data.creators
                    ]
                    import json
                    authors_json = json.dumps(authors_list)

                await db.execute(
                    """
                    INSERT INTO metadata (session_id, title, authors, doi, publication_date, journal, abstract)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        item.data.title,
                        authors_json,
                        item.data.DOI,
                        item.data.date,
                        item.data.publicationTitle,
                        item.data.abstractNote
                    )
                )

        # Return session response
        return SessionResponse(
            session_id=session_id,
            filename=item.data.title or "Untitled",
            initial_analysis=initial_analysis,
            created_at=now,
            updated_at=now,
            zotero_key=zotero_key,
            page_count=page_count
        )

    async def get_session(self, session_id: str) -> Optional[SessionDetail]:
        """
        Get full session details including conversation history.

        Args:
            session_id: Session identifier

        Returns:
            SessionDetail with full conversation, or None if not found
        """
        async with self.db.get_connection() as db:
            # Get session info
            cursor = await db.execute(
                """
                SELECT id, filename, zotero_key, pdf_path, created_at, updated_at
                FROM sessions
                WHERE id = ?
                """,
                (session_id,)
            )
            session_row = await cursor.fetchone()

            if not session_row:
                return None

            # Get conversation history
            cursor = await db.execute(
                """
                SELECT exchange_id, role, content, model, highlighted_text, page_number, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY exchange_id, id
                """,
                (session_id,)
            )
            conversation_rows = await cursor.fetchall()

            # Build conversation messages
            conversation = []
            for row in conversation_rows:
                conversation.append(ConversationMessage(
                    exchange_id=row[0],
                    role=row[1],
                    content=row[2],
                    model=row[3],
                    highlighted_text=row[4],
                    page_number=row[5],
                    timestamp=datetime.fromisoformat(row[6]) if row[6] else datetime.utcnow()
                ))

            # Extract initial analysis (exchange_id = 0)
            initial_analysis = ""
            if conversation and conversation[0].exchange_id == 0:
                initial_analysis = conversation[0].content
                conversation = conversation[1:]  # Remove initial analysis from conversation

            # Get page count from metadata or stored value
            page_count = None

            return SessionDetail(
                session_id=session_row[0],
                filename=session_row[1],
                initial_analysis=initial_analysis,
                created_at=datetime.fromisoformat(session_row[4]) if session_row[4] else datetime.utcnow(),
                updated_at=datetime.fromisoformat(session_row[5]) if session_row[5] else datetime.utcnow(),
                zotero_key=session_row[2],
                page_count=page_count,
                conversation=conversation
            )

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> SessionList:
        """
        List all sessions with pagination.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            SessionList with sessions and total count
        """
        async with self.db.get_connection() as db:
            # Get total count
            cursor = await db.execute("SELECT COUNT(*) FROM sessions")
            total_row = await cursor.fetchone()
            total = total_row[0] if total_row else 0

            # Get sessions
            cursor = await db.execute(
                """
                SELECT id, filename, zotero_key, created_at, updated_at
                FROM sessions
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            session_rows = await cursor.fetchall()

            # Build session list items
            sessions = []
            for row in session_rows:
                sessions.append(SessionListItem(
                    session_id=row[0],
                    filename=row[1],
                    created_at=datetime.fromisoformat(row[3]) if row[3] else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(row[4]) if row[4] else datetime.utcnow(),
                    zotero_key=row[2]
                ))

            return SessionList(sessions=sessions, total=total)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all associated data.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if session not found
        """
        async with self.db.transaction() as db:
            # Check if session exists and get PDF path
            cursor = await db.execute(
                "SELECT pdf_path FROM sessions WHERE id = ?",
                (session_id,)
            )
            session_row = await cursor.fetchone()

            if not session_row:
                return False

            # Delete PDF file if it exists
            pdf_path = session_row[0]
            if pdf_path and Path(pdf_path).exists():
                try:
                    Path(pdf_path).unlink()
                except Exception:
                    pass  # Continue even if file deletion fails

            # Delete session (cascades to conversations, flags, highlights, metadata)
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

            return True

    async def restore_session(self, session_id: str) -> Optional[SessionDetail]:
        """
        Restore full session for "pick up where you left off" functionality.

        This is an alias for get_session() that returns complete conversation history.

        Args:
            session_id: Session identifier

        Returns:
            SessionDetail with full conversation history, or None if not found
        """
        return await self.get_session(session_id)

    async def get_session_text(self, session_id: str) -> Optional[str]:
        """
        Get the full PDF text for a session.

        Args:
            session_id: Session identifier

        Returns:
            Full PDF text, or None if session not found
        """
        async with self.db.get_connection() as db:
            cursor = await db.execute(
                "SELECT full_text FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def update_session_timestamp(self, session_id: str) -> None:
        """
        Update session's last activity timestamp.

        Args:
            session_id: Session identifier
        """
        async with self.db.transaction() as db:
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.utcnow(), session_id)
            )


# Global instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get global session manager instance (singleton pattern).

    Returns:
        SessionManager: Session manager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


# Convenience functions
async def create_session_from_pdf(file: UploadFile) -> SessionResponse:
    """Create session from PDF upload."""
    manager = get_session_manager()
    return await manager.create_session_from_pdf(file)


async def get_session(session_id: str) -> Optional[SessionDetail]:
    """Get session details."""
    manager = get_session_manager()
    return await manager.get_session(session_id)


async def list_sessions(limit: int = 50, offset: int = 0) -> SessionList:
    """List sessions."""
    manager = get_session_manager()
    return await manager.list_sessions(limit, offset)


async def delete_session(session_id: str) -> bool:
    """Delete session."""
    manager = get_session_manager()
    return await manager.delete_session(session_id)
