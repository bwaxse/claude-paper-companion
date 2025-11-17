# Paper Companion Frontend

Modern web frontend for Paper Companion built with Lit + TypeScript + PDF.js.

## Features

- **Multi-page PDF Viewer** - Render PDFs with virtualized scrolling for performance
- **Text Selection** - Select and highlight text from PDF pages
- **Zoom Controls** - Zoom in/out and reset view
- **Page Navigation** - Navigate between pages with prev/next buttons
- **Responsive Design** - Clean layout with left panel and wide PDF viewer

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000` (for full integration)

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Opens at `http://localhost:5173`

### Build

```bash
npm run build
```

Output in `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── app-root.ts           # Main app component
│   │   └── pdf-viewer/
│   │       └── pdf-viewer.ts     # Multi-page PDF viewer
│   ├── types/
│   │   ├── session.ts            # Session & conversation types
│   │   ├── query.ts              # Query request/response types
│   │   └── pdf.ts                # PDF-related types
│   ├── styles/
│   │   ├── global.css            # Global styles
│   │   └── theme.ts              # Design tokens
│   └── services/                 # (Coming soon: API client)
├── index.html                    # Entry point
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Components

### `<pdf-viewer>`

Multi-page PDF viewer with text layer for selection.

**Properties:**
- `pdfUrl` (string) - URL or blob URL of PDF to display
- `scale` (number) - Zoom level (default: 1.5)

**Events:**
- `text-selected` - Emitted when user selects text
  - `detail.text` - Selected text
  - `detail.page` - Page number

**Methods:**
- `zoomIn()` - Increase zoom
- `zoomOut()` - Decrease zoom
- `resetZoom()` - Reset to default zoom
- `goToPage(page: number)` - Navigate to specific page
- `nextPage()` - Go to next page
- `prevPage()` - Go to previous page

**Example:**
```typescript
<pdf-viewer
  .pdfUrl=${pdfUrl}
  @text-selected=${handleSelection}
></pdf-viewer>
```

### `<app-root>`

Main application shell (demo version).

Currently demonstrates:
- File upload
- PDF viewing
- Text selection display

## Architecture

Built with:
- **Lit 3.1** - Fast, lightweight web components
- **PDF.js 3.11** - Mozilla's PDF rendering library
- **TypeScript 5.3** - Type safety
- **Vite 5** - Fast builds and dev server

## Performance Optimizations

The PDF viewer uses several techniques for optimal performance:

1. **Virtualized Rendering** - Uses IntersectionObserver to only render visible pages
2. **Lazy Loading** - Pages render as they scroll into view
3. **Buffer Zone** - Pre-renders pages 500px before they're visible
4. **Text Layer Optimization** - Lightweight transparent text layer for selection

## Development Tips

### Adding New Components

1. Create component in `src/components/`
2. Use Lit decorators: `@customElement`, `@property`, `@state`
3. Import and use in parent components

### TypeScript Configuration

The project uses strict TypeScript with:
- `experimentalDecorators: true` - For Lit decorators
- `useDefineForClassFields: false` - Required for Lit compatibility

### Vite Proxy Configuration

The Vite dev server proxies API calls to the backend:
- `/sessions/*` → `http://localhost:8000/sessions/*`
- `/zotero/*` → `http://localhost:8000/zotero/*`

## Next Steps

This is the MVP PDF viewer component. Next to build:

1. **Ask Tab Component** - Query input + conversation display
2. **Left Panel Tabs** - Outline, Concepts, Ask tabs
3. **API Service Layer** - Backend integration
4. **Session Management** - Pick up where you left off
5. **Highlights** - Visual markers on PDF pages

See `TODO_PHASE_B.md` in project root for full roadmap.

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 15+
- Edge 90+

(Requires ES2020 and Web Components support)

## License

See LICENSE file in repository root.
