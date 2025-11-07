-- Claude Paper Companion Database Schema
-- Version: 1.0
-- SQLite database schema for managing papers, sessions, messages, and insights

-- =============================================================================
-- SCHEMA VERSION TRACKING
-- =============================================================================

CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Initial schema with papers, sessions, messages, flags, insights, cache, and pdf_chunks');

-- =============================================================================
-- PAPERS AND METADATA
-- =============================================================================

-- Core papers table with metadata
CREATE TABLE papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf_hash TEXT UNIQUE NOT NULL,           -- SHA-256 hash of PDF content
    pdf_path TEXT,                           -- Local file path
    title TEXT,
    abstract TEXT,                           -- Paper abstract
    authors TEXT,                            -- JSON array: ["Author 1", "Author 2"]
    year INTEGER,                            -- Publication year
    venue TEXT,                              -- Journal/Conference name
    doi TEXT,
    arxiv_id TEXT,
    zotero_key TEXT,                         -- Zotero item key
    metadata TEXT,                           -- JSON blob for additional fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PDF chunks for context management
CREATE TABLE pdf_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,           -- Sequential chunk number
    chunk_type TEXT NOT NULL,               -- 'text', 'figure', 'table', 'equation'
    content TEXT NOT NULL,                  -- Extracted text or description
    page_number INTEGER,                    -- Source page
    embedding BLOB,                         -- Optional: vector embedding for semantic search
    metadata TEXT,                          -- JSON: bounding boxes, captions, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    UNIQUE(paper_id, chunk_index)
);

-- =============================================================================
-- SESSIONS AND CONVERSATIONS
-- =============================================================================

-- Research sessions (one per paper conversation)
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                    -- ISO timestamp-based ID: 'YYYYMMDD_HHMMSS'
    paper_id INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',           -- 'active', 'ended', 'archived'
    model_used TEXT,                        -- e.g., 'claude-sonnet-4'
    total_exchanges INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    summary TEXT,                           -- High-level session summary
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Conversation messages
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens_prompt INTEGER,                  -- Tokens in prompt
    tokens_completion INTEGER,              -- Tokens in completion
    is_summary BOOLEAN DEFAULT FALSE,       -- True if this is a summarized message
    parent_message_id INTEGER,              -- For threading (optional)
    metadata TEXT,                          -- JSON: model params, latency, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL
);

-- Conversation summaries (for memory management)
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    summary_type TEXT NOT NULL,             -- 'rolling', 'periodic', 'final'
    from_message_id INTEGER,                -- First message in range
    to_message_id INTEGER,                  -- Last message in range
    content TEXT NOT NULL,                  -- Summary text
    tokens_saved INTEGER,                   -- Approximate tokens saved
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (from_message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (to_message_id) REFERENCES messages(id) ON DELETE CASCADE
);

-- =============================================================================
-- FLAGS AND INSIGHTS
-- =============================================================================

-- Flagged exchanges (for later review)
CREATE TABLE flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_message_id INTEGER NOT NULL,       -- User's question
    assistant_message_id INTEGER,           -- Assistant's response
    note TEXT,                              -- User's note about why it's flagged
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (assistant_message_id) REFERENCES messages(id) ON DELETE SET NULL
);

-- Thematic insights extracted from conversations
CREATE TABLE insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    category TEXT NOT NULL,                 -- 'strength', 'weakness', 'methodological_note', 'question', 'idea'
    content TEXT NOT NULL,
    tags TEXT,                              -- JSON array: ["tag1", "tag2"]
    priority INTEGER DEFAULT 0,             -- For ranking importance
    from_flag BOOLEAN DEFAULT FALSE,        -- True if extracted from a flagged exchange
    source_message_ids TEXT,                -- JSON array of contributing message IDs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- =============================================================================
-- CACHING LAYER
-- =============================================================================

-- Multi-purpose cache for PDF extractions, API responses, embeddings
CREATE TABLE cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,         -- Hash of (operation + params)
    cache_type TEXT NOT NULL,               -- 'pdf_text', 'pdf_images', 'summary', 'api_response', 'embedding'
    data BLOB NOT NULL,                     -- JSON or binary data
    size_bytes INTEGER,                     -- For cache size management
    access_count INTEGER DEFAULT 0,         -- For LRU/LFU eviction
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                   -- NULL = no expiration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Papers indexes
CREATE INDEX idx_papers_hash ON papers(pdf_hash);
CREATE INDEX idx_papers_zotero ON papers(zotero_key);
CREATE INDEX idx_papers_doi ON papers(doi);
CREATE INDEX idx_papers_arxiv ON papers(arxiv_id);
CREATE INDEX idx_papers_year ON papers(year);

-- PDF chunks indexes
CREATE INDEX idx_chunks_paper ON pdf_chunks(paper_id);
CREATE INDEX idx_chunks_type ON pdf_chunks(chunk_type);
CREATE INDEX idx_chunks_page ON pdf_chunks(page_number);

-- Sessions indexes
CREATE INDEX idx_sessions_paper ON sessions(paper_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_started ON sessions(started_at);
CREATE INDEX idx_sessions_activity ON sessions(last_activity_at);

-- Messages indexes
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_role ON messages(role);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_messages_parent ON messages(parent_message_id);
CREATE INDEX idx_messages_summary ON messages(is_summary);

-- Summaries indexes
CREATE INDEX idx_summaries_session ON summaries(session_id);
CREATE INDEX idx_summaries_type ON summaries(summary_type);

-- Flags indexes
CREATE INDEX idx_flags_session ON flags(session_id);
CREATE INDEX idx_flags_user_msg ON flags(user_message_id);
CREATE INDEX idx_flags_created ON flags(created_at);

-- Insights indexes
CREATE INDEX idx_insights_session ON insights(session_id);
CREATE INDEX idx_insights_category ON insights(category);
CREATE INDEX idx_insights_priority ON insights(priority);
CREATE INDEX idx_insights_from_flag ON insights(from_flag);
CREATE INDEX idx_insights_created ON insights(created_at);

-- Cache indexes
CREATE INDEX idx_cache_key ON cache(cache_key);
CREATE INDEX idx_cache_type ON cache(cache_type);
CREATE INDEX idx_cache_expires ON cache(expires_at);
CREATE INDEX idx_cache_accessed ON cache(last_accessed_at);
CREATE INDEX idx_cache_size ON cache(size_bytes);

-- =============================================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMP UPDATES
-- =============================================================================

-- Update papers.updated_at on modification
CREATE TRIGGER update_papers_timestamp
AFTER UPDATE ON papers
FOR EACH ROW
BEGIN
    UPDATE papers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update sessions.last_activity_at when messages are added
CREATE TRIGGER update_session_activity
AFTER INSERT ON messages
FOR EACH ROW
BEGIN
    UPDATE sessions
    SET last_activity_at = CURRENT_TIMESTAMP,
        total_exchanges = total_exchanges + CASE WHEN NEW.role = 'user' THEN 1 ELSE 0 END,
        total_tokens_used = total_tokens_used + COALESCE(NEW.tokens_prompt, 0) + COALESCE(NEW.tokens_completion, 0)
    WHERE id = NEW.session_id;
END;

-- Update cache.last_accessed_at and access_count on read
CREATE TRIGGER update_cache_access
AFTER UPDATE OF data ON cache
FOR EACH ROW
WHEN OLD.data = NEW.data
BEGIN
    UPDATE cache
    SET last_accessed_at = CURRENT_TIMESTAMP,
        access_count = access_count + 1
    WHERE id = NEW.id;
END;

-- Update flags.updated_at on modification
CREATE TRIGGER update_flags_timestamp
AFTER UPDATE ON flags
FOR EACH ROW
BEGIN
    UPDATE flags SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Active sessions with paper details
CREATE VIEW active_sessions AS
SELECT
    s.id,
    s.started_at,
    s.last_activity_at,
    s.total_exchanges,
    s.total_tokens_used,
    p.title,
    p.authors,
    p.year,
    p.pdf_path
FROM sessions s
JOIN papers p ON s.paper_id = p.id
WHERE s.status = 'active'
ORDER BY s.last_activity_at DESC;

-- Session conversation history (with token counts)
CREATE VIEW conversation_history AS
SELECT
    m.id,
    m.session_id,
    m.role,
    m.content,
    m.tokens_prompt,
    m.tokens_completion,
    m.is_summary,
    m.created_at,
    s.paper_id,
    p.title
FROM messages m
JOIN sessions s ON m.session_id = s.id
JOIN papers p ON s.paper_id = p.id
ORDER BY m.session_id, m.created_at;

-- Flagged exchanges with context
CREATE VIEW flagged_exchanges AS
SELECT
    f.id,
    f.session_id,
    f.note,
    f.created_at,
    um.content AS user_message,
    am.content AS assistant_message,
    p.title AS paper_title
FROM flags f
JOIN messages um ON f.user_message_id = um.id
LEFT JOIN messages am ON f.assistant_message_id = am.id
JOIN sessions s ON f.session_id = s.id
JOIN papers p ON s.paper_id = p.id
ORDER BY f.created_at DESC;

-- Insights by session with paper context
CREATE VIEW insights_with_context AS
SELECT
    i.id,
    i.session_id,
    i.category,
    i.content,
    i.tags,
    i.priority,
    i.from_flag,
    i.created_at,
    p.title AS paper_title,
    p.authors,
    p.year
FROM insights i
JOIN sessions s ON i.session_id = s.id
JOIN papers p ON s.paper_id = p.id
ORDER BY i.priority DESC, i.created_at DESC;

-- Cache statistics
CREATE VIEW cache_stats AS
SELECT
    cache_type,
    COUNT(*) AS entry_count,
    SUM(size_bytes) AS total_size_bytes,
    AVG(access_count) AS avg_access_count,
    MAX(last_accessed_at) AS last_access
FROM cache
WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
GROUP BY cache_type;
