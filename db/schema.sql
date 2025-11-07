-- Paper Companion Database Schema
-- SQLite database for managing papers, sessions, conversations, and insights

-- Papers table: Core paper metadata
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf_hash TEXT UNIQUE NOT NULL,
    pdf_path TEXT,
    title TEXT,
    authors TEXT,  -- JSON array of author objects
    doi TEXT,
    arxiv_id TEXT,
    pmid TEXT,
    journal TEXT,
    publication_date TEXT,
    abstract TEXT,
    zotero_key TEXT UNIQUE,
    metadata TEXT,  -- JSON blob for additional flexible fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table: Reading sessions for papers
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,  -- ISO timestamp-based ID
    paper_id INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    model_used TEXT DEFAULT 'claude-haiku-4-5-20251001',
    total_exchanges INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',  -- 'active', 'completed', 'interrupted'
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Messages table: Conversation messages
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens_used INTEGER,
    is_summary BOOLEAN DEFAULT FALSE,
    is_flagged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Flags table: Flagged exchanges with optional notes
CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_message_id INTEGER NOT NULL,
    assistant_message_id INTEGER NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (assistant_message_id) REFERENCES messages(id) ON DELETE CASCADE
);

-- Insights table: Thematically organized insights
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'strength', 'weakness', 'methodological_note', etc.
    content TEXT NOT NULL,
    from_flag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- PDF chunks table: Chunked PDF content for smart context
CREATE TABLE IF NOT EXISTS pdf_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_type TEXT,  -- 'abstract', 'methods', 'results', 'discussion', 'page_range', etc.
    start_page INTEGER,
    end_page INTEGER,
    content TEXT NOT NULL,
    char_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    UNIQUE(paper_id, chunk_index)
);

-- PDF images table: Extracted images/figures
CREATE TABLE IF NOT EXISTS pdf_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    image_index INTEGER NOT NULL,
    image_data BLOB NOT NULL,
    media_type TEXT DEFAULT 'image/png',
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Cache table: Multi-purpose caching
CREATE TABLE IF NOT EXISTS cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    cache_type TEXT NOT NULL,  -- 'pdf_text', 'pdf_images', 'summary', 'response'
    data BLOB NOT NULL,
    metadata TEXT,  -- JSON for cache-specific metadata
    expires_at TIMESTAMP,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_papers_zotero ON papers(zotero_key);
CREATE INDEX IF NOT EXISTS idx_papers_hash ON papers(pdf_hash);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_sessions_paper ON sessions(paper_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_messages_flagged ON messages(is_flagged);
CREATE INDEX IF NOT EXISTS idx_flags_session ON flags(session_id);
CREATE INDEX IF NOT EXISTS idx_insights_session ON insights(session_id);
CREATE INDEX IF NOT EXISTS idx_insights_category ON insights(category);
CREATE INDEX IF NOT EXISTS idx_pdf_chunks_paper ON pdf_chunks(paper_id);
CREATE INDEX IF NOT EXISTS idx_pdf_chunks_type ON pdf_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_pdf_images_paper ON pdf_images(paper_id);
CREATE INDEX IF NOT EXISTS idx_cache_key ON cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_type ON cache(cache_type);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial schema with papers, sessions, messages, flags, insights, chunks, images, and cache');
