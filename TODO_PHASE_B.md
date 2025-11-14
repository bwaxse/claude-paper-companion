# Phase B: Frontend Development - Implementation Plan

## Overview
Build a Lumi-inspired web frontend using Lit + TypeScript that integrates with the Phase A FastAPI backend. Focus on clean UX for paper reading with conversational AI assistance.

## Design Reference
**This chat (November 14, 2025)** contains detailed design decisions:
- Layout: Left panel (tabs) + Wide center (PDF viewer)
- UI patterns borrowed from Lumi
- Token optimization strategy
- PDF rendering approach

**Lumi source:** https://github.com/PAIR-code/lumi (Apache 2.0 licensed)

## Layout Design (Final)

```
┌─────────────────────────────────────────────────────┐
│  Paper Companion Web                                │
│  ┌────────────┬──────────────────────────────────┐  │
│  │ Left Panel │      Center Pane (Wide)         │  │
│  │ (300px)    │                                  │  │
│  │            │                                  │  │
│  │ [Tabs]     │   PDF Viewer (PDF.js)           │  │
│  │ ────────   │   - Multi-page rendering        │  │
│  │            │   - Text selection layer        │  │
│  │ Content:   │   - Highlight anchoring         │  │
│  │ • Outline  │   - Scroll navigation           │  │
│  │ • Concepts │                                  │  │
│  │ • Ask      │                                  │  │
│  │   - Query  │                                  │  │
│  │     input  │                                  │  │
│  │   - Conv.  │                                  │  │
│  │     history│                                  │  │
│  │   - Flags  │                                  │  │
│  └────────────┴──────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── app-root.ts              # Main app component
│   │   ├── left-panel/
│   │   │   ├── left-panel.ts        # Panel container
│   │   │   ├── outline-tab.ts       # Outline/TOC
│   │   │   ├── concepts-tab.ts      # Key concepts
│   │   │   └── ask-tab.ts           # Conversation UI
│   │   ├── pdf-viewer/
│   │   │   ├── pdf-viewer.ts        # PDF.js wrapper
│   │   │   ├── pdf-page.ts          # Single page component
│   │   │   └── text-layer.ts        # Selection layer
│   │   ├── shared/
│   │   │   ├── query-input.ts       # Reusable input
│   │   │   ├── conversation-item.ts # Message display
│   │   │   └── loading-spinner.ts   # Loading states
│   │   └── session-picker/
│   │       └── session-list.ts      # "Pick up where left off"
│   ├── services/
│   │   ├── api.ts                   # Backend API client
│   │   └── session-storage.ts      # LocalStorage wrapper
│   ├── types/
│   │   ├── session.ts               # TypeScript interfaces
│   │   ├── query.ts
│   │   └── pdf.ts
│   ├── styles/
│   │   ├── global.css               # Global styles
│   │   └── theme.ts                 # Design tokens
│   └── index.html                   # Entry point
├── public/
│   └── favicon.ico
├── package.json
├── tsconfig.json
├── vite.config.ts                   # Build config
└── README.md
```

## Phase B Tasks (Ordered)

### Task 1: Project Setup
**Files: `package.json`, `tsconfig.json`, `vite.config.ts`**

- [ ] Initialize npm project
- [ ] Install dependencies:
  ```json
  {
    "dependencies": {
      "lit": "^3.1.0",
      "pdfjs-dist": "^3.11.174"
    },
    "devDependencies": {
      "typescript": "^5.3.0",
      "vite": "^5.0.0",
      "@types/node": "^20.0.0"
    }
  }
  ```
- [ ] Configure TypeScript (strict mode)
- [ ] Configure Vite for development
- [ ] Set up dev server with proxy to backend

**Vite proxy config:**
```typescript
export default {
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
}
```

### Task 2: TypeScript Interfaces
**File: `src/types/session.ts`**
```typescript
export interface Session {
  session_id: string;
  filename: string;
  created_at: string;
  initial_analysis: string;
}

export interface ConversationMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  highlighted_text?: string;
  page?: number;
  timestamp: string;
  model?: string;
  flagged?: boolean;
}

export interface SessionFull extends Session {
  conversation: ConversationMessage[];
  flags: number[];
  highlights: Highlight[];
}
```

**File: `src/types/query.ts`**
```typescript
export interface QueryRequest {
  query: string;
  highlighted_text?: string;
  page?: number;
}

export interface QueryResponse {
  exchange_id: number;
  response: string;
  model_used: string;
}
```

**File: `src/types/pdf.ts`**
```typescript
export interface OutlineItem {
  title: string;
  page: number;
  level: number;
  children?: OutlineItem[];
}

export interface Concept {
  term: string;
  frequency: number;
  pages: number[];
}

export interface Highlight {
  text: string;
  page: number;
  exchange_id?: number;
  coords?: BoundingBox;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}
```

### Task 3: API Service Layer
**File: `src/services/api.ts`**

- [ ] Create ApiClient class
- [ ] Methods for all backend endpoints:
  ```typescript
  class ApiClient {
    async createSession(file: File): Promise<Session>
    async createSessionFromZotero(key: string): Promise<Session>
    async getSession(sessionId: string): Promise<SessionFull>
    async listSessions(): Promise<Session[]>
    async query(sessionId: string, request: QueryRequest): Promise<QueryResponse>
    async toggleFlag(sessionId: string, exchangeId: number): Promise<void>
    async deleteSession(sessionId: string): Promise<void>
    
    // Zotero
    async searchZotero(query: string): Promise<ZoteroItem[]>
    async getRecentPapers(limit: number): Promise<ZoteroItem[]>
  }
  ```
- [ ] Add error handling and retries
- [ ] Add loading state management
- [ ] Export singleton instance

### Task 4: Design System
**File: `src/styles/theme.ts`**
```typescript
export const theme = {
  colors: {
    primary: '#1a73e8',
    primaryHover: '#1557b0',
    background: '#f8f9fa',
    surface: '#ffffff',
    border: '#e0e0e0',
    text: '#333333',
    textSecondary: '#666666',
    highlight: '#fff3cd',
    highlightText: '#856404',
    flag: '#f4b400',
    pdfBackground: '#525659'
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '20px',
    xxl: '24px'
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: {
      sm: '13px',
      base: '14px',
      lg: '16px',
      xl: '18px'
    }
  },
  layout: {
    leftPanelWidth: '300px',
    maxContentWidth: '1200px'
  }
}
```

**File: `src/styles/global.css`**
- [ ] CSS reset
- [ ] Global typography
- [ ] Scrollbar styling
- [ ] Selection styling

### Task 5: Multi-Page PDF Viewer
**File: `src/components/pdf-viewer/pdf-viewer.ts`**

This is the most complex component. Key features:

- [ ] Load PDF with PDF.js
- [ ] Render all pages (virtualized scrolling for performance)
- [ ] Text layer for each page (selection)
- [ ] Highlight layer (visual markers)
- [ ] Page navigation
- [ ] Zoom controls
- [ ] Search within PDF (future)

**Implementation approach:**
```typescript
class PdfViewer extends LitElement {
  @property() pdfUrl: string;
  @property() highlights: Highlight[] = [];
  
  private pdf?: PDFDocumentProxy;
  private pages: PDFPageProxy[] = [];
  private textLayers: Map<number, HTMLElement> = new Map();
  
  async loadPdf() {
    // Load PDF with PDF.js
    // Render all pages with text layers
    // Set up intersection observer for lazy rendering
  }
  
  handleTextSelection() {
    // Capture selection
    // Emit 'text-selected' event with {text, page, coords}
  }
  
  addHighlight(highlight: Highlight) {
    // Draw highlight overlay on specific page
  }
}
```

**Performance optimization:**
- Use Intersection Observer for lazy page rendering
- Only render visible pages + buffer (±2 pages)
- Unload offscreen pages after scrolling past

### Task 6: PDF Text Layer Component
**File: `src/components/pdf-viewer/text-layer.ts`**

- [ ] Render transparent text spans over canvas
- [ ] Position using PDF.js text content data
- [ ] Handle selection events
- [ ] Calculate bounding boxes for highlights
- [ ] Emit selection events to parent

**Text layer rendering:**
```typescript
async renderTextLayer(page: PDFPageProxy, viewport: PageViewport) {
  const textContent = await page.getTextContent();
  
  textContent.items.forEach(item => {
    const tx = pdfjsLib.Util.transform(
      pdfjsLib.Util.transform(viewport.transform, item.transform),
      [1, 0, 0, -1, 0, 0]
    );
    
    // Create span with precise positioning
    // Add to text layer container
  });
}
```

### Task 7: Left Panel Container
**File: `src/components/left-panel/left-panel.ts`**

- [ ] Tab navigation (Outline, Concepts, Ask)
- [ ] Tab state management
- [ ] Responsive tab switching
- [ ] Emit tab change events

```typescript
class LeftPanel extends LitElement {
  @property() activeTab: 'outline' | 'concepts' | 'ask' = 'ask';
  @property() sessionId?: string;
  
  render() {
    return html`
      <div class="tabs">
        <button @click=${() => this.activeTab = 'outline'}>Outline</button>
        <button @click=${() => this.activeTab = 'concepts'}>Concepts</button>
        <button @click=${() => this.activeTab = 'ask'}>Ask</button>
      </div>
      <div class="tab-content">
        ${this.renderActiveTab()}
      </div>
    `;
  }
}
```

### Task 8: Outline Tab
**File: `src/components/left-panel/outline-tab.ts`**

- [ ] Display hierarchical outline from backend
- [ ] Click outline item → scroll to page
- [ ] Nested structure (h1, h2, h3)
- [ ] Current section highlighting

**Get outline from backend:**
```typescript
// Backend should provide outline via new endpoint
GET /sessions/{id}/outline
Response: OutlineItem[]
```

**Note:** Backend needs to extract outline in Phase A (Task 3 mentions this, ensure it's implemented)

### Task 9: Concepts Tab
**File: `src/components/left-panel/concepts-tab.ts`**

- [ ] Display key concepts/terms
- [ ] Click concept → highlight occurrences in PDF
- [ ] Show frequency count
- [ ] Show pages where concept appears
- [ ] Search/filter concepts

**Get concepts from backend:**
```typescript
// Backend should provide concepts via new endpoint
GET /sessions/{id}/concepts
Response: Concept[]
```

**Simple concept extraction (backend):**
- Frequency analysis of nouns
- Filter common words
- Return top 20-30 terms

### Task 10: Ask Tab (Conversation UI)
**File: `src/components/left-panel/ask-tab.ts`**

- [ ] Display conversation history
- [ ] Query input at bottom
- [ ] Show highlighted text context
- [ ] Flag buttons on responses
- [ ] Auto-scroll to latest
- [ ] Loading states
- [ ] Error handling

**UI structure:**
```typescript
class AskTab extends LitElement {
  @property() sessionId: string;
  @property() conversation: ConversationMessage[] = [];
  @property() loading: boolean = false;
  @property() selectedText?: string;
  
  async handleQuery(query: string) {
    this.loading = true;
    const response = await api.query(this.sessionId, {
      query,
      highlighted_text: this.selectedText
    });
    // Add to conversation, clear input, scroll
    this.loading = false;
  }
}
```

### Task 11: Conversation Item Component
**File: `src/components/shared/conversation-item.ts`**

- [ ] Display user query
- [ ] Display assistant response
- [ ] Show highlighted text context (yellow bg)
- [ ] Flag button with toggle state
- [ ] Timestamp
- [ ] Model badge (Haiku/Sonnet)
- [ ] Copy response button

**Visual design:**
```
┌─────────────────────────────────────┐
│ [Highlighted: "transformer arch..."]│ ← If present
│ How does positional encoding work?  │ ← User query
├─────────────────────────────────────┤
│ The positional encodings use sine...│ ← Assistant response
│                                  ★  │ ← Flag button
│ Sonnet • 2:34 PM              [Copy]│ ← Footer
└─────────────────────────────────────┘
```

### Task 12: Query Input Component
**File: `src/components/shared/query-input.ts`**

- [ ] Textarea with auto-resize
- [ ] Show selected text preview above input
- [ ] Clear selected text button
- [ ] Submit button
- [ ] Keyboard shortcuts (Cmd+Enter to submit)
- [ ] Character count (optional)
- [ ] Disable when loading

### Task 13: Session Picker
**File: `src/components/session-picker/session-list.ts`**

For "pick up where left off" functionality:

- [ ] List all sessions
- [ ] Show filename, date, # exchanges
- [ ] Click to load session
- [ ] Delete button
- [ ] Search/filter sessions
- [ ] Sort by date (newest first)
- [ ] Empty state (no sessions)

**Show on:**
- App startup (before any session loaded)
- Menu button "Switch Paper"
- After deleting current session

### Task 14: Main App Component
**File: `src/components/app-root.ts`**

Orchestrates everything:

- [ ] Route to session picker or main view
- [ ] Handle file upload
- [ ] Handle Zotero paper selection
- [ ] Pass data between components
- [ ] Global loading state
- [ ] Global error handling
- [ ] Keyboard shortcuts
- [ ] Connection to backend API

**App states:**
```typescript
type AppState = 
  | { type: 'no-session' }           // Show upload/picker
  | { type: 'loading' }               // Initial PDF load
  | { type: 'session-active', sessionId: string, pdfUrl: string }
  | { type: 'error', message: string }
```

### Task 15: Session Management
**File: `src/services/session-storage.ts`**

Use LocalStorage for UI preferences only (not data):

- [ ] Last active session ID
- [ ] Active tab preference
- [ ] PDF zoom level
- [ ] UI preferences (theme, etc.)

**Don't store in LocalStorage:**
- Conversation data (comes from backend)
- PDF content
- Anything already in backend DB

### Task 16: Loading & Error States
**File: `src/components/shared/loading-spinner.ts`**

- [ ] Consistent spinner component
- [ ] Use throughout app
- [ ] Skeleton loaders for lists

**Error handling:**
- [ ] Global error boundary
- [ ] Toast notifications for errors
- [ ] Retry buttons where appropriate
- [ ] Network error detection

### Task 17: File Upload Flow
**In `app-root.ts`:**

```
User uploads PDF
    ↓
Show loading spinner
    ↓
POST /sessions/new (sends file)
    ↓
Receive session_id + initial_analysis
    ↓
Load PDF in viewer (client-side)
    ↓
Display initial analysis in Ask tab
    ↓
Ready for queries
```

### Task 18: Zotero Integration UI
**New component: `zotero-picker.ts`**

- [ ] Search Zotero library
- [ ] Show recent papers
- [ ] Select paper → creates session
- [ ] Show paper metadata while searching

**Flow:**
```
Click "Load from Zotero"
    ↓
Show Zotero picker modal
    ↓
User searches or browses recent
    ↓
User selects paper
    ↓
POST /sessions/new (with zotero_key)
    ↓
Backend fetches PDF, creates session
    ↓
Close modal, load session
```

### Task 19: Keyboard Shortcuts
**Implement in `app-root.ts`:**

- [ ] `Cmd/Ctrl + K` - Focus query input
- [ ] `Cmd/Ctrl + Enter` - Submit query
- [ ] `Cmd/Ctrl + F` - Search in PDF (future)
- [ ] `Cmd/Ctrl + Shift + F` - Flag last exchange
- [ ] `Escape` - Clear text selection
- [ ] `1/2/3` - Switch tabs (when not typing)

### Task 20: Responsive Design (Optional)
**If time permits:**

- [ ] Mobile breakpoint (< 768px)
- [ ] Stack layout (panel above PDF)
- [ ] Touch-friendly buttons
- [ ] Hamburger menu for tabs

### Task 21: Testing
**File: `tests/frontend/`**

- [ ] Component tests with Lit testing helpers
- [ ] PDF viewer integration test
- [ ] API service mocking
- [ ] E2E test with Playwright (upload → query → response)

### Task 22: Build & Deploy
**Files: `vite.config.ts`, `Dockerfile` (optional)**

- [ ] Production build configuration
- [ ] Asset optimization
- [ ] Serve static files via backend or CDN
- [ ] Environment variable handling (API_URL)

**Deployment options:**
- Serve frontend from FastAPI (`app.mount()`)
- Deploy to Netlify/Vercel with API proxy
- Docker container with nginx

### Task 23: Documentation
**File: `frontend/README.md`**

- [ ] Development setup
- [ ] Component architecture
- [ ] How to add new features
- [ ] Build instructions
- [ ] Deployment guide

## Lumi Components to Reference

**Extract/adapt these from Lumi:**
1. **Sidebar component structure** - Clean tab navigation
2. **PDF text overlay technique** - They've solved this well
3. **Annotation styling** - Clean, minimal design
4. **Loading states** - Skeleton screens
5. **Color scheme** - Professional, academic feel

**What NOT to take from Lumi:**
- Firebase integration (we use FastAPI)
- LaTeX rendering (we use PDF.js)
- Their specific AI prompts
- ArXiv-specific features

## UI/UX Principles

**From our discussion:**
1. **Left panel for tools, center for reading** - Don't interrupt reading flow
2. **Progressive disclosure** - Show what's needed when needed
3. **Responsive to context** - Selected text → show in query input
4. **Minimal friction** - Fast loading, smooth interactions
5. **Preserve state** - "Pick up where left off" is critical

## Performance Targets

- Initial load: < 2s
- PDF rendering: < 1s per page
- Query response: < 3s (depends on Claude)
- Smooth scrolling at 60fps
- Bundle size: < 500KB gzipped

## Success Criteria

**Phase B is complete when:**
- ✅ Can upload PDF → see it rendered with text selection
- ✅ Can select text → query about it → see response
- ✅ Can flag exchanges
- ✅ Can navigate via outline
- ✅ Can see key concepts
- ✅ Can load paper from Zotero
- ✅ Can "pick up where left off" (session list)
- ✅ All three tabs functional
- ✅ Responsive design works
- ✅ Production build deploys successfully

## Development Workflow

```bash
# Terminal 1 - Backend (from Phase A)
cd paper-companion/web
python -m uvicorn api.main:app --reload

# Terminal 2 - Frontend
cd paper-companion/frontend
npm run dev

# Opens http://localhost:5173
# Auto-proxies /api/* to http://localhost:8000
```

## Common Pitfalls to Avoid

1. **Shadow DOM issues** - PDF.js text layer needs careful DOM handling
2. **Memory leaks** - Clean up PDF pages when scrolling
3. **Text selection** - Browser selection API can be tricky across shadow boundaries
4. **Highlight positioning** - PDF coordinates ≠ screen coordinates
5. **State management** - Keep source of truth in backend, not frontend

## Integration with Phase A

**Backend endpoints needed for Phase B:**
- `GET /sessions/{id}/outline` - For Outline tab
- `GET /sessions/{id}/concepts` - For Concepts tab
- All existing endpoints from Phase A

**If these don't exist, add them in Phase A or create stubs in Phase B.**

## Nice-to-Have Features (Post Phase B)

- Multi-supplement viewing (tabs for main + supplements)
- PDF annotation tools (draw, comment)
- Export conversation to PDF/markdown
- Share session (read-only link)
- Compare two papers side-by-side
- Dark mode
- Custom highlight colors
- Keyboard navigation through PDF

## Timeline Estimate

- Tasks 1-4: 2-3 hours (setup, types, services)
- Tasks 5-6: 4-6 hours (PDF viewer - most complex)
- Tasks 7-12: 3-4 hours (left panel components)
- Tasks 13-14: 2-3 hours (session picker, app root)
- Tasks 15-20: 2-3 hours (polish, shortcuts, states)
- Tasks 21-23: 2-3 hours (testing, build, docs)

**Total: ~15-20 hours of focused development**

## Phase B Deliverables

1. Complete Lit + TypeScript frontend
2. Multi-page PDF viewer with text selection
3. Three-tab left panel (Outline/Concepts/Ask)
4. Session management UI
5. Zotero integration UI
6. Production build ready for deployment
7. Frontend documentation

## Next Steps After Phase B

**Polish & Production:**
- User testing with real papers
- Performance optimization
- Error handling improvements
- Analytics (optional)
- Documentation site

**Future phases (if desired):**
- Mobile app
- Collaboration features
- Integration with other tools (Obsidian, Notion)
- Advanced PDF features

## Reference This Chat

When implementing Phase B, Claude Code should reference:
- Our layout design discussion
- Token optimization decisions
- PDF.js text layer implementation we built in PoC
- Design philosophy (minimal, focused on reading)

---

**Ready to implement after Phase A is complete!**
