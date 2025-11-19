import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { api } from '../../services/api';
import '../shared/loading-spinner';

interface Insights {
  strengths?: string[];
  weaknesses?: string[];
  methodological_notes?: string[];
  theoretical_contributions?: string[];
  empirical_findings?: string[];
  questions_raised?: string[];
  applications?: string[];
  key_quotes?: Array<{
    user: string;
    assistant: string;
    theme?: string;
    note?: string;
  }>;
  metadata?: {
    total_exchanges?: number;
    flagged_count?: number;
  };
}

@customElement('concepts-tab')
export class ConceptsTab extends LitElement {
  @property({ type: String }) sessionId = '';

  @state() private loading = false;
  @state() private error = '';
  @state() private insights: Insights | null = null;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f8f9fa;
      overflow: hidden;
    }

    .insights-container {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .section {
      margin-bottom: 20px;
    }

    .section-title {
      font-weight: 600;
      font-size: 14px;
      color: #333;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .section-title .icon {
      font-size: 16px;
    }

    .insight-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .insight-item {
      padding: 8px 12px;
      margin-bottom: 6px;
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      font-size: 13px;
      line-height: 1.5;
      color: #333;
    }

    .quote-item {
      padding: 12px;
      margin-bottom: 8px;
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      border-left: 3px solid #1a73e8;
    }

    .quote-question {
      font-size: 12px;
      color: #666;
      margin-bottom: 6px;
    }

    .quote-answer {
      font-size: 13px;
      color: #333;
      line-height: 1.5;
    }

    .quote-note {
      font-size: 11px;
      color: #1a73e8;
      margin-top: 6px;
      font-style: italic;
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
      margin: 0 0 20px 0;
      font-size: 14px;
      line-height: 1.5;
    }

    .extract-btn {
      padding: 12px 24px;
      background: #1a73e8;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .extract-btn:hover {
      background: #1557b0;
    }

    .extract-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px;
      height: 100%;
    }

    .loading-text {
      margin-top: 12px;
      font-size: 13px;
      color: #666;
    }

    .error-message {
      padding: 16px;
      margin: 16px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      color: #dc2626;
      font-size: 13px;
      text-align: center;
    }

    .retry-btn {
      margin-top: 12px;
      padding: 8px 16px;
      background: #dc2626;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 13px;
    }

    .retry-btn:hover {
      background: #b91c1c;
    }

    .metadata {
      font-size: 11px;
      color: #666;
      padding: 8px 12px;
      background: #f0f0f0;
      border-radius: 4px;
      margin-bottom: 16px;
    }
    if (changedProperties.has('sessionId') && this.sessionId) {
      // Clear error and reload when sessionId changes
      this.error = '';
      if (this.localConcepts.length === 0) {
        this.loadConcepts();
      }
    }
  }

  private async extractInsights() {
    if (!this.sessionId) return;

    this.loading = true;
    this.error = '';

    try {
      const insights = await api.getConcepts(this.sessionId);
      this.insights = insights;
    } catch (err) {
      console.error('Failed to extract insights:', err);
      this.error = 'Failed to extract insights. Please try again.';
    } finally {
      this.loading = false;
    }
  }

  private renderSection(title: string, icon: string, items: string[] | undefined) {
    if (!items || items.length === 0) return '';

    return html`
      <div class="section">
        <div class="section-title">
          <span class="icon">${icon}</span>
          ${title}
        </div>
        <ul class="insight-list">
          ${items.map(item => html`<li class="insight-item">${item}</li>`)}
        </ul>
      </div>
    `;
  }

  private renderQuotes() {
    if (!this.insights?.key_quotes || this.insights.key_quotes.length === 0) return '';

    return html`
      <div class="section">
        <div class="section-title">
          <span class="icon">💬</span>
          Key Exchanges
        </div>
        ${this.insights.key_quotes.map(quote => html`
          <div class="quote-item">
            <div class="quote-question"><strong>Q:</strong> ${quote.user}</div>
            <div class="quote-answer">${quote.assistant}</div>
            ${quote.note ? html`<div class="quote-note">${quote.note}</div>` : ''}
          </div>
        `)}
      </div>
    `;
  }

  render() {
    if (!this.sessionId) {
      return html`
        <div class="empty-state">
          <h3>No paper loaded</h3>
          <p>Upload a PDF to extract insights.</p>
        </div>
      `;
    }

    if (this.loading) {
      return html`
        <div class="loading-container">
          <loading-spinner></loading-spinner>
          <div class="loading-text">Analyzing conversation and extracting insights...</div>
        </div>
      `;
    }

    if (this.error) {
      return html`
        <div class="error-message">
          ${this.error}
          <br>
          <button class="retry-btn" @click=${this.extractInsights}>Try Again</button>
        </div>
      `;
    }

    if (!this.insights) {
      return html`
        <div class="empty-state">
          <h3>Extract Insights</h3>
          <p>
            Analyze your conversation to extract key insights,
            strengths, weaknesses, and important exchanges.
          </p>
          <button class="extract-btn" @click=${this.extractInsights}>
            Extract Insights
          </button>
        </div>
      `;
    }

    // Check if there are any insights to show
    const hasInsights =
      (this.insights.strengths && this.insights.strengths.length > 0) ||
      (this.insights.weaknesses && this.insights.weaknesses.length > 0) ||
      (this.insights.methodological_notes && this.insights.methodological_notes.length > 0) ||
      (this.insights.theoretical_contributions && this.insights.theoretical_contributions.length > 0) ||
      (this.insights.empirical_findings && this.insights.empirical_findings.length > 0) ||
      (this.insights.questions_raised && this.insights.questions_raised.length > 0) ||
      (this.insights.applications && this.insights.applications.length > 0) ||
      (this.insights.key_quotes && this.insights.key_quotes.length > 0);

    if (!hasInsights) {
      return html`
        <div class="empty-state">
          <h3>No insights extracted</h3>
          <p>
            Ask some questions about the paper first, then extract insights
            from your conversation. The more you discuss, the richer the insights.
          </p>
          <button class="extract-btn" @click=${this.extractInsights}>
            Try Again
          </button>
        </div>
      `;
    }

    // Render extracted insights
    return html`
      <div class="insights-container">
        ${this.insights.metadata ? html`
          <div class="metadata">
            Based on ${this.insights.metadata.total_exchanges || 0} exchanges
            ${this.insights.metadata.flagged_count ? ` • ${this.insights.metadata.flagged_count} flagged` : ''}
          </div>
        ` : ''}

        ${this.renderSection('Strengths', '💪', this.insights.strengths)}
        ${this.renderSection('Weaknesses', '⚠️', this.insights.weaknesses)}
        ${this.renderSection('Methodological Notes', '🔬', this.insights.methodological_notes)}
        ${this.renderSection('Theoretical Contributions', '💡', this.insights.theoretical_contributions)}
        ${this.renderSection('Key Findings', '📊', this.insights.empirical_findings)}
        ${this.renderSection('Questions Raised', '❓', this.insights.questions_raised)}
        ${this.renderSection('Applications', '🚀', this.insights.applications)}
        ${this.renderQuotes()}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'concepts-tab': ConceptsTab;
  }
}
