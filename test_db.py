#!/usr/bin/env python3
"""
Test suite for Paper Companion database initialization and operations
"""

import sqlite3
import tempfile
from pathlib import Path
from contextlib import contextmanager

from db import get_db, transaction, close_db
from db.schema import (
    get_current_schema_version,
    init_schema,
    ensure_schema,
    reset_database,
    vacuum_database,
    get_target_version,
    check_migration_needed,
    get_migration_info,
    apply_migrations
)


@contextmanager
def temp_database():
    """Context manager for temporary test database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        conn = get_db(db_path)
        try:
            yield conn
        finally:
            close_db()


def test_connection():
    """Test basic database connection"""
    print("Testing database connection...")
    with temp_database() as conn:
        # Test connection is alive
        cursor = conn.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1, "Basic query failed"

        # Test row factory is set
        assert conn.row_factory == sqlite3.Row, "Row factory not set"

        # Test foreign keys are enabled
        cursor = conn.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1, "Foreign keys not enabled"

        print("✓ Database connection works")


def test_schema_initialization():
    """Test schema initialization from schema.sql"""
    print("\nTesting schema initialization...")
    with temp_database() as conn:
        # Initialize schema
        init_schema(conn)

        # Check schema version
        version = get_current_schema_version(conn)
        assert version == 1, f"Expected version 1, got {version}"

        # Verify all tables exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            'papers', 'sessions', 'messages', 'flags', 'insights',
            'pdf_chunks', 'pdf_images', 'cache', 'schema_version'
        }

        assert tables == expected_tables, f"Missing tables: {expected_tables - tables}"

        print(f"✓ Schema initialized with {len(tables)} tables")


def test_schema_version_tracking():
    """Test schema version tracking"""
    print("\nTesting schema version tracking...")
    with temp_database() as conn:
        # Before init, version should be 0
        version = get_current_schema_version(conn)
        assert version == 0, f"Expected version 0 before init, got {version}"

        # After init, version should be 1
        init_schema(conn)
        version = get_current_schema_version(conn)
        assert version == 1, f"Expected version 1 after init, got {version}"

        # Calling init again should be idempotent
        init_schema(conn)
        version = get_current_schema_version(conn)
        assert version == 1, f"Expected version 1 after second init, got {version}"

        print("✓ Schema version tracking works")


def test_ensure_schema():
    """Test ensure_schema convenience function"""
    print("\nTesting ensure_schema...")
    with temp_database() as conn:
        # ensure_schema should initialize if needed
        returned_conn = ensure_schema(conn)
        assert returned_conn is conn, "ensure_schema should return same connection"

        version = get_current_schema_version(conn)
        assert version == 1, "ensure_schema should initialize schema"

        print("✓ ensure_schema works")


def test_all_indexes():
    """Test that all indexes are created"""
    print("\nTesting indexes...")
    with temp_database() as conn:
        init_schema(conn)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = {
            'idx_papers_zotero', 'idx_papers_hash', 'idx_papers_doi',
            'idx_sessions_paper', 'idx_sessions_status',
            'idx_messages_session', 'idx_messages_role', 'idx_messages_flagged',
            'idx_flags_session', 'idx_insights_session', 'idx_insights_category',
            'idx_pdf_chunks_paper', 'idx_pdf_chunks_type', 'idx_pdf_images_paper',
            'idx_cache_key', 'idx_cache_type', 'idx_cache_expires'
        }

        assert indexes == expected_indexes, f"Missing indexes: {expected_indexes - indexes}"

        print(f"✓ All {len(indexes)} indexes created")


def test_foreign_keys():
    """Test that foreign key constraints work"""
    print("\nTesting foreign key constraints...")
    with temp_database() as conn:
        init_schema(conn)

        # Insert a paper
        cursor = conn.execute(
            "INSERT INTO papers (pdf_hash, title) VALUES (?, ?)",
            ('test_hash', 'Test Paper')
        )
        paper_id = cursor.lastrowid

        # Insert a session
        cursor = conn.execute(
            "INSERT INTO sessions (id, paper_id) VALUES (?, ?)",
            ('test_session', paper_id)
        )

        # Try to insert a session with invalid paper_id
        try:
            conn.execute(
                "INSERT INTO sessions (id, paper_id) VALUES (?, ?)",
                ('bad_session', 99999)
            )
            assert False, "Should have raised foreign key constraint error"
        except sqlite3.IntegrityError:
            # Expected
            pass

        # Delete paper should cascade to sessions
        conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        cursor = conn.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", ('test_session',))
        count = cursor.fetchone()[0]
        assert count == 0, "Session should be deleted when paper is deleted"

        print("✓ Foreign key constraints work")


def test_table_schemas():
    """Test that table schemas match expectations"""
    print("\nTesting table schemas...")
    with temp_database() as conn:
        init_schema(conn)

        # Test papers table
        cursor = conn.execute("PRAGMA table_info(papers)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            'id', 'pdf_hash', 'pdf_path', 'title', 'authors', 'doi', 'arxiv_id',
            'pmid', 'journal', 'publication_date', 'abstract', 'zotero_key',
            'metadata', 'created_at', 'updated_at'
        }
        assert columns == expected, f"Papers columns mismatch: {columns} vs {expected}"

        # Test sessions table
        cursor = conn.execute("PRAGMA table_info(sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            'id', 'paper_id', 'started_at', 'ended_at', 'model_used',
            'total_exchanges', 'status'
        }
        assert columns == expected, f"Sessions columns mismatch: {columns} vs {expected}"

        # Test messages table
        cursor = conn.execute("PRAGMA table_info(messages)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            'id', 'session_id', 'role', 'content', 'tokens_used',
            'is_summary', 'is_flagged', 'created_at'
        }
        assert columns == expected, f"Messages columns mismatch: {columns} vs {expected}"

        print("✓ Table schemas match expectations")


def test_transactions():
    """Test transaction handling"""
    print("\nTesting transactions...")
    with temp_database() as conn:
        init_schema(conn)

        # Test successful transaction
        with transaction(conn):
            conn.execute(
                "INSERT INTO papers (pdf_hash, title) VALUES (?, ?)",
                ('hash1', 'Paper 1')
            )

        cursor = conn.execute("SELECT COUNT(*) FROM papers")
        assert cursor.fetchone()[0] == 1, "Transaction should commit"

        # Test rollback on error
        try:
            with transaction(conn):
                conn.execute(
                    "INSERT INTO papers (pdf_hash, title) VALUES (?, ?)",
                    ('hash2', 'Paper 2')
                )
                # This should fail due to duplicate hash
                conn.execute(
                    "INSERT INTO papers (pdf_hash, title) VALUES (?, ?)",
                    ('hash1', 'Paper 1 Duplicate')
                )
        except sqlite3.IntegrityError:
            # Expected
            pass

        cursor = conn.execute("SELECT COUNT(*) FROM papers")
        assert cursor.fetchone()[0] == 1, "Transaction should rollback on error"

        print("✓ Transaction handling works")


def test_unique_constraints():
    """Test unique constraints"""
    print("\nTesting unique constraints...")
    with temp_database() as conn:
        init_schema(conn)

        # Insert paper
        conn.execute(
            "INSERT INTO papers (pdf_hash, title, zotero_key) VALUES (?, ?, ?)",
            ('hash1', 'Paper 1', 'ZOTERO1')
        )

        # Try to insert duplicate pdf_hash
        try:
            conn.execute(
                "INSERT INTO papers (pdf_hash, title) VALUES (?, ?)",
                ('hash1', 'Paper 2')
            )
            assert False, "Should fail on duplicate pdf_hash"
        except sqlite3.IntegrityError:
            pass

        # Try to insert duplicate zotero_key
        try:
            conn.execute(
                "INSERT INTO papers (pdf_hash, title, zotero_key) VALUES (?, ?, ?)",
                ('hash2', 'Paper 3', 'ZOTERO1')
            )
            assert False, "Should fail on duplicate zotero_key"
        except sqlite3.IntegrityError:
            pass

        print("✓ Unique constraints work")


def test_reset_database():
    """Test database reset functionality"""
    print("\nTesting database reset...")
    with temp_database() as conn:
        init_schema(conn)

        # Insert some data
        conn.execute(
            "INSERT INTO papers (pdf_hash, title) VALUES (?, ?)",
            ('hash1', 'Paper 1')
        )
        conn.commit()

        cursor = conn.execute("SELECT COUNT(*) FROM papers")
        assert cursor.fetchone()[0] == 1, "Should have 1 paper"

        # Reset database
        reset_database(conn)

        # Check schema is still there
        version = get_current_schema_version(conn)
        assert version == 1, "Schema should be reinitialized"

        # Check data is gone
        cursor = conn.execute("SELECT COUNT(*) FROM papers")
        assert cursor.fetchone()[0] == 0, "Data should be deleted"

        print("✓ Database reset works")


def test_vacuum():
    """Test database vacuum"""
    print("\nTesting database vacuum...")
    with temp_database() as conn:
        init_schema(conn)

        # Insert and delete some data
        conn.execute(
            "INSERT INTO papers (pdf_hash, title) VALUES (?, ?)",
            ('hash1', 'Paper 1')
        )
        conn.execute("DELETE FROM papers WHERE pdf_hash = ?", ('hash1',))
        conn.commit()

        # Vacuum should succeed
        vacuum_database(conn)

        print("✓ Database vacuum works")


def test_data_types():
    """Test that data types are handled correctly"""
    print("\nTesting data types...")
    with temp_database() as conn:
        init_schema(conn)

        # Insert paper with all fields
        cursor = conn.execute("""
            INSERT INTO papers (
                pdf_hash, pdf_path, title, authors, doi, arxiv_id, pmid,
                journal, publication_date, abstract, zotero_key, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'hash1',
            '/path/to/paper.pdf',
            'Test Paper',
            '["Author One", "Author Two"]',  # JSON
            '10.1234/test',
            'arXiv:1234.5678',
            'PMID12345',
            'Nature',
            '2024-01-15',
            'This is an abstract',
            'ZOTERO123',
            '{"key": "value"}'  # JSON
        ))
        paper_id = cursor.lastrowid

        # Retrieve and verify
        cursor = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        row = cursor.fetchone()

        assert row['pdf_hash'] == 'hash1'
        assert row['title'] == 'Test Paper'
        assert row['authors'] == '["Author One", "Author Two"]'
        assert row['doi'] == '10.1234/test'

        # Test BLOB storage for images
        cursor = conn.execute("""
            INSERT INTO pdf_images (paper_id, page_number, image_index, image_data, width, height)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (paper_id, 1, 0, b'\x89PNG\r\n\x1a\n', 100, 200))

        cursor = conn.execute("SELECT image_data, width, height FROM pdf_images WHERE paper_id = ?", (paper_id,))
        row = cursor.fetchone()
        assert row['image_data'] == b'\x89PNG\r\n\x1a\n'
        assert row['width'] == 100
        assert row['height'] == 200

        print("✓ Data types handled correctly")


def test_migration_system():
    """Test schema migration system"""
    print("\nTesting migration system...")
    with temp_database() as conn:
        init_schema(conn)

        # Test get_target_version
        target = get_target_version()
        assert target >= 1, "Target version should be at least 1"

        # Test check_migration_needed
        migration_needed = check_migration_needed(conn)
        assert migration_needed == False, "No migrations should be needed for fresh database"

        # Test get_migration_info
        info = get_migration_info(conn)
        assert info['current_version'] == 1, "Current version should be 1"
        assert info['target_version'] >= 1, "Target version should be at least 1"
        assert info['migration_needed'] == False, "No migrations needed"
        assert len(info['pending_migrations']) == 0, "No pending migrations"
        assert len(info['version_history']) >= 1, "Should have version history"

        # Test that version history is correct
        history = info['version_history']
        assert history[0]['version'] == 1, "First version should be 1"
        assert 'Initial schema' in history[0]['description'], "Should have description"

        print("✓ Migration system works")


def test_migration_validation():
    """Test migration validation and error handling"""
    print("\nTesting migration validation...")
    with temp_database() as conn:
        init_schema(conn)

        # Test that downgrade is not allowed
        try:
            apply_migrations(conn, target_version=0)
            assert False, "Should not allow downgrade"
        except ValueError as e:
            assert "Cannot downgrade" in str(e), "Should have downgrade error message"

        # Test that migrating to current version is a no-op
        apply_migrations(conn, target_version=1)  # Should not raise

        print("✓ Migration validation works")


def run_all_tests():
    """Run all database tests"""
    print("=" * 60)
    print("Paper Companion Database Tests")
    print("=" * 60)

    tests = [
        test_connection,
        test_schema_initialization,
        test_schema_version_tracking,
        test_ensure_schema,
        test_all_indexes,
        test_foreign_keys,
        test_table_schemas,
        test_transactions,
        test_unique_constraints,
        test_reset_database,
        test_vacuum,
        test_data_types,
        test_migration_system,
        test_migration_validation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
