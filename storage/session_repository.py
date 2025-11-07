"""
SQLite implementation of SessionRepository
"""

import sqlite3
from typing import Dict, List, Optional
from datetime import datetime

from .repository import SessionRepository


class SQLiteSessionRepository(SessionRepository):
    """SQLite implementation of session storage"""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize repository with database connection.

        Args:
            conn: SQLite connection (should have row_factory set)
        """
        self.conn = conn

    def create(
        self,
        paper_id: int,
        session_id: Optional[str] = None,
        model_used: str = "claude-haiku-4-5-20251001"
    ) -> str:
        """Create a new session"""
        if session_id is None:
            session_id = datetime.now().isoformat()

        self.conn.execute("""
            INSERT INTO sessions (id, paper_id, model_used, status)
            VALUES (?, ?, ?, 'active')
        """, (session_id, paper_id, model_used))

        self.conn.commit()
        return session_id

    def get_by_id(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        cursor = self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_for_paper(
        self,
        paper_id: int,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """List sessions for a paper"""
        if status:
            query = """
                SELECT * FROM sessions
                WHERE paper_id = ? AND status = ?
                ORDER BY started_at DESC
            """
            params = [paper_id, status]
        else:
            query = """
                SELECT * FROM sessions
                WHERE paper_id = ?
                ORDER BY started_at DESC
            """
            params = [paper_id]

        if limit:
            query += f" LIMIT {limit}"

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_status(self, session_id: str, status: str) -> None:
        """Update session status"""
        self.conn.execute("""
            UPDATE sessions
            SET status = ?,
                ended_at = CASE WHEN ? IN ('completed', 'interrupted')
                          THEN CURRENT_TIMESTAMP ELSE ended_at END
            WHERE id = ?
        """, (status, status, session_id))
        self.conn.commit()

    def complete_session(self, session_id: str) -> None:
        """Mark session as completed"""
        self.update_status(session_id, 'completed')

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
        is_summary: bool = False
    ) -> int:
        """Add a message to session"""
        cursor = self.conn.execute("""
            INSERT INTO messages (session_id, role, content, tokens_used, is_summary)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, role, content, tokens_used, is_summary))

        message_id = cursor.lastrowid

        # Update total_exchanges count if not a summary
        if not is_summary and role in ('user', 'assistant'):
            self.conn.execute("""
                UPDATE sessions
                SET total_exchanges = (
                    SELECT COUNT(*) / 2
                    FROM messages
                    WHERE session_id = ? AND role IN ('user', 'assistant') AND is_summary = FALSE
                )
                WHERE id = ?
            """, (session_id, session_id))

        self.conn.commit()
        return message_id

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        include_summaries: bool = True
    ) -> List[Dict]:
        """Get messages for session"""
        if include_summaries:
            query = """
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
            """
        else:
            query = """
                SELECT * FROM messages
                WHERE session_id = ? AND is_summary = FALSE
                ORDER BY created_at ASC
            """

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        cursor = self.conn.execute(query, (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_messages(
        self,
        session_id: str,
        count: int = 10
    ) -> List[Dict]:
        """
        Get most recent messages for session.

        Args:
            session_id: Session ID
            count: Number of recent messages to retrieve

        Returns:
            List of message dicts, ordered chronologically
        """
        cursor = self.conn.execute("""
            SELECT * FROM (
                SELECT * FROM messages
                WHERE session_id = ? AND is_summary = FALSE
                ORDER BY created_at DESC
                LIMIT ?
            )
            ORDER BY created_at ASC
        """, (session_id, count))

        return [dict(row) for row in cursor.fetchall()]

    def add_flag(
        self,
        session_id: str,
        user_message_id: int,
        assistant_message_id: int,
        note: Optional[str] = None
    ) -> int:
        """Flag a message exchange"""
        cursor = self.conn.execute("""
            INSERT INTO flags (session_id, user_message_id, assistant_message_id, note)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_message_id, assistant_message_id, note))

        # Mark messages as flagged
        self.conn.execute("""
            UPDATE messages SET is_flagged = TRUE
            WHERE id IN (?, ?)
        """, (user_message_id, assistant_message_id))

        self.conn.commit()
        return cursor.lastrowid

    def get_flags(self, session_id: str) -> List[Dict]:
        """Get all flagged exchanges for session"""
        cursor = self.conn.execute("""
            SELECT
                f.id,
                f.session_id,
                f.note,
                f.created_at,
                m1.id as user_message_id,
                m1.content as user_content,
                m2.id as assistant_message_id,
                m2.content as assistant_content
            FROM flags f
            JOIN messages m1 ON f.user_message_id = m1.id
            JOIN messages m2 ON f.assistant_message_id = m2.id
            WHERE f.session_id = ?
            ORDER BY f.created_at ASC
        """, (session_id,))

        return [dict(row) for row in cursor.fetchall()]

    def add_insight(
        self,
        session_id: str,
        category: str,
        content: str,
        from_flag: bool = False
    ) -> int:
        """Add an insight to session"""
        cursor = self.conn.execute("""
            INSERT INTO insights (session_id, category, content, from_flag)
            VALUES (?, ?, ?, ?)
        """, (session_id, category, content, from_flag))

        self.conn.commit()
        return cursor.lastrowid

    def add_insights_bulk(
        self,
        session_id: str,
        insights_by_category: Dict[str, List[str]],
        from_flag: bool = False
    ) -> int:
        """
        Add multiple insights at once.

        Args:
            session_id: Session ID
            insights_by_category: Dict mapping category to list of insights
            from_flag: Whether these came from flagged exchanges

        Returns:
            Number of insights added
        """
        count = 0
        for category, insights in insights_by_category.items():
            for insight in insights:
                self.add_insight(session_id, category, insight, from_flag)
                count += 1
        return count

    def get_insights(
        self,
        session_id: str,
        category: Optional[str] = None
    ) -> List[Dict]:
        """Get insights for session"""
        if category:
            cursor = self.conn.execute("""
                SELECT * FROM insights
                WHERE session_id = ? AND category = ?
                ORDER BY created_at ASC
            """, (session_id, category))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM insights
                WHERE session_id = ?
                ORDER BY category, created_at ASC
            """, (session_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_insights_grouped(self, session_id: str) -> Dict[str, List[str]]:
        """
        Get insights grouped by category.

        Args:
            session_id: Session ID

        Returns:
            Dict mapping category to list of insight contents
        """
        insights = self.get_insights(session_id)

        grouped = {}
        for insight in insights:
            category = insight['category']
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(insight['content'])

        return grouped

    def get_session_stats(self, session_id: str) -> Dict:
        """Get session statistics"""
        # Get basic session info
        session = self.get_by_id(session_id)
        if not session:
            return {}

        # Count messages
        cursor = self.conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_count,
                   SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_count,
                   SUM(CASE WHEN is_summary = TRUE THEN 1 ELSE 0 END) as summary_count
            FROM messages
            WHERE session_id = ?
        """, (session_id,))
        message_stats = dict(cursor.fetchone())

        # Count flags
        cursor = self.conn.execute("""
            SELECT COUNT(*) as flag_count
            FROM flags
            WHERE session_id = ?
        """, (session_id,))
        flag_count = cursor.fetchone()[0]

        # Count insights
        cursor = self.conn.execute("""
            SELECT COUNT(*) as insight_count,
                   COUNT(DISTINCT category) as category_count
            FROM insights
            WHERE session_id = ?
        """, (session_id,))
        insight_stats = dict(cursor.fetchone())

        return {
            'session_id': session_id,
            'paper_id': session['paper_id'],
            'status': session['status'],
            'started_at': session['started_at'],
            'ended_at': session['ended_at'],
            'total_messages': message_stats['total'],
            'user_messages': message_stats['user_count'],
            'assistant_messages': message_stats['assistant_count'],
            'summary_messages': message_stats['summary_count'],
            'exchanges': session['total_exchanges'],
            'flags': flag_count,
            'insights': insight_stats['insight_count'],
            'insight_categories': insight_stats['category_count']
        }

    def delete(self, session_id: str) -> bool:
        """
        Delete a session (cascades to messages, flags, insights).

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()
        return cursor.rowcount > 0
