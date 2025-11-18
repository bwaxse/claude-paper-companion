import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { Concept } from '../../types/pdf';
import { api } from '../../services/api';
import '../shared/loading-spinner';

@customElement('concepts-tab')
export class ConceptsTab extends LitElement {
  @property({ type: Array }) concepts: Concept[] = [];
  @property({ type: String }) sessionId = '';

  @state() private loading = false;
  @state() private error = '';
  @state() private localConcepts: Concept[] = [];
  @state() private searchQuery = '';
  @state() private selectedConcept?: Concept;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f8f9fa;
      overflow: hidden;
    }

    .search-container {
      padding: 12px 16px;
      background: white;
      border-bottom: 1px solid #e0e0e0;
      flex-shrink: 0;
    }

    .search-input {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 13px;
      outline: none;
      box-sizing: border-box;
    }

    .search-input:focus {
      border-color: #1a73e8;
      box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.1);
    }

    .concepts-container {
      flex: 1;
      overflow-y: auto;
      padding: 12px 16px;
    }

    .concept-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      margin-bottom: 8px;
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .concept-item:hover {
      border-color: #1a73e8;
      background: #f8fbff;
    }

    .concept-item.selected {
      border-color: #1a73e8;
      background: #e8f0fe;
    }

    .concept-info {
      flex: 1;
      min-width: 0;
    }

    .concept-term {
      font-weight: 500;
      font-size: 13px;
      color: #333;
      margin-bottom: 4px;
    }

    .concept-meta {
      font-size: 11px;
      color: #666;
    }

    .concept-frequency {
      background: #f0f0f0;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      color: #555;
      font-weight: 500;
      flex-shrink: 0;
      margin-left: 12px;
    }

    .pages-list {
      margin-top: 8px;
      padding: 8px;
      background: #f5f5f5;
      border-radius: 4px;
    }

    .pages-title {
      font-size: 11px;
      color: #666;
      margin-bottom: 6px;
    }

    .page-links {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }

    .page-link {
      padding: 2px 6px;
      background: white;
      border: 1px solid #ddd;
      border-radius: 3px;
      font-size: 11px;
      color: #1a73e8;
      cursor: pointer;
      transition: all 0.15s;
    }

    .page-link:hover {
      background: #e8f0fe;
      border-color: #1a73e8;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px;
      text-align: center;
      color: #666;
      height: 100%;
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

    .loading-container {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px;
    }

    .error-message {
      padding: 16px;
      margin: 16px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      color: #dc2626;
      font-size: 13px;
    }

    .no-results {
      text-align: center;
      padding: 24px;
      color: #666;
      font-size: 13px;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    if (this.sessionId && this.concepts.length === 0) {
      this.loadConcepts();
    }
  }

  updated(changedProperties: Map<string, unknown>) {
    if (changedProperties.has('concepts') && this.concepts.length > 0) {
      this.localConcepts = this.concepts;
    }
    if (changedProperties.has('sessionId') && this.sessionId && this.localConcepts.length === 0) {
      this.loadConcepts();
    }
  }

  private async loadConcepts() {
    if (!this.sessionId) return;

    this.loading = true;
    this.error = '';

    try {
      const concepts = await api.getConcepts(this.sessionId);
      this.localConcepts = concepts;
    } catch (err) {
      console.error('Failed to load concepts:', err);
      this.error = 'Failed to load key concepts';
    } finally {
      this.loading = false;
    }
  }

  private handleSearchInput(e: Event) {
    const input = e.target as HTMLInputElement;
    this.searchQuery = input.value.toLowerCase();
  }

  private handleConceptClick(concept: Concept) {
    if (this.selectedConcept?.term === concept.term) {
      this.selectedConcept = undefined;
    } else {
      this.selectedConcept = concept;
      this.dispatchEvent(
        new CustomEvent('highlight-concept', {
          detail: { concept },
          bubbles: true,
          composed: true
        })
      );
    }
  }

  private handlePageClick(page: number, e: Event) {
    e.stopPropagation();
    this.dispatchEvent(
      new CustomEvent('navigate-to-page', {
        detail: { page },
        bubbles: true,
        composed: true
      })
    );
  }

  private getFilteredConcepts(): Concept[] {
    const concepts = this.localConcepts.length > 0 ? this.localConcepts : this.concepts;

    if (!this.searchQuery) {
      return concepts;
    }

    return concepts.filter((concept) =>
      concept.term.toLowerCase().includes(this.searchQuery)
    );
  }

  private renderConceptItem(concept: Concept) {
    const isSelected = this.selectedConcept?.term === concept.term;

    return html`
      <div
        class="concept-item ${isSelected ? 'selected' : ''}"
        @click=${() => this.handleConceptClick(concept)}
      >
        <div class="concept-info">
          <div class="concept-term">${concept.term}</div>
          <div class="concept-meta">
            ${concept.pages.length} ${concept.pages.length === 1 ? 'page' : 'pages'}
          </div>
          ${isSelected && concept.pages.length > 0
            ? html`
                <div class="pages-list">
                  <div class="pages-title">Found on pages:</div>
                  <div class="page-links">
                    ${concept.pages.map(
                      (page) => html`
                        <button
                          class="page-link"
                          @click=${(e: Event) => this.handlePageClick(page, e)}
                        >
                          ${page}
                        </button>
                      `
                    )}
                  </div>
                </div>
              `
            : ''}
        </div>
        <span class="concept-frequency">${concept.frequency}x</span>
      </div>
    `;
  }

  render() {
    if (!this.sessionId) {
      return html`
        <div class="empty-state">
          <h3>No paper loaded</h3>
          <p>Upload a PDF to view key concepts.</p>
        </div>
      `;
    }

    if (this.loading) {
      return html`
        <div class="loading-container">
          <loading-spinner message="Extracting concepts..."></loading-spinner>
        </div>
      `;
    }

    if (this.error) {
      return html`
        <div class="error-message">${this.error}</div>
      `;
    }

    const allConcepts = this.localConcepts.length > 0 ? this.localConcepts : this.concepts;

    if (allConcepts.length === 0) {
      return html`
        <div class="empty-state">
          <h3>No concepts extracted</h3>
          <p>Key concepts couldn't be extracted from this document.</p>
        </div>
      `;
    }

    const filteredConcepts = this.getFilteredConcepts();

    return html`
      <div class="search-container">
        <input
          type="text"
          class="search-input"
          placeholder="Search concepts..."
          .value=${this.searchQuery}
          @input=${this.handleSearchInput}
        />
      </div>

      <div class="concepts-container">
        ${filteredConcepts.length === 0
          ? html`<div class="no-results">No concepts match your search</div>`
          : filteredConcepts.map((concept) => this.renderConceptItem(concept))}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'concepts-tab': ConceptsTab;
  }
}
