import { LitElement, html, css } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';

@customElement('query-input')
export class QueryInput extends LitElement {
  @property({ type: String }) selectedText = '';
  @property({ type: Number }) selectedPage?: number;
  @property({ type: Boolean }) disabled = false;
  @property({ type: Boolean }) loading = false;

  @state() private queryText = '';

  @query('textarea') private textarea!: HTMLTextAreaElement;

  static styles = css`
    :host {
      display: block;
      background: white;
      border-top: 1px solid #e0e0e0;
      padding: 16px;
    }

    .selected-text-preview {
      background: #fff3cd;
      border: 1px solid #f4b400;
      border-radius: 4px;
      padding: 8px 12px;
      margin-bottom: 12px;
      font-size: 13px;
      color: #856404;
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 8px;
    }

    .preview-content {
      flex: 1;
      line-height: 1.4;
    }

    .preview-label {
      font-weight: 500;
      margin-bottom: 4px;
    }

    .preview-text {
      font-style: italic;
      max-height: 60px;
      overflow-y: auto;
    }

    .clear-selection {
      background: none;
      border: none;
      color: #856404;
      cursor: pointer;
      font-size: 18px;
      padding: 0;
      opacity: 0.6;
      line-height: 1;
    }

    .clear-selection:hover {
      opacity: 1;
    }

    .input-area {
      position: relative;
    }

    textarea {
      width: 100%;
      min-height: 80px;
      max-height: 200px;
      padding: 12px;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
      font-family: inherit;
      resize: vertical;
      box-sizing: border-box;
    }

    textarea:focus {
      outline: none;
      border-color: #1a73e8;
      box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.1);
    }

    textarea:disabled {
      background: #f5f5f5;
      cursor: not-allowed;
    }

    .footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
    }

    .hint {
      font-size: 12px;
      color: #999;
    }

    .actions {
      display: flex;
      gap: 8px;
    }

    .submit-btn {
      padding: 8px 20px;
      background: #1a73e8;
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .submit-btn:hover:not(:disabled) {
      background: #1557b0;
    }

    .submit-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    .model-toggle {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #666;
    }

    .model-toggle input {
      cursor: pointer;
    }

    .char-count {
      font-size: 12px;
      color: #999;
    }

    .char-count.warning {
      color: #f4b400;
    }
  `;

  private handleClearSelection() {
    this.dispatchEvent(
      new CustomEvent('clear-selection', {
        bubbles: true,
        composed: true
      })
    );
  }

  private handleSubmit() {
    const query = this.queryText.trim();
    if (!query) return;

    this.dispatchEvent(
      new CustomEvent('submit-query', {
        detail: {
          query,
          highlighted_text: this.selectedText || undefined,
          page: this.selectedPage
        },
        bubbles: true,
        composed: true
      })
    );

    this.queryText = '';
    if (this.textarea) {
      this.textarea.style.height = 'auto';
    }
  }

  private handleKeyDown(e: KeyboardEvent) {
    // Submit on Cmd+Enter or Ctrl+Enter
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      this.handleSubmit();
    }
  }

  private handleInput(e: Event) {
    const target = e.target as HTMLTextAreaElement;
    this.queryText = target.value;

    // Auto-resize textarea
    target.style.height = 'auto';
    target.style.height = target.scrollHeight + 'px';
  }

  render() {
    const charCount = this.queryText.length;
    const showWarning = charCount > 500;

    return html`
      ${this.selectedText
        ? html`
            <div class="selected-text-preview">
              <div class="preview-content">
                <div class="preview-label">
                  Selected text${this.selectedPage ? ` (Page ${this.selectedPage})` : ''}:
                </div>
                <div class="preview-text">"${this.selectedText}"</div>
              </div>
              <button
                class="clear-selection"
                @click=${this.handleClearSelection}
                title="Clear selection"
              >
                ×
              </button>
            </div>
          `
        : ''}

      <div class="input-area">
        <textarea
          placeholder="Ask a question about the paper..."
          .value=${this.queryText}
          @input=${this.handleInput}
          @keydown=${this.handleKeyDown}
          ?disabled=${this.disabled || this.loading}
        ></textarea>
      </div>

      <div class="footer">
        <div class="hint">
          ${this.loading ? 'Thinking...' : 'Cmd+Enter to send'}
          ${charCount > 0
            ? html`
                <span class="char-count ${showWarning ? 'warning' : ''}">
                  · ${charCount} chars
                </span>
              `
            : ''}
        </div>
        <div class="actions">
          <button
            class="submit-btn"
            @click=${this.handleSubmit}
            ?disabled=${this.disabled || this.loading || !this.queryText.trim()}
          >
            ${this.loading ? 'Thinking...' : 'Ask'}
          </button>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'query-input': QueryInput;
  }
}
