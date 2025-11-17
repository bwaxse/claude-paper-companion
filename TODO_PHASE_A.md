# Phase A: Backend Foundation - Implementation Plan

## 📊 Status Summary (Last Updated: 2025-11-17)

**Completed Tasks:** 4 of 15
- ✅ Task 1: Project Setup & Configuration
- ✅ Task 2: Database Schema & Connection
- ✅ Task 3: Core PDF Processing
- ✅ Task 4: Claude Integration
- ⏳ Task 5: Pydantic Models (IN PROGRESS / NEXT)
- ⬜ Task 6-15: Not started

**Foundation Status:** Core infrastructure complete. Ready to build services and API routes.

---

## Overview
Convert Paper Companion CLI to FastAPI web backend while preserving existing critical appraisal logic. Build robust session management and prepare for Lumi-inspired frontend.

## Architecture Decision
**Start fresh, port selectively from CLI:**
- PoC validates the PDF→Claude→UI flow
- CLI has Zotero integration we need
- Build clean FastAPI structure, import CLI modules as needed
- Keep CLI intact for users who prefer terminal workflow

## Project Structure
```
paper-companion/
├── cli/                          # Existing CLI (preserve as-is)
│   ├── chat.py
│   ├── list_zotero.py
│   ├── setup.py
│   └── ...existing files...
├── web/                          # New web backend
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── sessions.py      # Session CRUD
│   │   │   ├── queries.py       # Query handling
│   │   │   ├── zotero.py        # Zotero endpoints
│   │   │   └── insights.py      # Extraction endpoints
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── session.py       # Pydantic models
│   │       └── query.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Settings management
│   │   ├── database.py          # SQLite connection
│   │   ├── claude.py            # Claude API wrapper
│   │   └── pdf_processor.py    # PDF extraction (PyMuPDF)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_manager.py  # Session logic
│   │   ├── zotero_service.py   # Port from CLI
│   │   └── insight_extractor.py # Port from CLI
│   └── db/
│       ├── __init__.py
│       ├── schema.sql           # SQLite schema
│       └── migrations/          # Future schema changes
├── frontend/                     # Phase B (future)
│   └── ...Lit components...
├── tests/
│   ├── test_api.py
│   ├── test_sessions.py
│   └── test_zotero.py
├── requirements.txt              # Combined deps
├── requirements-web.txt          # Web-specific deps
└── README.md                     # Updated with web instructions
```

## Phase A Tasks (Ordered for Claude Code)

### Task 1: Project Setup & Configuration ✅ COMPLETED
**File: `web/core/config.py`**
- [x] Create Settings class using pydantic-settings
- [x] Load from environment variables
- [x] Support .env file loading
- [x] Settings: ANTHROPIC_API_KEY, ZOTERO_API_KEY, ZOTERO_LIBRARY_ID, DATABASE_PATH
- [x] Add validation for required settings

**File: `requirements-web.txt`**
- [x] fastapi
- [x] uvicorn[standard]
- [x] anthropic
- [x] pymupdf
- [x] python-multipart
- [x] pydantic-settings
- [x] python-dotenv
- [x] aiosqlite

### Task 2: Database Schema & Connection ✅ COMPLETED
**File: `web/db/schema.sql`**
```sql
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    zotero_key TEXT,
    pdf_path TEXT,
    full_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    exchange_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    highlighted_text TEXT,
    page_number INTEGER,
    model TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Flags table
CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    exchange_id INTEGER NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Highlights table
CREATE TABLE IF NOT EXISTS highlights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    text TEXT NOT NULL,
    page_number INTEGER,
    exchange_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Metadata extracted from papers
CREATE TABLE IF NOT EXISTS metadata (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT, -- JSON array
    doi TEXT,
    arxiv_id TEXT,
    publication_date TEXT,
    journal TEXT,
    abstract TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_flags_session ON flags(session_id);
CREATE INDEX IF NOT EXISTS idx_highlights_session ON highlights(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_zotero ON sessions(zotero_key);
```

**File: `web/core/database.py`**
- [x] Create async database connection manager
- [x] Initialize database with schema on startup
- [x] Provide context manager for transactions
- [x] Add connection pooling

### Task 3: Core PDF Processing ✅ COMPLETED
**File: `web/core/pdf_processor.py`**
- [x] Extract full text from PDF using PyMuPDF
- [x] Extract outline/headings (for Outline tab - Phase B)
- [x] Extract figures with captions and page numbers (for future)
- [x] Generate PDF hash for deduplication
- [x] Extract basic metadata (title, authors from PDF if available)

**Functions to implement:**
```python
async def extract_text(pdf_path: str) -> str  # ✅
async def extract_metadata(pdf_path: str) -> dict  # ✅
async def extract_outline(pdf_path: str) -> list  # ✅
async def get_pdf_hash(pdf_path: str) -> str  # ✅
```

### Task 4: Claude Integration ✅ COMPLETED
**File: `web/core/claude.py`**
- [x] Create ClaudeClient wrapper class
- [x] Method: initial_analysis(pdf_content: bytes) -> uses Haiku, sends full PDF
- [x] Method: query(messages: list, use_sonnet: bool = True) -> handles conversation
- [x] Add retry logic with exponential backoff
- [x] Token counting/tracking for cost monitoring
- [x] Error handling for rate limits

### Task 5: Pydantic Models
**File: `web/api/models/session.py`**
```python
class SessionCreate(BaseModel):
    # For PDF upload or Zotero key
    
class SessionResponse(BaseModel):
    session_id: str
    filename: str
    initial_analysis: str
    created_at: datetime
    
class SessionList(BaseModel):
    sessions: List[SessionResponse]
```

**File: `web/api/models/query.py`**
```python
class QueryRequest(BaseModel):
    query: str
    highlighted_text: Optional[str] = None
    page: Optional[int] = None
    
class QueryResponse(BaseModel):
    exchange_id: int
    response: str
    model_used: str
```

### Task 6: Session Management Service
**File: `web/services/session_manager.py`**
- [ ] create_session_from_pdf(file: UploadFile) -> Session
- [ ] create_session_from_zotero(zotero_key: str) -> Session
- [ ] get_session(session_id: str) -> Session
- [ ] list_sessions(limit: int = 50) -> List[Session]
- [ ] delete_session(session_id: str)
- [ ] restore_session(session_id: str) -> Full conversation history

**Logic:**
1. Receive PDF or Zotero key
2. Extract text with pdf_processor
3. Send to Claude for initial analysis (Haiku)
4. Store in database
5. Return session info

### Task 7: Zotero Integration Service
**File: `web/services/zotero_service.py`**
- [ ] Port Zotero API client from CLI
- [ ] search_papers(query: str) -> List[ZoteroItem]
- [ ] get_paper_by_key(key: str) -> ZoteroItem
- [ ] get_pdf_path(key: str) -> str
- [ ] list_recent(limit: int = 20) -> List[ZoteroItem]
- [ ] save_insights_to_note(session_id: str) -> bool
- [ ] get_related_papers(tags: List[str]) -> List[ZoteroItem]

### Task 8: FastAPI Routes - Sessions
**File: `web/api/routes/sessions.py`**
```python
POST   /sessions/new          # Upload PDF or provide Zotero key
GET    /sessions              # List all sessions
GET    /sessions/{id}         # Get session with full conversation
DELETE /sessions/{id}         # Delete session
GET    /sessions/{id}/export  # Export to JSON
```

### Task 9: FastAPI Routes - Queries
**File: `web/api/routes/queries.py`**
```python
POST /sessions/{id}/query      # Ask question
POST /sessions/{id}/flag       # Toggle flag on exchange
GET  /sessions/{id}/highlights # Get all highlights
```

### Task 10: FastAPI Routes - Zotero
**File: `web/api/routes/zotero.py`**
```python
GET  /zotero/search           # Search Zotero library
GET  /zotero/recent           # List recent papers
GET  /zotero/paper/{key}      # Get paper details
POST /zotero/save-insights    # Save session insights to Zotero note
GET  /zotero/related          # Find related papers
```

### Task 11: Insight Extraction Service
**File: `web/services/insight_extractor.py`**
- [ ] Port critical appraisal extraction from CLI
- [ ] extract_insights(session_id: str) -> dict
- [ ] Analyze flagged exchanges
- [ ] Identify key methods, findings, limitations
- [ ] Generate structured output for Zotero notes
- [ ] Format as HTML for Zotero attachment

**Extraction categories (from CLI):**
- Focus areas
- Key methods
- Main findings
- Your interpretations
- Limitations identified
- Open questions
- Application ideas

### Task 12: Main FastAPI Application
**File: `web/api/main.py`**
- [ ] Initialize FastAPI app
- [ ] Add CORS middleware
- [ ] Include routers (sessions, queries, zotero, insights)
- [ ] Add startup event: initialize database
- [ ] Add health check endpoint
- [ ] Add error handlers
- [ ] Add request logging

### Task 13: Testing Suite
**File: `tests/test_api.py`**
- [ ] Test session creation with sample PDF
- [ ] Test query flow
- [ ] Test flag functionality
- [ ] Test session restoration

**File: `tests/test_zotero.py`**
- [ ] Mock Zotero API
- [ ] Test search
- [ ] Test paper retrieval
- [ ] Test insight saving

### Task 14: CLI Compatibility Layer
**File: `cli/web_client.py`** (optional)
- [ ] Create CLI wrapper that calls web API
- [ ] Allows users to use CLI interface with web backend
- [ ] Maintains backward compatibility

### Task 15: Documentation
**File: `web/README.md`**
- [ ] Setup instructions
- [ ] Environment variable configuration
- [ ] API endpoint documentation
- [ ] Development workflow
- [ ] Testing instructions

**File: `web/API.md`**
- [ ] Full API specification
- [ ] Request/response examples
- [ ] Error codes
- [ ] Rate limiting info

## Success Criteria

**Phase A is complete when:**
- ✅ Can upload PDF → get initial analysis → stored in SQLite
- ✅ Can query paper → get response → conversation persisted
- ✅ Can flag exchanges
- ✅ Can load paper from Zotero by key
- ✅ Can search Zotero library
- ✅ Can save insights back to Zotero
- ✅ Can restore session ("pick up where left off")
- ✅ All core routes have tests
- ✅ Documentation is complete

## Testing Strategy

1. **Unit tests:** Each service independently
2. **Integration tests:** API routes with in-memory SQLite
3. **Manual testing:** Use Postman/curl or PoC frontend
4. **Zotero testing:** Use test library with sample papers

## Migration Path

**From PoC to Phase A:**
- Keep PoC frontend working during Phase A development
- Update PoC frontend's API calls to match new endpoints
- Once Phase A is stable, begin Phase B (proper frontend)

## Development Order (for Claude Code)

1. Start with database schema and connection
2. Build PDF processor (independent)
3. Build Claude client wrapper (independent)
4. Build session manager service (uses 1-3)
5. Build Zotero service (port from CLI)
6. Build FastAPI routes (uses services)
7. Build insight extractor (port from CLI)
8. Add tests
9. Update documentation

## Port from CLI (Specific Files)

**Priority imports:**
- `cli/chat.py` → Extract critical appraisal prompts and extraction logic
- `cli/list_zotero.py` → Port Zotero API client
- `cli/setup.py` → Port Zotero credential management

## Cost Optimization Notes

**Keep in Phase A:**
- Haiku for initial analysis (full PDF binary is fine)
- Sonnet for queries (text-only context)
- Store extracted text in database (don't re-extract)
- Token counting for monitoring

**Estimated costs per session:**
- Initial analysis: ~$0.02 (Haiku with PDF)
- 10 queries: ~$0.05 (Sonnet with text)
- Total: ~$0.07 per paper

## Phase A Deliverables

1. Working FastAPI backend with all endpoints
2. SQLite database with complete schema
3. Zotero integration (search, load, save)
4. Session persistence and restoration
5. Test suite
6. API documentation
7. PoC frontend still functional (updated to use new API)

## Next Steps After Phase A

**Phase B: Frontend**
- Extract Lumi UI components
- Build Lit component structure
- Implement Outline/Concepts tabs
- Multi-page PDF rendering
- Better highlight anchoring
- Session list/restore UI

## Questions for Claude Code

As you implement, consider:
1. Should we use async SQLite (aiosqlite) or sync?
2. File upload: store in filesystem or database?
3. Session expiration/cleanup policy?
4. Rate limiting on API endpoints?
5. Authentication needed? (Currently none)

## Notes

- **Don't over-engineer:** Phase A is foundation, not final product
- **Test as you go:** Each service gets basic tests
- **Port selectively:** Only bring over CLI code that's needed
- **Keep PoC:** It's our integration test
- **Document decisions:** Add comments explaining non-obvious choices
