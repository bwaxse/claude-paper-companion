import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { ConversationMessage } from '../../types/session';

@customElement('conversation-item')
export class ConversationItem extends LitElement {
  @property({ type: Object }) message!: ConversationMessage;
  @property({ type: Boolean }) flagged = false;

  @state() private expanded = false;

  static styles = css`
    :host {
      display: block;
      margin-bottom: 16px;
    }

    .message {
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      padding: 12px;
    }

    .user-message {
      border-left: 3px solid #1a73e8;
    }

    .assistant-message {
      border-left: 3px solid #7c4dff;
    }

    .highlighted-text {
      background: #fff3cd;
      padding: 8px;
      border-radius: 4px;
      margin-bottom: 8px;
      font-size: 13px;
      color: #856404;
      border-left: 3px solid #f4b400;
    }

    .highlighted-text::before {
      content: '"';
    }

    .highlighted-text::after {
      content: '"';
    }

    .user-query {
      color: #1a73e8;
      font-weight: 500;
      font-size: 14px;
      line-height: 1.5;
    }

    .user-query-preview {
      cursor: pointer;
    }

    .user-query-first-line {
      display: block;
    }

    .user-query-rest {
      display: block;
      color: #6b7280;
      opacity: 0.6;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      font-weight: 400;
    }

    .user-query-full {
      white-space: pre-wrap;
    }

    .expand-indicator {
      font-size: 12px;
      color: #6b7280;
      margin-top: 4px;
      cursor: pointer;
    }

    .expand-indicator:hover {
      color: #1a73e8;
    }

    .assistant-response {
      color: #333;
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-wrap: break-word;
    }

    .message-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #f0f0f0;
      font-size: 12px;
      color: #999;
    }

    .meta {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .model-badge {
      background: #ede9fe;
      color: #7c4dff;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
    }

    .timestamp {
      color: #999;
    }

    .page-indicator {
      color: #666;
      font-size: 12px;
    }

    .actions {
      display: flex;
      gap: 8px;
    }

    .flag-btn,
    .copy-btn {
      background: none;
      border: none;
      cursor: pointer;
      font-size: 16px;
      padding: 4px;
      opacity: 0.6;
      transition: opacity 0.2s;
    }

    .flag-btn:hover,
    .copy-btn:hover {
      opacity: 1;
    }

    .flag-btn.flagged {
      opacity: 1;
      color: #f4b400;
    }

    .copy-btn {
      font-size: 14px;
    }
  `;

  private handleFlag() {
    this.dispatchEvent(
      new CustomEvent('flag-toggle', {
        detail: { exchangeId: this.message.id },
        bubbles: true,
        composed: true
      })
    );
  }

  private async handleCopy() {
    if (this.message.role === 'assistant') {
      try {
        await navigator.clipboard.writeText(this.message.content);
        // Could show a toast notification here
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    }
  }

  private formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  }

  private getModelName(model?: string): string {
    if (!model) return '';
    if (model.includes('sonnet')) return 'Sonnet';
    if (model.includes('haiku')) return 'Haiku';
    if (model.includes('opus')) return 'Opus';
    return 'Claude';
  }

  private toggleExpand() {
    this.expanded = !this.expanded;
  }

  private renderUserQuery() {
    const content = this.message.content;
    const lines = content.split('\n');
    const hasMultipleLines = lines.length > 1 || content.length > 100;

    if (!hasMultipleLines || this.expanded) {
      return html`
        <div class="user-query user-query-full" @click=${this.toggleExpand}>
          ${content}
        </div>
        ${hasMultipleLines
          ? html`
              <div class="expand-indicator" @click=${this.toggleExpand}>
                Click to collapse
              </div>
            `
          : ''}
      `;
    }

    // Show preview with first line and faded second line
    const firstLine = lines[0];
    const rest = lines.length > 1 ? lines[1] : content.substring(firstLine.length);

    return html`
      <div class="user-query user-query-preview" @click=${this.toggleExpand}>
        <span class="user-query-first-line">${firstLine}</span>
        ${rest
          ? html`<span class="user-query-rest">${rest}</span>`
          : ''}
      </div>
      <div class="expand-indicator" @click=${this.toggleExpand}>
        Click to expand
      </div>
    `;
  }

  render() {
    const isUser = this.message.role === 'user';

    return html`
      <div class="message ${isUser ? 'user-message' : 'assistant-message'}">
        ${this.message.highlighted_text
          ? html`
              <div class="highlighted-text">
                ${this.message.highlighted_text}
              </div>
            `
          : ''}

        ${isUser
          ? html`
              ${this.renderUserQuery()}
              ${this.message.page
                ? html`
                    <div class="page-indicator">Page ${this.message.page}</div>
                  `
                : ''}
            `
          : html`
              <div class="assistant-response">${this.message.content}</div>
            `}

        ${!isUser
          ? html`
              <div class="message-footer">
                <div class="meta">
                  ${this.message.model
                    ? html`
                        <span class="model-badge">
                          ${this.getModelName(this.message.model)}
                        </span>
                      `
                    : ''}
                  <span class="timestamp">
                    ${this.formatTimestamp(this.message.timestamp)}
                  </span>
                </div>
                <div class="actions">
                  <button
                    class="flag-btn ${this.flagged ? 'flagged' : ''}"
                    @click=${this.handleFlag}
                    title="${this.flagged ? 'Unflag' : 'Flag important'}"
                  >
                    ${this.flagged ? '★' : '☆'}
                  </button>
                  <button
                    class="copy-btn"
                    @click=${this.handleCopy}
                    title="Copy response"
                  >
                    📋
                  </button>
                </div>
              </div>
            `
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'conversation-item': ConversationItem;
  }
}
