"""
Abstract repository interfaces for Paper Companion storage layer

Defines contracts that concrete implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime


class PaperRepository(ABC):
    """Repository for paper metadata operations"""

    @abstractmethod
    def create(
        self,
        pdf_hash: str,
        pdf_path: Optional[str] = None,
        title: Optional[str] = None,
        authors: Optional[str] = None,  # JSON string
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        zotero_key: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Create a new paper record.

        Args:
            pdf_hash: Unique hash of PDF content
            pdf_path: Path to PDF file
            title: Paper title
            authors: JSON string of author list
            doi: DOI identifier
            arxiv_id: ArXiv identifier
            zotero_key: Zotero item key
            metadata: Additional metadata as dict

        Returns:
            Paper ID
        """
        pass

    @abstractmethod
    def find_by_id(self, paper_id: int) -> Optional[Dict]:
        """
        Find paper by ID.

        Returns:
            Paper dict or None if not found
        """
        pass

    @abstractmethod
    def find_by_hash(self, pdf_hash: str) -> Optional[Dict]:
        """
        Find paper by PDF hash.

        Returns:
            Paper dict or None if not found
        """
        pass

    @abstractmethod
    def find_by_zotero_key(self, zotero_key: str) -> Optional[Dict]:
        """
        Find paper by Zotero key.

        Returns:
            Paper dict or None if not found
        """
        pass

    @abstractmethod
    def find_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Find paper by DOI.

        Returns:
            Paper dict or None if not found
        """
        pass

    @abstractmethod
    def update_metadata(self, paper_id: int, metadata: Dict) -> None:
        """
        Update paper metadata.

        Args:
            paper_id: Paper ID
            metadata: Dict of fields to update (title, authors, doi, etc.)
        """
        pass

    @abstractmethod
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        List all papers.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of paper dicts
        """
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search papers by title, authors, or DOI.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of paper dicts
        """
        pass


class SessionRepository(ABC):
    """Repository for session operations"""

    @abstractmethod
    def create(
        self,
        paper_id: int,
        session_id: Optional[str] = None,
        model_used: str = "claude-haiku-4-5-20251001"
    ) -> str:
        """
        Create a new session.

        Args:
            paper_id: Associated paper ID
            session_id: Optional custom session ID (generates one if None)
            model_used: Model identifier

        Returns:
            Session ID
        """
        pass

    @abstractmethod
    def get_by_id(self, session_id: str) -> Optional[Dict]:
        """
        Get session by ID.

        Returns:
            Session dict or None if not found
        """
        pass

    @abstractmethod
    def list_for_paper(
        self,
        paper_id: int,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        List sessions for a paper.

        Args:
            paper_id: Paper ID
            status: Optional status filter ('active', 'completed', 'interrupted')
            limit: Maximum number of results

        Returns:
            List of session dicts, ordered by most recent first
        """
        pass

    @abstractmethod
    def update_status(self, session_id: str, status: str) -> None:
        """
        Update session status.

        Args:
            session_id: Session ID
            status: New status ('active', 'completed', 'interrupted')
        """
        pass

    @abstractmethod
    def complete_session(self, session_id: str) -> None:
        """
        Mark session as completed.

        Args:
            session_id: Session ID
        """
        pass

    @abstractmethod
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
        is_summary: bool = False
    ) -> int:
        """
        Add a message to session.

        Args:
            session_id: Session ID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            tokens_used: Number of tokens used
            is_summary: Whether this is a summary of older messages

        Returns:
            Message ID
        """
        pass

    @abstractmethod
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        include_summaries: bool = True
    ) -> List[Dict]:
        """
        Get messages for session.

        Args:
            session_id: Session ID
            limit: Maximum number of messages
            offset: Number of messages to skip
            include_summaries: Whether to include summary messages

        Returns:
            List of message dicts, ordered chronologically
        """
        pass

    @abstractmethod
    def add_flag(
        self,
        session_id: str,
        user_message_id: int,
        assistant_message_id: int,
        note: Optional[str] = None
    ) -> int:
        """
        Flag a message exchange.

        Args:
            session_id: Session ID
            user_message_id: User message ID
            assistant_message_id: Assistant message ID
            note: Optional note about why this was flagged

        Returns:
            Flag ID
        """
        pass

    @abstractmethod
    def get_flags(self, session_id: str) -> List[Dict]:
        """
        Get all flagged exchanges for session.

        Returns:
            List of flag dicts with associated messages
        """
        pass

    @abstractmethod
    def add_insight(
        self,
        session_id: str,
        category: str,
        content: str,
        from_flag: bool = False
    ) -> int:
        """
        Add an insight to session.

        Args:
            session_id: Session ID
            category: Insight category (e.g., 'strength', 'weakness')
            content: Insight content
            from_flag: Whether this came from a flagged exchange

        Returns:
            Insight ID
        """
        pass

    @abstractmethod
    def get_insights(
        self,
        session_id: str,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Get insights for session.

        Args:
            session_id: Session ID
            category: Optional category filter

        Returns:
            List of insight dicts
        """
        pass

    @abstractmethod
    def get_session_stats(self, session_id: str) -> Dict:
        """
        Get session statistics.

        Returns:
            Dict with message_count, flag_count, insight_count, etc.
        """
        pass


class CacheRepository(ABC):
    """Repository for cache operations"""

    @abstractmethod
    def get(self, cache_key: str) -> Optional[bytes]:
        """
        Get cached value.

        Args:
            cache_key: Cache key

        Returns:
            Cached data as bytes, or None if not found or expired
        """
        pass

    @abstractmethod
    def set(
        self,
        cache_key: str,
        data: bytes,
        cache_type: str,
        ttl: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Store value in cache.

        Args:
            cache_key: Cache key
            data: Data to cache (as bytes)
            cache_type: Type of cache entry (e.g., 'pdf_text', 'summary')
            ttl: Time to live in seconds (None = no expiration)
            metadata: Optional metadata dict
        """
        pass

    @abstractmethod
    def delete(self, cache_key: str) -> bool:
        """
        Delete cache entry.

        Args:
            cache_key: Cache key

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def invalidate_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dict with total_entries, total_size, hit_count, by_type stats, etc.
        """
        pass

    @abstractmethod
    def clear(self, cache_type: Optional[str] = None) -> int:
        """
        Clear cache entries.

        Args:
            cache_type: Optional type filter (clears all if None)

        Returns:
            Number of entries cleared
        """
        pass

    @abstractmethod
    def record_hit(self, cache_key: str) -> None:
        """
        Record a cache hit.

        Args:
            cache_key: Cache key that was accessed
        """
        pass
