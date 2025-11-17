import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './pdf-viewer/pdf-viewer.ts';
import type { TextSelection } from '../types/pdf.ts';

@customElement('app-root')
export class AppRoot extends LitElement {
  @state() private pdfUrl = '';
  @state() private selectedText = '';
  @state() private selectedPage = 0;

  static styles = css`
    :host {
      display: flex;
      height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .left-panel {
      width: 300px;
      border-right: 1px solid #e0e0e0;
      display: flex;
      flex-direction: column;
      background: #f8f9fa;
      overflow-y: auto;
    }

    .panel-header {
      padding: 16px;
      background: white;
      border-bottom: 1px solid #e0e0e0;
    }

    .panel-header h2 {
      margin: 0;
      font-size: 18px;
      color: #333;
    }

    .panel-content {
      padding: 16px;
    }

    .upload-section {
      margin-bottom: 20px;
    }

    .upload-btn {
      display: inline-block;
      padding: 10px 16px;
      background: #1a73e8;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }

    .upload-btn:hover {
      background: #1557b0;
    }

    input[type='file'] {
      display: none;
    }

    .selection-info {
      background: #fff3cd;
      padding: 12px;
      border-radius: 4px;
      margin-bottom: 16px;
    }

    .selection-info h3 {
      margin: 0 0 8px 0;
      font-size: 14px;
      color: #856404;
    }

    .selection-info p {
      margin: 0;
      font-size: 13px;
      color: #856404;
      line-height: 1.5;
    }

    .info {
      color: #666;
      font-size: 14px;
      line-height: 1.5;
    }

    .center-pane {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: #525659;
      color: white;
    }

    .empty-state h2 {
      margin: 0 0 16px 0;
      font-size: 24px;
    }

    .empty-state p {
      margin: 0 0 24px 0;
      color: rgba(255, 255, 255, 0.8);
    }
  `;

  handleFileUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];

    if (file && file.type === 'application/pdf') {
      this.pdfUrl = URL.createObjectURL(file);
    }
  }

  handleTextSelection(e: CustomEvent<TextSelection>) {
    const { text, page } = e.detail;
    this.selectedText = text;
    this.selectedPage = page;
    console.log('Text selected:', { text, page });
  }

  render() {
    return html`
      <div class="left-panel">
        <div class="panel-header">
          <h2>PDF Viewer Demo</h2>
        </div>
        <div class="panel-content">
          <div class="upload-section">
            <label class="upload-btn">
              Choose PDF
              <input
                type="file"
                accept=".pdf"
                @change=${this.handleFileUpload}
              />
            </label>
          </div>

          ${this.selectedText
            ? html`
                <div class="selection-info">
                  <h3>Selected Text (Page ${this.selectedPage}):</h3>
                  <p>${this.selectedText}</p>
                </div>
              `
            : ''}

          <div class="info">
            <h3>Features:</h3>
            <ul>
              <li>Multi-page rendering</li>
              <li>Text selection</li>
              <li>Zoom controls</li>
              <li>Page navigation</li>
              <li>Virtualized scrolling</li>
            </ul>
          </div>
        </div>
      </div>

      <div class="center-pane">
        ${this.pdfUrl
          ? html`
              <pdf-viewer
                .pdfUrl=${this.pdfUrl}
                @text-selected=${this.handleTextSelection}
              ></pdf-viewer>
            `
          : html`
              <div class="empty-state">
                <h2>Welcome to PDF Viewer</h2>
                <p>Upload a PDF to get started</p>
                <label class="upload-btn">
                  Choose PDF
                  <input
                    type="file"
                    accept=".pdf"
                    @change=${this.handleFileUpload}
                  />
                </label>
              </div>
            `}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'app-root': AppRoot;
  }
}
