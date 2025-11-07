"""
SQLite implementation of PaperRepository
"""

import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime

from .repository import PaperRepository


class SQLitePaperRepository(PaperRepository):
    """SQLite implementation of paper storage"""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize repository with database connection.

        Args:
            conn: SQLite connection (should have row_factory set)
        """
        self.conn = conn

    def create(
        self,
        pdf_hash: str,
        pdf_path: Optional[str] = None,
        title: Optional[str] = None,
        authors: Optional[str] = None,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        zotero_key: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Create a new paper record"""
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.conn.execute("""
            INSERT INTO papers (
                pdf_hash, pdf_path, title, authors, doi, arxiv_id,
                zotero_key, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (pdf_hash, pdf_path, title, authors, doi, arxiv_id, zotero_key, metadata_json))

        self.conn.commit()
        return cursor.lastrowid

    def find_by_id(self, paper_id: int) -> Optional[Dict]:
        """Find paper by ID"""
        cursor = self.conn.execute(
            "SELECT * FROM papers WHERE id = ?",
            (paper_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def find_by_hash(self, pdf_hash: str) -> Optional[Dict]:
        """Find paper by PDF hash"""
        cursor = self.conn.execute(
            "SELECT * FROM papers WHERE pdf_hash = ?",
            (pdf_hash,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def find_by_zotero_key(self, zotero_key: str) -> Optional[Dict]:
        """Find paper by Zotero key"""
        cursor = self.conn.execute(
            "SELECT * FROM papers WHERE zotero_key = ?",
            (zotero_key,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def find_by_doi(self, doi: str) -> Optional[Dict]:
        """Find paper by DOI"""
        cursor = self.conn.execute(
            "SELECT * FROM papers WHERE doi = ?",
            (doi,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_metadata(self, paper_id: int, metadata: Dict) -> None:
        """Update paper metadata"""
        # Build UPDATE query dynamically based on provided fields
        allowed_fields = {
            'pdf_path', 'title', 'authors', 'doi', 'arxiv_id', 'pmid',
            'journal', 'publication_date', 'abstract', 'zotero_key', 'metadata'
        }

        updates = []
        values = []

        for field, value in metadata.items():
            if field in allowed_fields:
                if field == 'metadata' and isinstance(value, dict):
                    value = json.dumps(value)
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            return

        # Always update updated_at
        updates.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE papers SET {', '.join(updates)} WHERE id = ?"
        values.append(paper_id)

        self.conn.execute(query, values)
        self.conn.commit()

    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """List all papers"""
        query = "SELECT * FROM papers ORDER BY created_at DESC"

        if limit is not None:
            query += f" LIMIT {limit} OFFSET {offset}"

        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search papers by title, authors, or DOI.

        Uses SQLite's LIKE for simple text matching.
        """
        search_pattern = f"%{query}%"

        cursor = self.conn.execute("""
            SELECT * FROM papers
            WHERE title LIKE ? OR authors LIKE ? OR doi LIKE ? OR arxiv_id LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (search_pattern, search_pattern, search_pattern, search_pattern, limit))

        return [dict(row) for row in cursor.fetchall()]

    def store_pdf_chunks(
        self,
        paper_id: int,
        chunks: List[Dict]
    ) -> None:
        """
        Store PDF chunks for a paper.

        Args:
            paper_id: Paper ID
            chunks: List of chunk dicts with keys:
                    chunk_index, chunk_type, start_page, end_page, content
        """
        # Delete existing chunks
        self.conn.execute("DELETE FROM pdf_chunks WHERE paper_id = ?", (paper_id,))

        # Insert new chunks
        for chunk in chunks:
            self.conn.execute("""
                INSERT INTO pdf_chunks (
                    paper_id, chunk_index, chunk_type, start_page, end_page,
                    content, char_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                chunk['chunk_index'],
                chunk.get('chunk_type'),
                chunk.get('start_page'),
                chunk.get('end_page'),
                chunk['content'],
                len(chunk['content'])
            ))

        self.conn.commit()

    def get_pdf_chunks(
        self,
        paper_id: int,
        chunk_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get PDF chunks for a paper.

        Args:
            paper_id: Paper ID
            chunk_type: Optional filter by chunk type

        Returns:
            List of chunk dicts
        """
        if chunk_type:
            cursor = self.conn.execute("""
                SELECT * FROM pdf_chunks
                WHERE paper_id = ? AND chunk_type = ?
                ORDER BY chunk_index
            """, (paper_id, chunk_type))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM pdf_chunks
                WHERE paper_id = ?
                ORDER BY chunk_index
            """, (paper_id,))

        return [dict(row) for row in cursor.fetchall()]

    def store_pdf_images(
        self,
        paper_id: int,
        images: List[Dict]
    ) -> None:
        """
        Store PDF images for a paper.

        Args:
            paper_id: Paper ID
            images: List of image dicts with keys:
                    page_number, image_index, image_data, media_type, width, height
        """
        # Delete existing images
        self.conn.execute("DELETE FROM pdf_images WHERE paper_id = ?", (paper_id,))

        # Insert new images
        for img in images:
            self.conn.execute("""
                INSERT INTO pdf_images (
                    paper_id, page_number, image_index, image_data,
                    media_type, width, height
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                img['page_number'],
                img['image_index'],
                img['image_data'],
                img.get('media_type', 'image/png'),
                img.get('width'),
                img.get('height')
            ))

        self.conn.commit()

    def get_pdf_images(self, paper_id: int) -> List[Dict]:
        """
        Get PDF images for a paper.

        Args:
            paper_id: Paper ID

        Returns:
            List of image dicts
        """
        cursor = self.conn.execute("""
            SELECT * FROM pdf_images
            WHERE paper_id = ?
            ORDER BY page_number, image_index
        """, (paper_id,))

        return [dict(row) for row in cursor.fetchall()]

    def delete(self, paper_id: int) -> bool:
        """
        Delete a paper (cascades to sessions, chunks, images).

        Args:
            paper_id: Paper ID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        self.conn.commit()
        return cursor.rowcount > 0
