# Paper Companion: Database-First Refactor TODO

## Overview
Comprehensive refactor to add SQLite database, session resumption, intelligent caching, and modular architecture.

**Timeline**: ~9 days
**Current Status**: Phase 2 complete - moving to Phase 3

---

## Phase 1: Database Foundation (Days 1-2)

### ✅ 1.1 SQLite Schema Design
- [x] Create `db/schema.sql` with all tables
- [x] Add papers, sessions, messages, flags, insights tables
- [x] Add pdf_chunks, pdf_images, cache tables
- [x] Create indexes for common queries
- [x] Add schema versioning

### ✅ 1.2 Database Initialization
- [x] Create `db/__init__.py` with connection manager
- [x] Create `db/schema.py` for schema creation and versioning
- [x] Test database initialization (test_db.py with 14 tests)
- [x] Add schema upgrade path (migration system with apply_migrations, get_migration_info)

### ✅ 1.3 Migration Scripts
- [x] ~~Create `db/migrate.py` for JSON → SQLite migration~~ (Not needed - no existing JSON data)
- [x] ~~Parse existing `~/.paper_companion/sessions/*.json` files~~ (Not needed)
- [x] ~~Extract papers, sessions, messages, flags~~ (Not needed)
- [x] ~~Preserve timestamps and relationships~~ (Not needed)
- [x] ~~Add validation tests~~ (Not needed)

---

## Phase 2: Storage Abstraction (Day 3)

### ✅ 2.1 Repository Pattern Interfaces
- [x] Create `storage/repository.py` with abstract base classes
- [x] Define PaperRepository interface
- [x] Define SessionRepository interface
- [x] Define CacheRepository interface
- [x] Add type hints and documentation

### ✅ 2.2 SQLite Repository Implementations
- [x] Create `storage/paper_repository.py`
  - [x] `create()` - Insert new paper
  - [x] `find_by_hash()` - Find by PDF hash
  - [x] `find_by_zotero_key()` - Find by Zotero key
  - [x] `find_by_doi()` - Find by DOI
  - [x] `update_metadata()` - Update paper metadata
  - [x] `list_all()` - List all papers
  - [x] `store_pdf_chunks()` - Store PDF chunks
  - [x] `store_pdf_images()` - Store PDF images
  - [x] `search()` - Search papers by title/authors/DOI

- [x] Create `storage/session_repository.py`
  - [x] `create()` - Create new session
  - [x] `get_by_id()` - Get session by ID
  - [x] `get_messages()` - Get messages for session
  - [x] `add_message()` - Add message to session
  - [x] `list_for_paper()` - List sessions for paper
  - [x] `complete_session()` - Mark session as completed
  - [x] `add_flag()` - Flag a message exchange
  - [x] `get_flags()` - Get flagged exchanges
  - [x] `add_insight()` / `add_insights_bulk()` - Add insights
  - [x] `get_insights()` / `get_insights_grouped()` - Retrieve insights
  - [x] `get_session_stats()` - Get session statistics

- [x] Create `storage/cache_repository.py`
  - [x] `get()` - Get cached value
  - [x] `set()` - Store value in cache
  - [x] `invalidate_expired()` - Remove expired entries
  - [x] `get_stats()` - Cache hit/miss statistics
  - [x] `clear()` - Clear all cache
  - [x] `record_hit()` - Track cache hits
  - [x] `get_by_type()` - Get entries by cache type
  - [x] `cleanup_least_used()` - LRU cleanup

### ✅ 2.3 Testing
- [x] Unit tests for each repository (tests/test_repositories.py with 50+ assertions)
- [x] Integration tests for database operations
- [x] Test transaction handling and cascade deletes
- [x] All tests passing ✓

---

## Phase 3: Core Functionality (Days 4-5)

### ⏳ 3.1 Complete Zotero Methods
- [ ] Implement `_find_or_create_item()` in `chat.py`
  - [ ] Search by DOI
  - [ ] Search by PDF hash in Extra field
  - [ ] Create new journalArticle if not found
  - [ ] Return Zotero item dict

- [ ] Implement `_update_item_metadata()` in `chat.py`
  - [ ] Compare existing vs extracted metadata
  - [ ] Update title, authors, journal, DOI, abstract
  - [ ] Add PDF hash to Extra field
  - [ ] Add tags: claude-analyzed, method:*, topic:*

- [ ] Test with various paper sources
  - [ ] Local PDF → creates Zotero item
  - [ ] Zotero item → updates metadata
  - [ ] Duplicate detection works

### ⏳ 3.2 Session Resumption
- [ ] Update `PaperCompanion.__init__()` to accept `resume_session` param
- [ ] Implement `_resume_session()` method
  - [ ] Load paper info from database
  - [ ] Load message history
  - [ ] Load flagged exchanges
  - [ ] Restore conversation state

- [ ] Implement `_start_new_session()` method
  - [ ] Find or create paper record
  - [ ] Create session record in database
  - [ ] Initialize state

- [ ] Add CLI arguments
  - [ ] `--resume SESSION_ID` - Resume specific session
  - [ ] `--list-sessions` - List sessions for paper
  - [ ] `--resume-last` - Resume most recent session

- [ ] Update session saving
  - [ ] Save messages to database as they happen
  - [ ] Update session status on exit
  - [ ] Store insights in database

### ⏳ 3.3 Integration
- [ ] Update `PaperCompanion` to use repository pattern
- [ ] Replace direct JSON writes with database calls
- [ ] Test session creation, resumption, and completion

---

## Phase 4: Performance & Intelligence (Days 6-7)

### ⏳ 4.1 Multi-Tier Caching Strategy
- [ ] Create `core/cache_manager.py`
  - [ ] `MemoryCache` - In-memory cache for current session
  - [ ] `DatabaseCache` - SQLite cache for persistent storage
  - [ ] `DiskCache` - File-based cache for large objects
  - [ ] `CacheManager` - Unified interface checking all tiers

- [ ] Cache PDF extractions
  - [ ] Cache extracted text by PDF hash
  - [ ] Cache images by PDF hash
  - [ ] Store on disk (permanent)

- [ ] Cache API responses
  - [ ] Cache initial summaries (7 days TTL)
  - [ ] Cache critical reviews (7 days TTL)
  - [ ] Cache similar Q&A pairs (30 days TTL)
  - [ ] Store in SQLite

- [ ] Add cache warming
  - [ ] Pre-compute summaries for new papers
  - [ ] Background cache cleanup

- [ ] Implement cache eviction
  - [ ] LRU for memory cache
  - [ ] TTL-based for database cache
  - [ ] Size-based for disk cache

### ⏳ 4.2 Conversation Memory Management
- [ ] Create `core/conversation.py`
  - [ ] `_build_context()` - Build optimized context for Claude
    - [ ] Always include: paper metadata + summary
    - [ ] Recent messages (last 5 exchanges)
    - [ ] All flagged exchanges (condensed)
    - [ ] Summaries of older conversation chunks
    - [ ] Stay under ~50K token budget

  - [ ] `_summarize_old_messages()` - Summarize message blocks
    - [ ] Every 20 exchanges, create a summary
    - [ ] Store in messages table with `is_summary=True`
    - [ ] Replace originals with summary in context

  - [ ] `_estimate_tokens()` - Rough token estimation
  - [ ] `_compress_context()` - Compress if over budget

- [ ] Test with long conversations
  - [ ] 50+ exchange sessions
  - [ ] Multiple resumptions
  - [ ] Verify context quality maintained

### ⏳ 4.3 Smart Context & PDF Chunking
- [ ] Create `core/pdf_processor.py`
  - [ ] Extract from current `chat.py`
  - [ ] `extract_text_and_images()` - Current functionality
  - [ ] `extract_pdf_chunks()` - New chunking functionality
    - [ ] Split by sections (Abstract, Methods, Results, etc.)
    - [ ] Or by page ranges (configurable size)
    - [ ] Store chunks in database

  - [ ] `get_relevant_chunks()` - Select relevant chunks
    - [ ] Keyword matching
    - [ ] Return top 3-5 chunks (~10K chars)

- [ ] Update context building
  - [ ] Replace full PDF content with relevant chunks
  - [ ] Send only what's needed for current question

- [ ] Store chunks in database
  - [ ] Use `pdf_chunks` table
  - [ ] Cache chunk extraction

---

## Phase 5: Code Organization (Day 8)

### ⏳ 5.1 Extract Zotero Integration
- [ ] Create `integrations/zotero_client.py`
  - [ ] Move `setup_zotero()` from `chat.py`
  - [ ] Move `_load_from_zotero()` from `chat.py`
  - [ ] Move `_search_zotero_items()` from `chat.py`
  - [ ] Move `_choose_zotero_item()` from `chat.py`
  - [ ] Move `save_to_zotero()` from `chat.py`
  - [ ] Move all Zotero helper methods
  - [ ] Create `ZoteroClient` class

### ⏳ 5.2 Extract PDF Processing
- [ ] Create `core/pdf_processor.py` (if not done in 4.3)
  - [ ] Move `_load_pdf()` from `chat.py`
  - [ ] Move `_compute_pdf_hash()` from `chat.py`
  - [ ] Create `PDFProcessor` class

### ⏳ 5.3 Extract Conversation Logic
- [ ] Create `core/conversation.py` (if not done in 4.2)
  - [ ] Move `chat_loop()` from `chat.py`
  - [ ] Move `_get_claude_response()` from `chat.py`
  - [ ] Move command handlers
  - [ ] Create `ConversationManager` class

### ⏳ 5.4 Extract Insights Extraction
- [ ] Create `core/insights_extractor.py`
  - [ ] Move `extract_insights()` from `chat.py`
  - [ ] Move `_format_insights_html()` from `chat.py`
  - [ ] Create `InsightsExtractor` class

### ⏳ 5.5 Extract Claude Client
- [ ] Create `integrations/claude_client.py`
  - [ ] Move `get_initial_summary()` from `chat.py`
  - [ ] Move `get_full_critical_review()` from `chat.py`
  - [ ] Move other Claude API calls
  - [ ] Create `ClaudeClient` class with caching

### ⏳ 5.6 Refactor Main Entry Point
- [ ] Update `chat.py` to orchestrate components
  - [ ] Import all modules
  - [ ] `PaperCompanion` becomes lightweight orchestrator
  - [ ] Delegate to specialized classes
  - [ ] Target: ~200 lines

### ⏳ 5.7 Add Utilities
- [ ] Create `utils/helpers.py`
  - [ ] Move `_format_authors()` from `chat.py`
  - [ ] Move `_parse_selection()` from `chat.py`
  - [ ] Other utility functions

---

## Phase 6: Testing & Polish (Day 9)

### ⏳ 6.1 Migration Testing
- [ ] Create `tests/validate_migration.py`
  - [ ] Test JSON → SQLite migration
  - [ ] Verify data integrity
  - [ ] Compare migrated vs original data

### ⏳ 6.2 Feature Testing
- [ ] Test session creation
- [ ] Test session resumption
- [ ] Test message persistence
- [ ] Test flag persistence
- [ ] Test insights extraction
- [ ] Test Zotero integration
  - [ ] Local PDF → creates item
  - [ ] Existing item → updates metadata
  - [ ] Search and load

### ⏳ 6.3 Performance Testing
- [ ] Test caching behavior
  - [ ] Measure cache hit rates
  - [ ] Verify multi-tier fallback
  - [ ] Test cache expiration

- [ ] Test with long papers (100+ pages)
  - [ ] Verify chunking works
  - [ ] Context stays under limits

- [ ] Test with long conversations (50+ exchanges)
  - [ ] Verify summarization works
  - [ ] Context quality maintained

### ⏳ 6.4 Documentation
- [ ] Update README.md with new features
- [ ] Add database schema documentation
- [ ] Add migration guide
- [ ] Add API documentation
- [ ] Update USAGE.md with resume commands

### ⏳ 6.5 Final Polish
- [ ] Add error handling for database operations
- [ ] Add logging throughout
- [ ] Add progress bars for long operations
- [ ] Improve error messages
- [ ] Add `--debug` flag for verbose output

---

## Future Enhancements (Post-Launch)

### 🔮 Cross-Paper Analysis
- [ ] Compare multiple papers
- [ ] Find connections across papers
- [ ] Track concepts across literature

### 🔮 Semantic Search
- [ ] Add sentence-transformers for embeddings
- [ ] Store embeddings for messages
- [ ] Semantic search for relevant context
- [ ] Find similar papers by content

### 🔮 Advanced Zotero Integration
- [ ] Auto-highlight passages in PDF
- [ ] Sync highlights from Zotero
- [ ] Export insights to Obsidian/Roam

### 🔮 Batch Processing
- [ ] Process multiple papers in parallel
- [ ] Generate comparative summaries
- [ ] Build literature review automatically

### 🔮 Web Interface
- [ ] Simple web UI for browsing sessions
- [ ] Visualize paper connections
- [ ] Export formatted reports

---

### Testing Strategy
- Unit tests for each repository
- Integration tests for workflows
- Manual testing with real papers
- Migration testing with existing data

---

**Legend**: ✅ Done | 🔄 In Progress | ⏳ To Do | 🔮 Future
