import { LitElement, html, css } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';
import { api, ApiError } from '../../services/api';
import type { ConversationMessage } from '../../types/session';
import type { QueryRequest } from '../../types/query';
import '../shared/conversation-item';
import '../shared/query-input';
import '../shared/loading-spinner';
import '../shared/error-message';

@customElement('ask-tab')
export class AskTab extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: Array }) conversation: ConversationMessage[] = [];
  @property({ type: Array }) flags: number[] = [];
  @property({ type: String }) selectedText = '';
  @property({ type: Number }) selectedPage?: number;

  @state() private loading = false;
  @state() private error = '';

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
      margin-bottom: 12px;
      font-size: 15px;
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
  `;

  async handleSubmitQuery(e: CustomEvent<QueryRequest>) {
    if (!this.sessionId) return;

    this.loading = true;
    this.error = '';

    try {
      const response = await api.query(this.sessionId, e.detail);

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
      const assistantMessage: ConversationMessage = {
        id: response.exchange_id + 1,
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

  async handleFlagToggle(e: CustomEvent<{ exchangeId: number }>) {
    if (!this.sessionId) return;

    const { exchangeId } = e.detail;
    const isFlagged = this.flags.includes(exchangeId);

    try {
      if (isFlagged) {
        await api.unflag(this.sessionId, exchangeId);
        this.flags = this.flags.filter((id) => id !== exchangeId);
      } else {
        await api.toggleFlag(this.sessionId, exchangeId);
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
    } catch (err) {
      console.error('Flag toggle error:', err);
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
    let title = 'Critical Review: 5-Bullet Summary';
    let content = initialAnalysis.content;

    // Check if content starts with a markdown header
    const headerMatch = content.match(/^#\s*(.+?)[\r\n]/);
    if (headerMatch) {
      title = headerMatch[1].trim();
      content = content.substring(headerMatch[0].length).trim();
    }

    // Parse content to make section headers bold
    const formattedContent = this.formatAnalysisContent(content);

    return html`
      <div class="initial-analysis">
        <div class="initial-analysis-title">${title}</div>
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
        <div class="empty-state">
          <h3>No paper loaded</h3>
          <p>Upload a PDF to start asking questions.</p>
        </div>
      `;
    }

    return html`
      <div class="conversation-container">
        ${this.renderInitialAnalysis()} ${this.renderConversation()}
        ${this.loading
          ? html`
              <div class="loading-overlay">
                <loading-spinner message="Thinking..."></loading-spinner>
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

      <query-input
        .selectedText=${this.selectedText}
        .selectedPage=${this.selectedPage}
        .loading=${this.loading}
        @submit-query=${this.handleSubmitQuery}
        @clear-selection=${this.handleClearSelection}
      ></query-input>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ask-tab': AskTab;
  }
}
