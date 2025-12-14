# Scholia 📚

AI-powered web application for analyzing scientific papers with Claude, featuring deep Zotero integration, PDF viewing, and conversational Q&A.

*Scholia: marginal notes or commentaries on classical texts - the perfect name for annotating research papers.*

## 🎯 What It Does

- **Upload or load PDFs** from your Zotero library
- **View papers** with built-in PDF viewer and text selection
- **Ask questions** about the paper with Claude AI
- **Get initial analysis** automatically when loading papers
- **Load supplemental PDFs** for cross-paper analysis
- **Upload supplements to Zotero** directly from the interface
- **Flag important exchanges** for later review
- **Persistent sessions** - pick up where you left off

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Anthropic API key ([get one here](https://console.anthropic.com/))
- (Optional) Zotero API credentials for library integration

### Installation

```bash
# Clone the repository
git clone https://github.com/bwaxse/scholia.git
cd scholia

# Backend setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-web.txt

# Frontend setup
cd frontend
npm install
cd ..

# Configure API keys
# Create .env file in root directory:
echo "ANTHROPIC_API_KEY=your-key-here" > .env
# Optional Zotero:
echo "ZOTERO_API_KEY=your-zotero-key" >> .env
echo "ZOTERO_LIBRARY_ID=your-library-id" >> .env
```

### Running the Application

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
uvicorn web.api.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Open your browser to **http://localhost:5173**

## 📚 Features

### PDF Analysis
- Upload PDFs or load from Zotero
- Automatic initial analysis with Claude
- Text selection and highlighting
- Multi-page viewer with zoom controls

### Conversational Q&A
- Ask questions about the paper with full context
- Claude acts as a senior researcher mentor
- References specific sections and figures
- Maintains conversation history

### Zotero Integration
- Load papers directly from your library
- Search your Zotero collection
- Auto-check for supplemental PDFs
- Upload new supplements to Zotero
- Auto-redownload PDFs when missing
- Refresh to get latest highlights

### Supplement Management
- See count of available supplements
- Load supplemental papers for cross-reference
- Upload PDFs as Zotero child attachments
- Smart filtering (excludes main PDF)

### Session Management
- Persistent sessions stored in SQLite
- Resume previous conversations
- Export session history
- Flag important exchanges

## 🏗️ Architecture

```
paper-companion/
├── web/                    # FastAPI Backend
│   ├── api/
│   │   ├── main.py        # FastAPI app
│   │   ├── routes/        # API endpoints
│   │   └── models/        # Pydantic models
│   ├── core/
│   │   ├── claude.py      # Claude API client
│   │   ├── database.py    # SQLite connection
│   │   └── pdf_processor.py
│   └── services/          # Business logic
│       ├── session_manager.py
│       ├── query_service.py
│       ├── zotero_service.py
│       └── insight_extractor.py
│
├── frontend/              # Lit + TypeScript Frontend
│   ├── src/
│   │   ├── components/    # Web components
│   │   ├── services/      # API client
│   │   └── types/         # TypeScript types
│   └── dist/              # Built files (served by backend)
│
├── requirements-web.txt   # Python dependencies
└── TODO.md               # Development roadmap
```

## 🔧 Development

### Run Tests
```bash
# Backend tests
pytest tests/

# Frontend tests
cd frontend && npm test
```

### Build for Production
```bash
# Build frontend
cd frontend
npm run build

# Frontend assets are now in frontend/dist/
# Backend will serve them automatically
```

### API Documentation

With backend running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📖 Documentation

- **[TODO.md](TODO.md)** - Current status, features, and development notes
- **[web/README.md](web/README.md)** - Backend API documentation
- **[frontend/README.md](frontend/README.md)** - Frontend component documentation

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional - Zotero Integration
ZOTERO_API_KEY=your-api-key
ZOTERO_LIBRARY_ID=your-library-id
ZOTERO_LIBRARY_TYPE=user  # or 'group'

# Optional - Database
DATABASE_PATH=./paper_companion.db  # defaults to current directory
```

## 🎨 Tech Stack

**Backend:**
- FastAPI (Python web framework)
- SQLite (database)
- Anthropic Claude API
- PyMuPDF (PDF processing)
- Pyzotero (Zotero integration)

**Frontend:**
- Lit (web components)
- TypeScript
- PDF.js (PDF rendering)
- Vite (build tool)

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Additional prompt templates
- Enhanced PDF annotations
- Export formats (Markdown, HTML)
- Multi-paper comparison
- Citation extraction
- Dark mode UI

## 📝 License

MIT

## 🙏 Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/)
- [Zotero](https://www.zotero.org/)
- [PDF.js](https://mozilla.github.io/pdf.js/)
- [Lit](https://lit.dev/)

---

**Ready to explore your research with AI! 🚀**
