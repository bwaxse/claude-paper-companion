import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { api, ApiError } from '../../services/api';
import type { Session } from '../../types/session';
import '../shared/loading-spinner';

@customElement('session-list')
export class SessionList extends LitElement {
  @property({ type: Boolean }) visible = false;

  @state() private sessions: Session[] = [];
  @state() private loading = true;
  @state() private error = '';
  @state() private searchQuery = '';
  @state() private deletingId?: string;

  static styles = css`
    :host {
      display: block;
    }

    .session-picker {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .picker-content {
      background: white;
      border-radius: 12px;
      width: 90%;
      max-width: 600px;
      max-height: 80vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }

    .picker-header {
      padding: 20px 24px;
      border-bottom: 1px solid #e0e0e0;
      flex-shrink: 0;
    }

    .picker-header h2 {
      margin: 0 0 16px 0;
      font-size: 20px;
      color: #333;
    }

    .search-input {
      width: 100%;
      padding: 10px 14px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 14px;
      outline: none;
      box-sizing: border-box;
    }

    .search-input:focus {
      border-color: #1a73e8;
      box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.1);
    }

    .picker-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .session-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      margin-bottom: 8px;
      background: #f8f9fa;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .session-item:hover {
      background: #e8f0fe;
      border-color: #1a73e8;
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
      color: #333;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .session-meta {
      font-size: 12px;
      color: #666;
    }

    .session-actions {
      flex-shrink: 0;
      margin-left: 12px;
    }

    .delete-btn {
      padding: 6px 10px;
      background: transparent;
      border: 1px solid #dc2626;
      border-radius: 4px;
      color: #dc2626;
      cursor: pointer;
      font-size: 12px;
      transition: all 0.15s;
    }

    .delete-btn:hover {
      background: #fef2f2;
    }

    .delete-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .picker-footer {
      padding: 16px 24px;
      border-top: 1px solid #e0e0e0;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      flex-shrink: 0;
    }

    .btn {
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
    }

    .btn-secondary {
      background: white;
      border: 1px solid #ddd;
      color: #333;
    }

    .btn-secondary:hover {
      background: #f5f5f5;
    }

    .btn-primary {
      background: #1a73e8;
      border: 1px solid #1a73e8;
      color: white;
    }

    .btn-primary:hover {
      background: #1557b0;
    }

    .empty-state {
      text-align: center;
      padding: 40px 20px;
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
    }

    .loading-container {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 40px;
    }

    .error-message {
      padding: 16px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      color: #dc2626;
      font-size: 13px;
      margin-bottom: 16px;
    }

    .no-results {
      text-align: center;
      padding: 24px;
      color: #666;
      font-size: 14px;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    this.loadSessions();
  }

  updated(changedProperties: Map<string, unknown>) {
    // Reload sessions when the picker becomes visible
    if (changedProperties.has('visible') && this.visible) {
      this.loadSessions();
    }
  }

  async loadSessions() {
    this.loading = true;
    this.error = '';

    try {
      this.sessions = await api.listSessions();
    } catch (err) {
      console.error('Failed to load sessions:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to load sessions';
      }
    } finally {
      this.loading = false;
    }
  }

  private handleSearchInput(e: Event) {
    const input = e.target as HTMLInputElement;
    this.searchQuery = input.value.toLowerCase();
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

  private async handleDeleteClick(session: Session, e: Event) {
    e.stopPropagation();

    if (!confirm(`Delete session for "${session.filename}"? This cannot be undone.`)) {
      return;
    }

    this.deletingId = session.session_id;

    try {
      await api.deleteSession(session.session_id);
      this.sessions = this.sessions.filter((s) => s.session_id !== session.session_id);
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('Failed to delete session');
    } finally {
      this.deletingId = undefined;
    }
  }

  private handleClose() {
    this.dispatchEvent(
      new CustomEvent('close', {
        bubbles: true,
        composed: true
      })
    );
  }

  private handleUploadNew() {
    this.dispatchEvent(
      new CustomEvent('upload-new', {
        bubbles: true,
        composed: true
      })
    );
  }

  private getFilteredSessions(): Session[] {
    if (!this.searchQuery) {
      return this.sessions;
    }

    return this.sessions.filter((session) =>
      session.filename.toLowerCase().includes(this.searchQuery)
    );
  }

  private formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  private renderSessionItem(session: Session) {
    const isDeleting = this.deletingId === session.session_id;

    return html`
      <div class="session-item" @click=${() => this.handleSessionClick(session)}>
        <div class="session-info">
          <div class="session-filename" title="${session.filename}">
            ${session.filename}
          </div>
          <div class="session-meta">${this.formatDate(session.created_at)}</div>
        </div>
        <div class="session-actions">
          <button
            class="delete-btn"
            @click=${(e: Event) => this.handleDeleteClick(session, e)}
            ?disabled=${isDeleting}
          >
            ${isDeleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    `;
  }

  render() {
    if (!this.visible) {
      return null;
    }

    const filteredSessions = this.getFilteredSessions();

    return html`
      <div class="session-picker" @click=${(e: Event) => {
        if (e.target === e.currentTarget) this.handleClose();
      }}>
        <div class="picker-content">
          <div class="picker-header">
            <h2>Your Papers</h2>
            <input
              type="text"
              class="search-input"
              placeholder="Search papers..."
              .value=${this.searchQuery}
              @input=${this.handleSearchInput}
            />
          </div>

          <div class="picker-body">
            ${this.error
              ? html`<div class="error-message">${this.error}</div>`
              : ''}

            ${this.loading
              ? html`
                  <div class="loading-container">
                    <loading-spinner message="Loading sessions..."></loading-spinner>
                  </div>
                `
              : this.sessions.length === 0
              ? html`
                  <div class="empty-state">
                    <h3>No papers yet</h3>
                    <p>Upload a PDF to get started.</p>
                  </div>
                `
              : filteredSessions.length === 0
              ? html`<div class="no-results">No papers match your search</div>`
              : filteredSessions.map((session) => this.renderSessionItem(session))}
          </div>

          <div class="picker-footer">
            <button class="btn btn-secondary" @click=${this.handleClose}>
              Cancel
            </button>
            <button class="btn btn-primary" @click=${this.handleUploadNew}>
              Upload New PDF
            </button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'session-list': SessionList;
  }
}
