import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, ApiError } from '../services/api';
import type { ConversationMessage } from '../types/session';
import type { TextSelection } from '../types/pdf';
import './pdf-viewer/pdf-viewer';
import './left-panel/ask-tab';
import './shared/loading-spinner';
import './shared/error-message';

@customElement('app-root')
export class AppRoot extends LitElement {
  @state() private sessionId = '';
  @state() private filename = '';
  @state() private pdfUrl = '';
  @state() private conversation: ConversationMessage[] = [];
  @state() private flags: number[] = [];
  @state() private selectedText = '';
  @state() private selectedPage?: number;
  @state() private loading = false;
  @state() private error = '';

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
    }

    .panel-header {
      padding: 16px;
      background: white;
      border-bottom: 1px solid #e0e0e0;
      flex-shrink: 0;
    }

    .panel-header h1 {
      margin: 0 0 4px 0;
      font-size: 18px;
      color: #333;
    }

    .panel-header .filename {
      margin: 0;
      font-size: 13px;
      color: #666;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
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
      padding: 40px;
      text-align: center;
    }

    .empty-state h2 {
      margin: 0 0 16px 0;
      font-size: 32px;
    }

    .empty-state p {
      margin: 0 0 32px 0;
      color: rgba(255, 255, 255, 0.8);
      font-size: 16px;
      max-width: 400px;
    }

    .upload-btn {
      padding: 14px 28px;
      background: #1a73e8;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .upload-btn:hover {
      background: #1557b0;
    }

    input[type='file'] {
      display: none;
    }

    .loading-screen {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: #525659;
    }

    .error-screen {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      background: #525659;
      padding: 40px;
    }

    .error-screen error-message {
      max-width: 500px;
      margin-bottom: 20px;
    }

    ask-tab {
      flex: 1;
      min-height: 0;
    }
  `;

  async handleFileUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file || file.type !== 'application/pdf') {
      this.error = 'Please select a valid PDF file';
      return;
    }

    this.loading = true;
    this.error = '';

    try {
      // Create session with backend
      const session = await api.createSession(file);

      this.sessionId = session.session_id;
      this.filename = session.filename;
      this.pdfUrl = URL.createObjectURL(file);

      // Initialize conversation with initial analysis
      this.conversation = [
        {
          id: 0,
          role: 'user',
          content: 'Initial analysis',
          timestamp: session.created_at
        },
        {
          id: 1,
          role: 'assistant',
          content: session.initial_analysis,
          timestamp: session.created_at
        }
      ];

      this.loading = false;
    } catch (err) {
      console.error('Upload error:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to upload PDF. Please try again.';
      }
      this.loading = false;
    }

    // Reset file input
    input.value = '';
  }

  handleTextSelection(e: CustomEvent<TextSelection>) {
    const { text, page } = e.detail;
    this.selectedText = text;
    this.selectedPage = page;
  }

  handleClearSelection() {
    this.selectedText = '';
    this.selectedPage = undefined;
  }

  private renderEmptyState() {
    return html`
      <div class="empty-state">
        <h2>Paper Companion</h2>
        <p>
          Upload a PDF to get started. Ask questions about your paper with AI-powered
          analysis.
        </p>
        <label class="upload-btn">
          Upload PDF
          <input type="file" accept=".pdf" @change=${this.handleFileUpload} />
        </label>
      </div>
    `;
  }

  private renderLoadingScreen() {
    return html`
      <div class="loading-screen">
        <loading-spinner
          size="large"
          message="Analyzing paper..."
        ></loading-spinner>
      </div>
    `;
  }

  private renderErrorScreen() {
    return html`
      <div class="error-screen">
        <error-message .message=${this.error}></error-message>
        <label class="upload-btn">
          Try Again
          <input type="file" accept=".pdf" @change=${this.handleFileUpload} />
        </label>
      </div>
    `;
  }

  render() {
    return html`
      <div class="left-panel">
        <div class="panel-header">
          <h1>Paper Companion</h1>
          ${this.filename
            ? html`<p class="filename" title="${this.filename}">${this.filename}</p>`
            : ''}
        </div>

        <ask-tab
          .sessionId=${this.sessionId}
          .conversation=${this.conversation}
          .flags=${this.flags}
          .selectedText=${this.selectedText}
          .selectedPage=${this.selectedPage}
          @conversation-updated=${(e: CustomEvent) =>
            (this.conversation = e.detail.conversation)}
          @flags-updated=${(e: CustomEvent) => (this.flags = e.detail.flags)}
          @clear-selection=${this.handleClearSelection}
        ></ask-tab>
      </div>

      <div class="center-pane">
        ${this.loading
          ? this.renderLoadingScreen()
          : this.error
          ? this.renderErrorScreen()
          : this.pdfUrl
          ? html`
              <pdf-viewer
                .pdfUrl=${this.pdfUrl}
                @text-selected=${this.handleTextSelection}
              ></pdf-viewer>
            `
          : this.renderEmptyState()}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'app-root': AppRoot;
  }
}
