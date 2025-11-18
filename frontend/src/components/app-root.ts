import { LitElement, html, css } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';
import { api, ApiError } from '../services/api';
import type { ConversationMessage, Session } from '../types/session';
import type { TextSelection, OutlineItem, Concept } from '../types/pdf';
import './pdf-viewer/pdf-viewer';
import './left-panel/left-panel';
import './session-picker/session-list';
import './shared/loading-spinner';
import './shared/error-message';
import type { PdfViewer } from './pdf-viewer/pdf-viewer';

@customElement('app-root')
export class AppRoot extends LitElement {
  @state() private sessionId = '';
  @state() private filename = '';
  @state() private pdfUrl = '';
  @state() private conversation: ConversationMessage[] = [];
  @state() private flags: number[] = [];
  @state() private outline: OutlineItem[] = [];
  @state() private concepts: Concept[] = [];
  @state() private selectedText = '';
  @state() private selectedPage?: number;
  @state() private loading = false;
  @state() private error = '';
  @state() private showSessionPicker = false;

  @query('pdf-viewer') private pdfViewer?: PdfViewer;

  static styles = css`
    :host {
      display: flex;
      height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .left-panel {
      width: 450px;
      min-width: 450px;
      flex-shrink: 0;
      border-right: 1px solid #e0e0e0;
      display: flex;
      flex-direction: column;
      background: #f8f9fa;
    }

    left-panel {
      height: 100%;
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

    .secondary-btn {
      padding: 14px 28px;
      background: transparent;
      color: white;
      border: 2px solid white;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
      font-weight: 500;
      transition: all 0.2s;
    }

    .secondary-btn:hover {
      background: rgba(255, 255, 255, 0.1);
    }

    .empty-state-actions {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      justify-content: center;
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

  handleNavigateToPage(e: CustomEvent<{ page: number }>) {
    if (this.pdfViewer) {
      this.pdfViewer.scrollToPage(e.detail.page);
    }
  }

  handleHighlightConcept(e: CustomEvent<{ concept: Concept }>) {
    // TODO: Implement concept highlighting in PDF viewer
    // For now, navigate to the first page where the concept appears
    const concept = e.detail.concept;
    if (concept.pages.length > 0 && this.pdfViewer) {
      this.pdfViewer.scrollToPage(concept.pages[0]);
    }
  }

  handleShowSessionPicker() {
    this.showSessionPicker = true;
  }

  handleCloseSessionPicker() {
    this.showSessionPicker = false;
  }

  async handleSessionSelected(e: CustomEvent<{ session: Session }>) {
    const { session } = e.detail;
    this.showSessionPicker = false;
    this.loading = true;
    this.error = '';

    try {
      // Load full session data
      const fullSession = await api.getSession(session.session_id);

      this.sessionId = fullSession.session_id;
      this.filename = fullSession.filename;
      this.conversation = fullSession.conversation || [];
      this.flags = fullSession.flags || [];

      // For now, we need the user to re-upload the PDF file
      // In a full implementation, we'd fetch it from the backend
      // Show a message that the PDF needs to be re-uploaded
      this.pdfUrl = '';
      this.loading = false;

      // Display a notification or prompt to re-upload
      alert('Session loaded! Please re-upload the PDF file to view it. Your conversation history has been restored.');

    } catch (err) {
      console.error('Failed to load session:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to load session';
      }
      this.loading = false;
    }
  }

  handleUploadNewFromPicker() {
    this.showSessionPicker = false;
    // Trigger file input click
    const fileInput = this.shadowRoot?.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  }

  private renderEmptyState() {
    return html`
      <div class="empty-state">
        <h2>Paper Companion</h2>
        <p>
          Upload a PDF to get started, or load a previous session.
        </p>
        <div class="empty-state-actions">
          <label class="upload-btn">
            Upload PDF
            <input type="file" accept=".pdf" @change=${this.handleFileUpload} />
          </label>
          <button class="secondary-btn" @click=${this.handleShowSessionPicker}>
            Load Previous Session
          </button>
        </div>
      </div>
    `;
  }

  private renderLoadingScreen() {
    return html`
      <div class="loading-screen">
        <loading-spinner
          size="large"
          message="Analyzing paper..."
          light
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
        <left-panel
          .sessionId=${this.sessionId}
          .filename=${this.filename}
          .conversation=${this.conversation}
          .flags=${this.flags}
          .outline=${this.outline}
          .concepts=${this.concepts}
          .selectedText=${this.selectedText}
          .selectedPage=${this.selectedPage}
          @conversation-updated=${(e: CustomEvent) =>
            (this.conversation = e.detail.conversation)}
          @flags-updated=${(e: CustomEvent) => (this.flags = e.detail.flags)}
          @clear-selection=${this.handleClearSelection}
          @navigate-to-page=${this.handleNavigateToPage}
          @highlight-concept=${this.handleHighlightConcept}
        ></left-panel>
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

      <session-list
        .visible=${this.showSessionPicker}
        @session-selected=${this.handleSessionSelected}
        @close=${this.handleCloseSessionPicker}
        @upload-new=${this.handleUploadNewFromPicker}
      ></session-list>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'app-root': AppRoot;
  }
}
