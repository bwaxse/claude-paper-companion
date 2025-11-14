-- Paper Companion Database Schema
-- SQLite database for storing sessions, conversations, and metadata

-- Sessions table: stores paper information and extracted text
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    zotero_key TEXT,
    pdf_path TEXT,
    full_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table: stores chat messages between user and Claude
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    exchange_id INTEGER NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    highlighted_text TEXT,  -- Optional: text highlighted by user
    page_number INTEGER,  -- Optional: page reference
    model TEXT,  -- Claude model used (e.g., 'claude-3-haiku', 'claude-3-5-sonnet')
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Flags table: user-flagged exchanges for later review
CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    exchange_id INTEGER NOT NULL,
    note TEXT,  -- Optional user note about why flagged
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Highlights table: text selections user wants to save
CREATE TABLE IF NOT EXISTS highlights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    text TEXT NOT NULL,
    page_number INTEGER,
    exchange_id INTEGER,  -- Optional: associate with conversation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Metadata table: extracted paper metadata
CREATE TABLE IF NOT EXISTS metadata (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT,  -- JSON array of author names
    doi TEXT,
    arxiv_id TEXT,
    publication_date TEXT,
    journal TEXT,
    abstract TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_exchange ON conversations(session_id, exchange_id);
CREATE INDEX IF NOT EXISTS idx_flags_session ON flags(session_id);
CREATE INDEX IF NOT EXISTS idx_highlights_session ON highlights(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_zotero ON sessions(zotero_key);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);
