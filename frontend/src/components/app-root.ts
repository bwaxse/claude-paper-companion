import { LitElement, html, css } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';
import { api, ApiError } from '../services/api';
import { sessionStorage } from '../services/session-storage';
import type { ConversationMessage, Session } from '../types/session';
import type { TextSelection } from '../types/pdf';
import './pdf-viewer/pdf-viewer';
import './left-panel/left-panel';
import './session-picker/session-list';
import './zotero-picker/zotero-picker';
import './shared/loading-spinner';
import './shared/error-message';
import type { PdfViewer } from './pdf-viewer/pdf-viewer';
import type { LeftPanel } from './left-panel/left-panel';
import type { ZoteroItem } from '../types/session';

@customElement('app-root')
export class AppRoot extends LitElement {
  @state() private sessionId = '';
  @state() private filename = '';
  @state() private zoteroKey?: string;  // Zotero key if session was loaded from Zotero
  @state() private pdfUrl = '';
  @state() private conversation: ConversationMessage[] = [];
  @state() private flags: number[] = [];
  @state() private selectedText = '';
  @state() private selectedPage?: number;
  @state() private loading = false;
  @state() private error = '';
  @state() private showSessionPicker = false;
  @state() private showZoteroPicker = false;

  @query('pdf-viewer') private pdfViewer?: PdfViewer;
  @query('left-panel') private leftPanel?: LeftPanel;

  private boundKeydownHandler = this.handleKeydown.bind(this);

  connectedCallback() {
    super.connectedCallback();
    document.addEventListener('keydown', this.boundKeydownHandler);

    // Load saved zoom preference
    const savedZoom = sessionStorage.getPdfZoom();
    if (this.pdfViewer && savedZoom) {
      this.pdfViewer.scale = savedZoom;
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener('keydown', this.boundKeydownHandler);
  }

  private handleKeydown(e: KeyboardEvent) {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modifier = isMac ? e.metaKey : e.ctrlKey;

    // Don't trigger shortcuts when typing in input fields
    const target = e.target as HTMLElement;
    const isTyping = target.tagName === 'INPUT' ||
                     target.tagName === 'TEXTAREA' ||
                     target.isContentEditable;

    // Cmd/Ctrl + K - Focus query input
    if (modifier && e.key === 'k') {
      e.preventDefault();
      this.focusQueryInput();
      return;
    }

    // Cmd/Ctrl + Shift + F - Flag last exchange
    if (modifier && e.shiftKey && e.key === 'F') {
      e.preventDefault();
      this.flagLastExchange();
      return;
    }

    // Escape - Close modals or clear text selection
    if (e.key === 'Escape') {
      if (this.showSessionPicker) {
        this.showSessionPicker = false;
      } else if (this.showZoteroPicker) {
        this.showZoteroPicker = false;
      } else if (this.selectedText) {
        this.handleClearSelection();
      }
      return;
    }

    // Tab switching with number keys (only when not typing)
    if (!isTyping && !modifier && !e.shiftKey && !e.altKey) {
      if (e.key === '1') {
        e.preventDefault();
        this.switchTab('concepts');
        return;
      }
      if (e.key === '2') {
        e.preventDefault();
        this.switchTab('ask');
        return;
      }
    }
  }

  private focusQueryInput() {
    // Find the query input in the shadow DOM
    const leftPanel = this.shadowRoot?.querySelector('left-panel');
    if (leftPanel) {
      const askTab = leftPanel.shadowRoot?.querySelector('ask-tab');
      if (askTab) {
        const queryInput = askTab.shadowRoot?.querySelector('query-input');
        if (queryInput) {
          const textarea = queryInput.shadowRoot?.querySelector('textarea');
          if (textarea) {
            textarea.focus();
          }
        }
      }
    }
  }

  private async flagLastExchange() {
    if (!this.sessionId || this.conversation.length < 2) return;

    // Find the last assistant message
    const lastAssistantMsg = [...this.conversation]
      .reverse()
      .find(msg => msg.role === 'assistant');

    if (lastAssistantMsg && lastAssistantMsg.id > 1) {
      const isFlagged = this.flags.includes(lastAssistantMsg.id);

      try {
        if (isFlagged) {
          await api.unflag(this.sessionId, lastAssistantMsg.id);
          this.flags = this.flags.filter(id => id !== lastAssistantMsg.id);
        } else {
          await api.toggleFlag(this.sessionId, lastAssistantMsg.id);
          this.flags = [...this.flags, lastAssistantMsg.id];
        }
      } catch (err) {
        console.error('Failed to toggle flag:', err);
      }
    }
  }

  private switchTab(tab: 'concepts' | 'ask') {
    if (this.leftPanel) {
      // Access the activeTab property directly
      (this.leftPanel as any).activeTab = tab;
      sessionStorage.setActiveTab(tab);
    }
  }

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
      margin: 0 0 8px 0;
      font-size: 32px;
    }

    .empty-state .tagline {
      margin: 0 0 24px 0;
      color: rgba(255, 255, 255, 0.7);
      font-size: 14px;
      font-style: italic;
      font-weight: 300;
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

    .recent-sessions {
      width: 100%;
      max-width: 500px;
      margin: 0 0 32px 0;
    }

    .recent-sessions h3 {
      font-size: 16px;
      margin: 0 0 16px 0;
      color: rgba(255, 255, 255, 0.9);
      text-align: left;
    }

    .session-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      margin-bottom: 8px;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;
      text-align: left;
    }

    .session-item:hover {
      background: rgba(255, 255, 255, 0.15);
      border-color: rgba(255, 255, 255, 0.3);
    }

    .session-item:last-child {
      margin-bottom: 0;
    }

    .session-info {
      flex: 1;
      min-width: 0;
    }

    .session-filename {
      font-weight: 500;
      font-size: 14px;
      color: white;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .session-meta {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
    }

    .see-all-link {
      color: rgba(255, 255, 255, 0.8);
      font-size: 14px;
      text-decoration: none;
      cursor: pointer;
      display: inline-block;
      margin-top: 12px;
    }

    .see-all-link:hover {
      color: white;
      text-decoration: underline;
    }

    .no-sessions {
      color: rgba(255, 255, 255, 0.7);
      font-size: 14px;
      margin-bottom: 24px;
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
      this.zoteroKey = undefined;  // File upload, no Zotero key
      this.pdfUrl = URL.createObjectURL(file);

      // Save to session storage for "pick up where left off"
      sessionStorage.setLastSessionId(session.session_id);

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
      this.zoteroKey = fullSession.zotero_key;  // Restore Zotero key if available
      this.flags = fullSession.flags || [];

      // Build conversation with initial analysis as first messages
      const initialMessages: ConversationMessage[] = [];
      if (fullSession.initial_analysis) {
        initialMessages.push({
          id: 0,
          role: 'user',
          content: 'Initial analysis',
          timestamp: fullSession.created_at
        });
        initialMessages.push({
          id: 1,
          role: 'assistant',
          content: fullSession.initial_analysis,
          timestamp: fullSession.created_at
        });
      }

      // Convert conversation messages from API format to frontend format
      const conversationMessages: ConversationMessage[] = (fullSession.conversation || []).map((msg: any) => ({
        id: msg.exchange_id,
        role: msg.role,
        content: msg.content,
        model: msg.model,
        highlighted_text: msg.highlighted_text,
        page: msg.page_number,
        timestamp: msg.timestamp
      }));

      this.conversation = [...initialMessages, ...conversationMessages];

      // Save to session storage
      sessionStorage.setLastSessionId(fullSession.session_id);

      // Load PDF from backend
      this.pdfUrl = `/sessions/${fullSession.session_id}/pdf`;
      this.loading = false;

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

  handleShowZoteroPicker() {
    this.showZoteroPicker = true;
  }

  handleCloseZoteroPicker() {
    this.showZoteroPicker = false;
  }

  handleHomeClick() {
    // Clear current session and return to empty state
    this.sessionId = '';
    this.filename = '';
    this.zoteroKey = undefined;
    this.pdfUrl = '';
    this.conversation = [];
    this.flags = [];
    this.selectedText = '';
    this.selectedPage = undefined;
    this.error = '';
  }

  async handleZoteroPaperSelected(e: CustomEvent<{ session: Session; paper: ZoteroItem }>) {
    const { session, paper } = e.detail;
    this.showZoteroPicker = false;
    this.loading = true;
    this.error = '';

    try {
      // Load full session data
      const fullSession = await api.getSession(session.session_id);

      this.sessionId = fullSession.session_id;
      this.filename = fullSession.filename;
      this.zoteroKey = paper.key;  // Set Zotero key from selected paper
      this.flags = fullSession.flags || [];

      // Build conversation with initial analysis as first messages
      const initialMessages: ConversationMessage[] = [];
      if (fullSession.initial_analysis) {
        initialMessages.push({
          id: 0,
          role: 'user',
          content: 'Initial analysis',
          timestamp: fullSession.created_at
        });
        initialMessages.push({
          id: 1,
          role: 'assistant',
          content: fullSession.initial_analysis,
          timestamp: fullSession.created_at
        });
      }

      // Convert conversation messages from API format to frontend format
      const conversationMessages: ConversationMessage[] = (fullSession.conversation || []).map((msg: any) => ({
        id: msg.exchange_id,
        role: msg.role,
        content: msg.content,
        model: msg.model,
        highlighted_text: msg.highlighted_text,
        page: msg.page_number,
        timestamp: msg.timestamp
      }));

      this.conversation = [...initialMessages, ...conversationMessages];

      // Save to session storage
      sessionStorage.setLastSessionId(fullSession.session_id);

      // Load PDF from backend
      this.pdfUrl = `/sessions/${fullSession.session_id}/pdf`;
      this.loading = false;

    } catch (err) {
      console.error('Failed to load Zotero session:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to load paper from Zotero';
      }
      this.loading = false;
    }
  }

  private renderEmptyState() {
    return html`
      <div class="empty-state">
        <h2>Scholia</h2>
        <p class="tagline">Critical reading, captured.</p>
        <p>
          Upload a PDF to get started or load from Zotero.
        </p>

        <div class="empty-state-actions">
          <label class="upload-btn">
            Upload PDF
            <input type="file" accept=".pdf" @change=${this.handleFileUpload} />
          </label>
          <button class="secondary-btn" @click=${this.handleShowZoteroPicker}>
            Load from Zotero
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
          .zoteroKey=${this.zoteroKey}
          .conversation=${this.conversation}
          .flags=${this.flags}
          .selectedText=${this.selectedText}
          .selectedPage=${this.selectedPage}
          @conversation-updated=${(e: CustomEvent) =>
            (this.conversation = e.detail.conversation)}
          @flags-updated=${(e: CustomEvent) => (this.flags = e.detail.flags)}
          @clear-selection=${this.handleClearSelection}
          @navigate-to-page=${this.handleNavigateToPage}
          @home-click=${this.handleHomeClick}
          @session-selected=${this.handleSessionSelected}
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

      <zotero-picker
        .visible=${this.showZoteroPicker}
        @zotero-paper-selected=${this.handleZoteroPaperSelected}
        @close=${this.handleCloseZoteroPicker}
      ></zotero-picker>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'app-root': AppRoot;
  }
}
