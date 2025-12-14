import { LitElement, html, css } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';
import { api, ApiError } from '../../services/api';
import type { ConversationMessage, Session } from '../../types/session';
import type { QueryRequest } from '../../types/query';
import type { ZoteroItem } from '../../types/session';
import '../shared/conversation-item';
import '../shared/query-input';
import '../shared/loading-spinner';
import '../shared/error-message';
import '../zotero-picker/zotero-picker';

@customElement('ask-tab')
export class AskTab extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: Array }) conversation: ConversationMessage[] = [];
  @property({ type: Array }) flags: number[] = [];
  @property({ type: String }) selectedText = '';
  @property({ type: Number }) selectedPage?: number;
  @property({ type: String }) zoteroKey?: string;  // Zotero key if session was loaded from Zotero

  @state() private loading = false;
  @state() private error = '';
  @state() private showSupplementPicker = false;
  @state() private loadingSupplements = false;
  @state() private supplementAttachments: ZoteroItem[] = [];
  @state() private supplementCount: number | null = null; // null = not loaded yet, 0 = none available, >0 = count
  @state() private selectedModel: 'sonnet' | 'haiku' = 'sonnet'; // Default to Sonnet
  @state() private allSessions: Session[] = [];
  @state() private loadingSessions = false;

  @query('.conversation-container') private conversationContainer!: HTMLElement;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f8f9fa;
    }

    .conversation-container {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
      text-align: center;
      color: #666;
    }

    .empty-state h3 {
      margin: 0 0 8px 0;
      font-size: 16px;
      color: #333;
    }

    .empty-state p {
      margin: 0;
      font-size: 14px;
      line-height: 1.5;
    }

    .sessions-list-container {
      padding: 16px;
      height: 100%;
      overflow-y: auto;
    }

    .sessions-header {
      margin: 0 0 16px 0;
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }

    .sessions-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .session-item {
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      padding: 12px;
      cursor: pointer;
      transition: all 0.2s;
    }

    .session-item:hover {
      border-color: #1a73e8;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .session-filename {
      font-size: 14px;
      font-weight: 500;
      color: #333;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .session-date {
      font-size: 12px;
      color: #666;
    }

    .no-sessions {
      text-align: center;
      padding: 40px 20px;
      color: #666;
    }

    .no-sessions p {
      margin: 4px 0;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
    }

    .loading-container p {
      margin-top: 12px;
      color: #666;
      font-size: 13px;
    }

    .initial-analysis {
      background: white;
      border: 1px solid #9e9e9e;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }

    .initial-analysis-title {
      font-weight: 700;
      color: #333;
      margin-bottom: 4px;
      font-size: 15px;
    }

    .initial-analysis-subtitle {
      font-weight: 600;
      color: #666;
      margin-bottom: 12px;
      font-size: 13px;
    }

    .initial-analysis-content {
      color: #444;
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
    }

    .initial-analysis-content .section-header {
      font-weight: 700;
      color: #333;
    }

    .error-container {
      padding: 16px;
    }

    .loading-overlay {
      display: flex;
      justify-content: center;
      padding: 20px;
    }

    query-input {
      flex-shrink: 0;
    }

    .model-selector {
      padding: 12px 16px;
      background: white;
      border-top: 1px solid #e0e0e0;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }

    .model-label {
      font-size: 12px;
      color: #666;
      font-weight: 500;
    }

    .model-toggle {
      display: flex;
      background: #f0f0f0;
      border-radius: 6px;
      padding: 2px;
      gap: 2px;
    }

    .model-option {
      padding: 6px 12px;
      font-size: 12px;
      border: none;
      background: transparent;
      color: #666;
      cursor: pointer;
      border-radius: 4px;
      transition: all 0.2s;
      font-weight: 500;
    }

    .model-option:hover {
      background: #e0e0e0;
    }

    .model-option.active {
      background: white;
      color: #1a73e8;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .model-info {
      font-size: 11px;
      color: #999;
      margin-left: auto;
    }
  `;

  private handleModelChange(model: 'sonnet' | 'haiku') {
    this.selectedModel = model;
  }

  async handleSubmitQuery(e: CustomEvent<QueryRequest>) {
    if (!this.sessionId) return;

    this.loading = true;
    this.error = '';

    try {
      // Add model parameter to the query request
      const queryWithModel = {
        ...e.detail,
        model: this.selectedModel
      };
      const response = await api.query(this.sessionId, queryWithModel);

      // Add user message to conversation
      const userMessage: ConversationMessage = {
        id: response.exchange_id,
        role: 'user',
        content: e.detail.query,
        highlighted_text: e.detail.highlighted_text,
        page: e.detail.page,
        timestamp: new Date().toISOString()
      };

      // Add assistant response to conversation
      // Note: Both user and assistant share the same exchange_id
      const assistantMessage: ConversationMessage = {
        id: response.exchange_id,
        role: 'assistant',
        content: response.response,
        model: response.model_used,
        timestamp: new Date().toISOString()
      };

      this.conversation = [...this.conversation, userMessage, assistantMessage];

      // Notify parent of conversation update
      this.dispatchEvent(
        new CustomEvent('conversation-updated', {
          detail: { conversation: this.conversation },
          bubbles: true,
          composed: true
        })
      );

      // Scroll to bottom after update
      await this.updateComplete;
      this.scrollToBottom();
    } catch (err) {
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to send query. Please try again.';
      }
      console.error('Query error:', err);
    } finally {
      this.loading = false;
    }
  }

  updated(changedProperties: Map<string, unknown>) {
    // Check for supplements when zoteroKey is set
    if (changedProperties.has('zoteroKey') && this.zoteroKey) {
      this.checkSupplementsAvailable();
    }

    // Load sessions when no session is active
    if (changedProperties.has('sessionId') && !this.sessionId && this.allSessions.length === 0) {
      this.loadAllSessions();
    }
  }

  private async loadAllSessions() {
    this.loadingSessions = true;
    try {
      // Load all sessions (limit 100 for now)
      this.allSessions = await api.listSessions(100, 0);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      this.loadingSessions = false;
    }
  }

  private handleSessionClick(session: Session) {
    this.dispatchEvent(
      new CustomEvent('session-selected', {
        detail: { session },
        bubbles: true,
        composed: true
      })
    );
  }

  private formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
  }

  private async checkSupplementsAvailable() {
    if (!this.zoteroKey) {
      this.supplementCount = null;
      return;
    }

    try {
      const attachments = await api.getPaperAttachments(this.zoteroKey);
      this.supplementCount = attachments.length;
      // Pre-cache the attachments so we don't need to fetch again when opening picker
      if (attachments.length > 0) {
        this.supplementAttachments = attachments;
      }
    } catch (err) {
      // If we can't fetch, just don't show count
      this.supplementCount = null;
      console.error('Failed to check supplements:', err);
    }
  }

  private async handleShowSupplementPicker() {
    if (!this.zoteroKey) {
      // If no Zotero key, we could implement file upload here
      this.error = 'Upload supplement feature coming soon';
      return;
    }

    // If we don't have attachments cached or count is 0, try to fetch
    if (!this.supplementAttachments.length || this.supplementCount === 0) {
      this.loadingSupplements = true;
      try {
        const attachments = await api.getPaperAttachments(this.zoteroKey);
        if (attachments.length === 0) {
          this.error = 'No supplemental files found for this paper';
          this.loadingSupplements = false;
          return;
        }
        this.supplementAttachments = attachments;
        this.supplementCount = attachments.length;
      } catch (err) {
        if (err instanceof ApiError) {
          this.error = `Failed to load supplements: ${err.message}`;
        } else {
          this.error = 'Failed to load supplements';
        }
        this.loadingSupplements = false;
        return;
      } finally {
        this.loadingSupplements = false;
      }
    }

    // Show picker with cached attachments
    this.showSupplementPicker = true;
  }

  private handleCloseSupplementPicker() {
    this.showSupplementPicker = false;
  }

  private async handleSupplementUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file || !this.sessionId || !this.zoteroKey) {
      return;
    }

    this.loadingSupplements = true;
    this.error = '';

    try {
      // Upload supplement to backend (which will add it to Zotero)
      await api.uploadSupplement(this.sessionId, this.zoteroKey, file);

      // Refresh the supplement count and list
      await this.checkSupplementsAvailable();

      // Show success message
      const successMessage: ConversationMessage = {
        id: this.conversation.length,
        role: 'user',
        content: `📎 **Supplement Uploaded**: "${file.name}" has been added to your Zotero library and is now available for reference.`,
        timestamp: new Date().toISOString()
      };

      this.conversation = [...this.conversation, successMessage];

      // Notify parent
      this.dispatchEvent(
        new CustomEvent('conversation-updated', {
          detail: { conversation: this.conversation },
          bubbles: true,
          composed: true
        })
      );
    } catch (err) {
      if (err instanceof ApiError) {
        this.error = `Failed to upload supplement: ${err.message}`;
      } else {
        this.error = 'Failed to upload supplement. Please try again.';
      }
      console.error('Upload error:', err);
    } finally {
      this.loadingSupplements = false;
      // Clear the input so the same file can be uploaded again if needed
      input.value = '';
    }
  }

  private async handleSupplementSelected(e: CustomEvent<{ session: any; paper: ZoteroItem }>) {
    if (!this.sessionId) return;

    const { paper } = e.detail;
    this.showSupplementPicker = false;
    this.loadingSupplements = true;
    this.error = '';

    try {
      // Load supplement text from backend
      const supplement = await api.loadSupplement(this.sessionId, paper.key);

      // Add system message about loaded supplement
      const supplementMessage: ConversationMessage = {
        id: this.conversation.length,
        role: 'user',
        content: `📎 **Supplement Loaded**: "${supplement.title}" (${supplement.authors || 'Unknown'}, ${supplement.year || 'N/A'})\n\nYou can now reference this supplement in your questions.`,
        timestamp: new Date().toISOString()
      };

      this.conversation = [...this.conversation, supplementMessage];

      // Add the supplement text as a system message that Claude can see
      const supplementContextMessage: ConversationMessage = {
        id: this.conversation.length + 1,
        role: 'assistant',
        content: `[Supplement loaded: "${supplement.title}"\n\n${supplement.supplement_text.substring(0, 3000)}${supplement.supplement_text.length > 3000 ? '...' : ''}]`,
        timestamp: new Date().toISOString()
      };

      this.conversation = [...this.conversation, supplementContextMessage];

      // Notify parent of conversation update
      this.dispatchEvent(
        new CustomEvent('conversation-updated', {
          detail: { conversation: this.conversation },
          bubbles: true,
          composed: true
        })
      );

      // Scroll to bottom after update
      await this.updateComplete;
      this.scrollToBottom();
    } catch (err) {
      if (err instanceof ApiError) {
        this.error = `Failed to load supplement: ${err.message}`;
      } else {
        this.error = 'Failed to load supplement. Please try again.';
      }
      console.error('Supplement loading error:', err);
    } finally {
      this.loadingSupplements = false;
    }
  }

  async handleFlagToggle(e: CustomEvent<{ exchangeId: number }>) {
    if (!this.sessionId) return;

    const { exchangeId } = e.detail;
    const isFlagged = this.flags.includes(exchangeId);

    // Update UI immediately (optimistic update)
    if (isFlagged) {
      this.flags = this.flags.filter((id) => id !== exchangeId);
    } else {
      this.flags = [...this.flags, exchangeId];
    }

    // Notify parent of flags update
    this.dispatchEvent(
      new CustomEvent('flags-updated', {
        detail: { flags: this.flags },
        bubbles: true,
        composed: true
      })
    );

    this.requestUpdate();

    // Then sync with backend (don't block UI on this)
    try {
      if (isFlagged) {
        await api.unflag(this.sessionId, exchangeId);
      } else {
        await api.toggleFlag(this.sessionId, exchangeId);
      }
    } catch (err) {
      console.error('Flag toggle error:', err);
      // Note: We keep the optimistic UI update even if API fails
    }
  }

  handleClearSelection() {
    this.dispatchEvent(
      new CustomEvent('clear-selection', {
        bubbles: true,
        composed: true
      })
    );
  }

  private scrollToBottom() {
    if (this.conversationContainer) {
      this.conversationContainer.scrollTop = this.conversationContainer.scrollHeight;
    }
  }

  private renderConversation() {
    // Skip the initial analysis (first two messages: user prompt + assistant analysis)
    const conversationMessages = this.conversation.slice(2);

    if (conversationMessages.length === 0) {
      return html`
        <div class="empty-state">
          <h3>No questions yet</h3>
          <p>
            Type a question below, or select text in the PDF to ask about specific passages.
          </p>
        </div>
      `;
    }

    // Group messages into pairs (user question + assistant response)
    const exchanges: Array<{ user: ConversationMessage; assistant: ConversationMessage }> = [];
    for (let i = 0; i < conversationMessages.length; i += 2) {
      const userMsg = conversationMessages[i];
      const assistantMsg = conversationMessages[i + 1];
      if (userMsg && assistantMsg && userMsg.role === 'user' && assistantMsg.role === 'assistant') {
        exchanges.push({ user: userMsg, assistant: assistantMsg });
      }
    }

    return exchanges.map(
      (exchange) => html`
        <conversation-item
          .userMessage=${exchange.user}
          .assistantMessage=${exchange.assistant}
          .flagged=${this.flags.includes(exchange.assistant.id)}
          @flag-toggle=${this.handleFlagToggle}
        ></conversation-item>
      `
    );
  }

  private renderInitialAnalysis() {
    const initialAnalysis = this.conversation.find(
      (msg) => msg.id === 1 && msg.role === 'assistant'
    );

    if (!initialAnalysis) return '';

    // Parse the content to extract title and body
    let paperTitle = '';
    let content = initialAnalysis.content;

    // Check for "TITLE: ..." format at start
    const titleMatch = content.match(/^TITLE:\s*(.+?)(?:\n|$)/i);
    if (titleMatch) {
      paperTitle = titleMatch[1].trim();
      content = content.substring(titleMatch[0].length).trim();
    } else {
      // Fallback: check for markdown header format
      const headerMatch = content.match(/^#\s*(.+?)[\r\n]/);
      if (headerMatch) {
        const fullTitle = headerMatch[1].trim();
        // Extract paper title from formats like "Review Summary: Paper Title"
        const subtitleMatch = fullTitle.match(/^(?:Review Summary|Critical Review|5-Bullet Summary):\s*(.+)$/i);
        if (subtitleMatch) {
          paperTitle = subtitleMatch[1].trim();
        } else {
          paperTitle = fullTitle;
        }
        content = content.substring(headerMatch[0].length).trim();
      }
    }

    // Parse content to make section headers bold
    const formattedContent = this.formatAnalysisContent(content);

    return html`
      <div class="initial-analysis">
        ${paperTitle ? html`<div class="initial-analysis-title">${paperTitle}</div>` : ''}
        <div class="initial-analysis-subtitle">Review Summary</div>
        <div class="initial-analysis-content">${formattedContent}</div>
      </div>
    `;
  }

  private formatAnalysisContent(content: string) {
    // Split content by lines and process each line
    const lines = content.split('\n');
    const result: any[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Check for section headers like "**Core Innovation**:" or "Core Innovation:" or "• **Core Innovation**:"
      const boldMatch = line.match(/^(•?\s*)\*\*([^*]+)\*\*(:.*)?$/);
      const plainHeaderMatch = line.match(/^(•?\s*)([A-Z][A-Za-z\s]+)(:)(.*)$/);

      if (boldMatch) {
        // Handle **Bold Header**: format
        const [, prefix, headerText, rest] = boldMatch;
        result.push(html`${prefix}<span class="section-header">${headerText}</span>${rest || ''}`);
      } else if (plainHeaderMatch && plainHeaderMatch[2].length < 30) {
        // Handle plain "Header:" format (only if reasonably short)
        const [, prefix, headerText, colon, rest] = plainHeaderMatch;
        result.push(html`${prefix}<span class="section-header">${headerText}</span>${colon}${rest}`);
      } else {
        result.push(line);
      }

      // Add newline between lines (except after last line)
      if (i < lines.length - 1) {
        result.push('\n');
      }
    }

    return result;
  }

  render() {
    if (!this.sessionId) {
      return html`
        <div class="sessions-list-container">
          <h3 class="sessions-header">Recent Papers</h3>
          ${this.loadingSessions ? html`
            <div class="loading-container">
              <loading-spinner></loading-spinner>
              <p>Loading sessions...</p>
            </div>
          ` : this.allSessions.length > 0 ? html`
            <div class="sessions-list">
              ${this.allSessions.map(session => html`
                <div class="session-item" @click=${() => this.handleSessionClick(session)}>
                  <div class="session-filename" title="${session.filename}">
                    ${session.filename}
                  </div>
                  <div class="session-date">${this.formatDate(session.created_at)}</div>
                </div>
              `)}
            </div>
          ` : html`
            <div class="no-sessions">
              <p>No previous sessions yet</p>
              <p style="font-size: 13px; color: #999;">Upload a PDF to get started</p>
            </div>
          `}
        </div>
      `;
    }

    return html`
      <div class="conversation-container">
        ${this.renderInitialAnalysis()} ${this.renderConversation()}
        ${this.loading || this.loadingSupplements
          ? html`
              <div class="loading-overlay">
                <loading-spinner message="${this.loadingSupplements ? 'Loading supplement...' : 'Thinking...'}"></loading-spinner>
              </div>
            `
          : ''}
        ${this.error
          ? html`
              <div class="error-container">
                <error-message
                  .message=${this.error}
                  dismissible
                  @dismiss=${() => (this.error = '')}
                ></error-message>
              </div>
            `
          : ''}
      </div>

      <div style="padding: 8px 16px; border-top: 1px solid #e0e0e0; background: white;">
        ${this.zoteroKey && this.supplementCount === 0
          ? html`
              <div style="text-align: center; margin-bottom: 8px; font-size: 12px; color: #666;">
                No Supplemental PDFs Available
              </div>
              <input
                type="file"
                accept="application/pdf"
                style="display: none;"
                id="supplement-upload"
                @change=${this.handleSupplementUpload}
              />
              <button
                style="
                  width: 100%;
                  padding: 10px;
                  background: #4CAF50;
                  border: 1px solid #45a049;
                  border-radius: 6px;
                  font-size: 13px;
                  cursor: pointer;
                  color: white;
                  font-weight: 500;
                "
                @click=${() => {
                  const input = this.shadowRoot?.getElementById('supplement-upload') as HTMLInputElement;
                  input?.click();
                }}
                ?disabled=${!this.sessionId || this.loading || this.loadingSupplements}
              >
                📎 Upload Supplemental PDF
              </button>
            `
          : html`
              <button
                style="
                  width: 100%;
                  padding: 10px;
                  background: #f0f0f0;
                  border: 1px solid #ddd;
                  border-radius: 6px;
                  font-size: 13px;
                  cursor: pointer;
                  color: #333;
                "
                @click=${this.handleShowSupplementPicker}
                ?disabled=${!this.sessionId || this.loading || this.loadingSupplements}
              >
                ${this.zoteroKey
                  ? this.supplementCount === null
                    ? '📎 Checking supplements...'
                    : `📎 Add Supplement (${this.supplementCount})`
                  : '📎 Upload Supplement'}
              </button>
            `}
      </div>

      <div class="model-selector">
        <span class="model-label">Model:</span>
        <div class="model-toggle">
          <button
            class="model-option ${this.selectedModel === 'sonnet' ? 'active' : ''}"
            @click=${() => this.handleModelChange('sonnet')}
          >
            Sonnet
          </button>
          <button
            class="model-option ${this.selectedModel === 'haiku' ? 'active' : ''}"
            @click=${() => this.handleModelChange('haiku')}
          >
            Haiku
          </button>
        </div>
        <span class="model-info">
          ${this.selectedModel === 'sonnet' ? 'Deep analysis • $3/MTok' : 'Fast & cheap • $0.25/MTok'}
        </span>
      </div>

      <query-input
        .selectedText=${this.selectedText}
        .selectedPage=${this.selectedPage}
        .loading=${this.loading}
        @submit-query=${this.handleSubmitQuery}
        @clear-selection=${this.handleClearSelection}
      ></query-input>

      <zotero-picker
        .visible=${this.showSupplementPicker}
        .preFilteredItems=${this.supplementAttachments}
        .mode=${'supplements'}
        @zotero-paper-selected=${this.handleSupplementSelected}
        @close=${this.handleCloseSupplementPicker}
      ></zotero-picker>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ask-tab': AskTab;
  }
}
