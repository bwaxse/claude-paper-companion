# Paper Companion Web - Proof of Concept

Minimal implementation to validate the architecture:
- PDF upload → Claude ingestion
- PDF.js rendering with text selection
- Highlight → Query → Response flow
- Session persistence (in-memory for now)

## Setup

1. **Install dependencies:**
```bash
cd /home/claude/paper-companion-web/poc
pip install -r requirements.txt
```

2. **Set environment variable:**
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

3. **Start backend:**
```bash
python backend.py
```

Backend runs on `http://localhost:8000`

4. **Open frontend:**
Open `index.html` in a web browser, or serve it:
```bash
python -m http.server 8080
```

Then navigate to `http://localhost:8080`

## Testing the Flow

1. **Upload PDF:**
   - Click "Choose PDF"
   - Select your test paper
   - Wait for initial analysis

2. **Read & Highlight:**
   - PDF renders in center pane
   - Select text with mouse (basic implementation)

3. **Ask Questions:**
   - Type in the query box (left panel, "Ask" tab)
   - Claude responds with full paper context
   - Conversation history shown in left panel

4. **Flag Important Exchanges:**
   - Click ★ next to responses (coming soon)

## What Works (PoC)

✅ PDF upload & Claude ingestion (full paper in context)
✅ Initial analysis generation
✅ PDF.js rendering (first page only for PoC)
✅ Conversational queries with context
✅ Conversation history display
✅ Session persistence (in-memory)

## What's Next (Phase A: Backend)

- [ ] Multi-page PDF rendering
- [ ] Better text selection/highlighting
- [ ] SQLite session persistence
- [ ] PDF metadata extraction (outline, concepts)
- [ ] Flag functionality
- [ ] Zotero integration endpoints
- [ ] Session restoration

## What's After (Phase B: Frontend)

- [ ] Proper Lit component structure
- [ ] Outline tab (extracted from PDF)
- [ ] Concepts tab (key terms extraction)
- [ ] Highlight annotations on PDF
- [ ] Session list/restore UI
- [ ] Multi-supplement handling

## API Endpoints (PoC)

- `POST /session/new` - Upload PDF, get initial analysis
- `POST /session/query` - Ask question (with optional highlight)
- `POST /session/flag` - Toggle flag on exchange
- `GET /session/{id}` - Retrieve session data
- `GET /sessions` - List all sessions

## Architecture Validated

This PoC proves:
1. Claude handles full PDF ingestion efficiently
2. Conversation context persists across queries
3. Lit + PDF.js work together seamlessly
4. FastAPI backend is simple enough for rapid iteration
5. Layout (left panel tabs + wide PDF viewer) works well

## Notes

- In-memory storage will be replaced with SQLite
- PDF rendering is single-page for now
- Text selection is basic (no proper highlight anchoring yet)
- No Zotero integration yet (manual PDF upload only)
