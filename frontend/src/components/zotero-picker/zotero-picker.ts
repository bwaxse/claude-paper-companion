import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { api, ApiError } from '../../services/api';
import type { ZoteroItem } from '../../types/session';
import '../shared/loading-spinner';

@customElement('zotero-picker')
export class ZoteroPicker extends LitElement {
  @property({ type: Boolean }) visible = false;
  @property({ type: Array }) preFilteredItems?: ZoteroItem[]; // Pass pre-filtered items (e.g., attachments)
  @property({ type: String }) mode: 'full' | 'supplements' = 'full'; // Mode: 'full' for all papers, 'supplements' for attachments only

  @state() private items: ZoteroItem[] = [];
  @state() private loading = true;
  @state() private error = '';
  @state() private searchQuery = '';
  @state() private activeTab: 'recent' | 'search' = 'recent';
  @state() private searching = false;
  @state() private selectingKey?: string;

  static styles = css`
    :host {
      display: block;
    }

    .zotero-picker {
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
      max-width: 650px;
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

    .tabs {
      display: flex;
      gap: 4px;
      margin-bottom: 16px;
    }

    .tab {
      padding: 8px 16px;
      border: none;
      background: transparent;
      font-size: 14px;
      font-weight: 500;
      color: #666;
      cursor: pointer;
      border-radius: 6px;
      transition: all 0.15s;
    }

    .tab:hover {
      background: #f0f0f0;
    }

    .tab.active {
      background: #e8f0fe;
      color: #1a73e8;
    }

    .search-container {
      display: flex;
      gap: 8px;
    }

    .search-input {
      flex: 1;
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

    .search-btn {
      padding: 10px 16px;
      background: #1a73e8;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .search-btn:hover {
      background: #1557b0;
    }

    .search-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    .picker-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .paper-item {
      padding: 14px 16px;
      margin-bottom: 8px;
      background: #f8f9fa;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .paper-item:hover {
      background: #e8f0fe;
      border-color: #1a73e8;
    }

    .paper-item.selecting {
      opacity: 0.7;
      cursor: wait;
    }

    .paper-item:last-child {
      margin-bottom: 0;
    }

    .paper-title {
      font-weight: 500;
      font-size: 14px;
      color: #333;
      margin-bottom: 6px;
      line-height: 1.4;
    }

    .paper-authors {
      font-size: 13px;
      color: #555;
      margin-bottom: 4px;
    }

    .paper-meta {
      font-size: 12px;
      color: #666;
      display: flex;
      gap: 12px;
    }

    .paper-meta span {
      display: flex;
      align-items: center;
      gap: 4px;
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

    .search-hint {
      text-align: center;
      padding: 40px 20px;
      color: #666;
      font-size: 14px;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
  }

  updated(changedProperties: Map<string, unknown>) {
    // If pre-filtered items provided, use those instead of loading
    if (changedProperties.has('preFilteredItems') && this.preFilteredItems) {
      this.items = this.preFilteredItems;
      this.loading = false;
      return;
    }

    // Load recent papers when the picker becomes visible (only in 'full' mode)
    if (changedProperties.has('visible') && this.visible && this.mode === 'full') {
      this.loadRecentPapers();
    }
  }

  private async loadRecentPapers() {
    this.loading = true;
    this.error = '';
    this.activeTab = 'recent';

    try {
      this.items = await api.getRecentPapers(20);
    } catch (err) {
      console.error('Failed to load recent papers:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to load recent papers from Zotero';
      }
    } finally {
      this.loading = false;
    }
  }

  private async handleSearch() {
    if (!this.searchQuery.trim()) return;

    this.searching = true;
    this.error = '';
    this.activeTab = 'search';

    try {
      this.items = await api.searchZotero(this.searchQuery.trim(), 20);
    } catch (err) {
      console.error('Failed to search Zotero:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to search Zotero';
      }
    } finally {
      this.searching = false;
    }
  }

  private handleSearchInput(e: Event) {
    const input = e.target as HTMLInputElement;
    this.searchQuery = input.value;
  }

  private handleSearchKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      this.handleSearch();
    }
  }

  private handleTabClick(tab: 'recent' | 'search') {
    this.activeTab = tab;
    if (tab === 'recent') {
      this.loadRecentPapers();
    }
  }

  private async handlePaperClick(paper: ZoteroItem) {
    if (this.selectingKey) return;

    this.selectingKey = paper.key;

    try {
      // Create session from Zotero paper
      const session = await api.createSessionFromZotero(paper.key);

      this.dispatchEvent(
        new CustomEvent('zotero-paper-selected', {
          detail: { session, paper },
          bubbles: true,
          composed: true
        })
      );
    } catch (err) {
      console.error('Failed to create session from Zotero:', err);
      if (err instanceof ApiError) {
        this.error = err.message;
      } else {
        this.error = 'Failed to load paper from Zotero';
      }
    } finally {
      this.selectingKey = undefined;
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

  private renderPaperItem(paper: ZoteroItem) {
    const isSelecting = this.selectingKey === paper.key;

    // Skip attachment items without titles - they're usually PDFs of other items
    if (paper.item_type === 'attachment' && !paper.title) {
      return null;
    }

    // Skip pure attachment items - show the parent paper instead
    if (paper.item_type === 'attachment' && paper.title) {
      // Filter to only show actual papers, not PDF attachments
      return null;
    }

    return html`
      <div
        class="paper-item ${isSelecting ? 'selecting' : ''}"
        @click=${() => this.handlePaperClick(paper)}
      >
        <div class="paper-title">${paper.title || 'Untitled'}</div>
        ${paper.authors ? html`<div class="paper-authors">${paper.authors}</div>` : ''}
        <div class="paper-meta">
          ${paper.year ? html`<span>${paper.year}</span>` : ''}
          ${paper.publication ? html`<span>${paper.publication}</span>` : ''}
          ${paper.item_type ? html`<span>${this.formatItemType(paper.item_type)}</span>` : ''}
        </div>
        ${isSelecting ? html`<div style="font-size: 12px; color: #1a73e8; margin-top: 8px;">Loading paper...</div>` : ''}
      </div>
    `;
  }

  private formatItemType(itemType: string): string {
    const typeMap: Record<string, string> = {
      journalArticle: 'Journal Article',
      conferencePaper: 'Conference Paper',
      book: 'Book',
      bookSection: 'Book Chapter',
      thesis: 'Thesis',
      report: 'Report',
      preprint: 'Preprint'
    };
    return typeMap[itemType] || itemType;
  }

  render() {
    if (!this.visible) {
      return null;
    }

    return html`
      <div class="zotero-picker" @click=${(e: Event) => {
        if (e.target === e.currentTarget) this.handleClose();
      }}>
        <div class="picker-content">
          <div class="picker-header">
            <h2>${this.mode === 'supplements' ? 'Select Supplement' : 'Load from Zotero'}</h2>

            ${this.mode === 'full' ? html`
              <div class="tabs">
                <button
                  class="tab ${this.activeTab === 'recent' ? 'active' : ''}"
                  @click=${() => this.handleTabClick('recent')}
                >
                  Recent
                </button>
                <button
                  class="tab ${this.activeTab === 'search' ? 'active' : ''}"
                  @click=${() => this.handleTabClick('search')}
                >
                  Search
                </button>
              </div>

              <div class="search-container">
                <input
                  type="text"
                  class="search-input"
                  placeholder="Search by title, author, or DOI..."
                  .value=${this.searchQuery}
                  @input=${this.handleSearchInput}
                  @keydown=${this.handleSearchKeydown}
                />
                <button
                  class="search-btn"
                  @click=${this.handleSearch}
                  ?disabled=${this.searching || !this.searchQuery.trim()}
                >
                  ${this.searching ? 'Searching...' : 'Search'}
                </button>
              </div>
            ` : ''}
          </div>

          <div class="picker-body">
            ${this.error
              ? html`<div class="error-message">${this.error}</div>`
              : ''}

            ${this.loading || this.searching
              ? html`
                  <div class="loading-container">
                    <loading-spinner message="${this.loading ? 'Loading recent papers...' : 'Searching...'}"></loading-spinner>
                  </div>
                `
              : this.activeTab === 'search' && !this.searchQuery.trim()
              ? html`
                  <div class="search-hint">
                    Enter a search term to find papers in your Zotero library
                  </div>
                `
              : this.items.length === 0
              ? html`
                  <div class="empty-state">
                    <h3>
                      ${this.mode === 'supplements'
                        ? 'No Supplemental PDFs Found'
                        : this.activeTab === 'recent'
                        ? 'No papers in Zotero'
                        : 'No results found'}
                    </h3>
                    <p>
                      ${this.mode === 'supplements'
                        ? 'This paper has no additional PDF attachments in Zotero.'
                        : this.activeTab === 'recent'
                        ? 'Add papers to your Zotero library to see them here.'
                        : 'Try a different search term.'}
                    </p>
                  </div>
                `
              : this.items.map((paper) => this.renderPaperItem(paper))}
          </div>

          <div class="picker-footer">
            <button class="btn btn-secondary" @click=${this.handleClose}>
              Cancel
            </button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'zotero-picker': ZoteroPicker;
  }
}
