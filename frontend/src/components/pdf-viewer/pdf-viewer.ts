import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import * as pdfjsLib from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import type { TextSelection } from '../../types/pdf.ts';

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc =
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

@customElement('pdf-viewer')
export class PdfViewer extends LitElement {
  @property({ type: String }) pdfUrl = '';
  @property({ type: Number }) scale = 1.5;

  @state() private pdf?: PDFDocumentProxy;
  @state() private numPages = 0;
  @state() private loading = true;
  @state() private error = '';
  @state() private currentPage = 1;

  private renderingPages = new Set<number>();
  private renderTasks = new Map<number, any>(); // Track active render tasks
  private intersectionObserver?: IntersectionObserver;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #525659;
    }

    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: #323639;
      color: white;
      border-bottom: 1px solid #000;
    }

    .toolbar-section {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .toolbar button {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: white;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }

    .toolbar button:hover {
      background: rgba(255, 255, 255, 0.2);
    }

    .toolbar button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .page-info {
      font-size: 14px;
    }

    .pdf-container {
      flex: 1;
      overflow-y: auto;
      overflow-x: auto;
      padding: 20px;
    }

    .pages {
      display: flex;
      flex-direction: column;
      gap: 20px;
      align-items: center;
      margin: 0 auto;
      width: fit-content;
      min-width: 100%;
    }

    .page {
      position: relative;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      background: white;
    }

    .page canvas {
      display: block;
    }

    .textLayer {
      position: absolute;
      left: 0;
      top: 0;
      right: 0;
      bottom: 0;
      overflow: hidden;
      opacity: 0.2;
      line-height: 1.0;
      user-select: text;
    }

    .textLayer > span {
      color: transparent;
      position: absolute;
      white-space: pre;
      cursor: text;
      transform-origin: 0% 0%;
    }

    .textLayer ::selection {
      background: rgba(26, 115, 232, 0.3);
    }

    .loading,
    .error {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: white;
      font-size: 16px;
    }

    .error {
      color: #ff6b6b;
    }

    .page-placeholder {
      width: 800px;
      height: 1100px;
      background: rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      color: rgba(255, 255, 255, 0.5);
    }
  `;

  async firstUpdated() {
    if (this.pdfUrl) {
      await this.loadPDF();
    }
  }

  async updated(changedProperties: Map<string, any>) {
    if (changedProperties.has('pdfUrl') && this.pdfUrl) {
      await this.loadPDF();
    }
    if (changedProperties.has('scale') && this.pdf) {
      await this.rerenderVisiblePages();
    }
  }

  async loadPDF() {
    this.loading = true;
    this.error = '';

    try {
      const loadingTask = pdfjsLib.getDocument(this.pdfUrl);
      this.pdf = await loadingTask.promise;
      this.numPages = this.pdf.numPages;
      this.loading = false;

      // Set up intersection observer after pages are rendered
      await this.updateComplete;
      this.setupIntersectionObserver();
    } catch (err) {
      console.error('Error loading PDF:', err);
      this.error = 'Failed to load PDF. Please try again.';
      this.loading = false;
    }
  }

  setupIntersectionObserver() {
    // Clean up existing observer
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }

    // Observe page containers to render only visible pages
    this.intersectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const pageNum = parseInt(
              (entry.target as HTMLElement).dataset.page || '0'
            );
            if (pageNum > 0) {
              this.renderPage(pageNum);
            }
          }
        });
      },
      {
        root: this.shadowRoot?.querySelector('.pdf-container'),
        rootMargin: '500px', // Pre-render pages that are close to viewport
        threshold: 0.01
      }
    );

    // Observe all page containers
    const pageContainers = this.shadowRoot?.querySelectorAll('.page');
    pageContainers?.forEach((container) => {
      this.intersectionObserver?.observe(container);
    });
  }

  async renderPage(pageNum: number) {
    if (!this.pdf || this.renderingPages.has(pageNum)) {
      return;
    }

    // Cancel any existing render task for this page
    const existingTask = this.renderTasks.get(pageNum);
    if (existingTask) {
      existingTask.cancel();
      this.renderTasks.delete(pageNum);
    }

    this.renderingPages.add(pageNum);

    try {
      const page = await this.pdf.getPage(pageNum);
      const viewport = page.getViewport({ scale: this.scale });

      const pageContainer = this.shadowRoot?.querySelector(
        `.page[data-page="${pageNum}"]`
      );
      if (!pageContainer) return;

      const canvas = pageContainer.querySelector('canvas') as HTMLCanvasElement;
      const textLayerDiv = pageContainer.querySelector('.textLayer') as HTMLElement;

      if (!canvas || !textLayerDiv) return;

      // Render canvas
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const context = canvas.getContext('2d');
      if (context) {
        const renderTask = page.render({ canvasContext: context, viewport });
        this.renderTasks.set(pageNum, renderTask);

        try {
          await renderTask.promise;
        } catch (err: any) {
          // Ignore cancellation errors
          if (err.name === 'RenderingCancelledException') {
            return;
          }
          throw err;
        }
      }

      // Render text layer with proper positioning
      const textContent = await page.getTextContent();
      textLayerDiv.innerHTML = '';
      textLayerDiv.style.width = viewport.width + 'px';
      textLayerDiv.style.height = viewport.height + 'px';

      textContent.items.forEach((item: any) => {
        if (item.str) {
          const span = document.createElement('span');
          span.textContent = item.str;

          // Calculate proper transform
          const transform = pdfjsLib.Util.transform(
            viewport.transform,
            item.transform
          );

          // Extract position and scale
          const angle = Math.atan2(transform[1], transform[0]);
          const fontHeight = Math.sqrt(transform[2] * transform[2] + transform[3] * transform[3]);

          // Position the span
          span.style.left = transform[4] + 'px';
          span.style.top = (transform[5] - fontHeight) + 'px'; // Adjust for baseline
          span.style.fontSize = fontHeight + 'px';
          span.style.fontFamily = item.fontName || 'sans-serif';

          if (angle !== 0) {
            span.style.transform = `rotate(${angle}rad)`;
          }

          textLayerDiv.appendChild(span);
        }
      });

      // Add text selection listener
      textLayerDiv.addEventListener('mouseup', () => this.handleTextSelection(pageNum));
    } catch (err) {
      console.error(`Error rendering page ${pageNum}:`, err);
    } finally {
      this.renderingPages.delete(pageNum);
      this.renderTasks.delete(pageNum);
    }
  }

  async rerenderVisiblePages() {
    // Cancel all active render tasks
    this.renderTasks.forEach((task) => {
      task.cancel();
    });
    this.renderTasks.clear();

    // Clear rendering state and re-render visible pages
    this.renderingPages.clear();
    const pageContainers = this.shadowRoot?.querySelectorAll('.page');
    pageContainers?.forEach((container) => {
      const pageNum = parseInt((container as HTMLElement).dataset.page || '0');
      if (pageNum > 0) {
        this.renderPage(pageNum);
      }
    });
  }

  handleTextSelection(pageNum: number) {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim();

    if (selectedText) {
      const textSelection: TextSelection = {
        text: selectedText,
        page: pageNum
      };

      this.dispatchEvent(
        new CustomEvent('text-selected', {
          detail: textSelection,
          bubbles: true,
          composed: true
        })
      );
    }
  }

  zoomIn() {
    this.scale = Math.min(this.scale + 0.25, 3.0);
  }

  zoomOut() {
    this.scale = Math.max(this.scale - 0.25, 0.5);
  }

  resetZoom() {
    this.scale = 1.5;
  }

  goToPage(page: number) {
    if (page < 1 || page > this.numPages) return;

    const pageContainer = this.shadowRoot?.querySelector(
      `.page[data-page="${page}"]`
    );

    if (pageContainer) {
      pageContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
      this.currentPage = page;
    }
  }

  nextPage() {
    this.goToPage(this.currentPage + 1);
  }

  prevPage() {
    this.goToPage(this.currentPage - 1);
  }

  render() {
    if (this.loading) {
      return html`<div class="loading">Loading PDF...</div>`;
    }

    if (this.error) {
      return html`<div class="error">${this.error}</div>`;
    }

    if (!this.pdf) {
      return html`<div class="loading">No PDF loaded</div>`;
    }

    return html`
      <div class="toolbar">
        <div class="toolbar-section">
          <button @click=${this.prevPage} ?disabled=${this.currentPage === 1}>
            Previous
          </button>
          <span class="page-info">
            Page ${this.currentPage} / ${this.numPages}
          </span>
          <button @click=${this.nextPage} ?disabled=${this.currentPage === this.numPages}>
            Next
          </button>
        </div>

        <div class="toolbar-section">
          <button @click=${this.zoomOut} ?disabled=${this.scale <= 0.5}>
            Zoom Out
          </button>
          <span class="page-info">${Math.round(this.scale * 100)}%</span>
          <button @click=${this.zoomIn} ?disabled=${this.scale >= 3.0}>
            Zoom In
          </button>
          <button @click=${this.resetZoom}>
            Reset
          </button>
        </div>
      </div>

      <div class="pdf-container">
        <div class="pages">
          ${Array.from({ length: this.numPages }, (_, i) => i + 1).map(
            (pageNum) => html`
              <div class="page" data-page="${pageNum}">
                <canvas></canvas>
                <div class="textLayer"></div>
              </div>
            `
          )}
        </div>
      </div>
    `;
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'pdf-viewer': PdfViewer;
  }
}
