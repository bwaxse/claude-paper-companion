import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { ConversationMessage } from '../../types/session';
import type { OutlineItem, Concept } from '../../types/pdf';
import './ask-tab';
import './outline-tab';
import './concepts-tab';

export type TabType = 'outline' | 'concepts' | 'ask';

@customElement('left-panel')
export class LeftPanel extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: String }) filename = '';
  @property({ type: Array }) conversation: ConversationMessage[] = [];
  @property({ type: Array }) flags: number[] = [];
  @property({ type: Array }) outline: OutlineItem[] = [];
  @property({ type: Array }) concepts: Concept[] = [];
  @property({ type: String }) selectedText = '';
  @property({ type: Number }) selectedPage?: number;

  @state() private activeTab: TabType = 'ask';

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f8f9fa;
    }

    .panel-header {
      padding: 16px;
      background: white;
      border-bottom: 1px solid #e0e0e0;
      flex-shrink: 0;
    }

    .panel-header h1 {
      margin: 0 0 4px 0;
      font-size: 18px;
      color: #333;
    }

    .panel-header .filename {
      margin: 0;
      font-size: 13px;
      color: #666;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .tabs {
      display: flex;
      background: white;
      border-bottom: 1px solid #e0e0e0;
      flex-shrink: 0;
    }

    .tab-button {
      flex: 1;
      padding: 12px 16px;
      border: none;
      background: transparent;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      color: #666;
      transition: all 0.2s;
      position: relative;
    }

    .tab-button:hover {
      background: #f5f5f5;
      color: #333;
    }

    .tab-button.active {
      color: #1a73e8;
    }

    .tab-button.active::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: #1a73e8;
    }

    .tab-content {
      flex: 1;
      min-height: 0;
      overflow: hidden;
    }

    .tab-content > * {
      height: 100%;
    }

    /* Hide inactive tabs */
    .tab-content > :not(.active) {
      display: none;
    }
  `;

  private handleTabClick(tab: TabType) {
    this.activeTab = tab;
    this.dispatchEvent(
      new CustomEvent('tab-change', {
        detail: { tab },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleNavigateToPage(e: CustomEvent<{ page: number }>) {
    this.dispatchEvent(
      new CustomEvent('navigate-to-page', {
        detail: e.detail,
        bubbles: true,
        composed: true
      })
    );
  }

  private handleHighlightConcept(e: CustomEvent<{ concept: Concept }>) {
    this.dispatchEvent(
      new CustomEvent('highlight-concept', {
        detail: e.detail,
        bubbles: true,
        composed: true
      })
    );
  }

  render() {
    return html`
      <div class="panel-header">
        <h1>Paper Companion</h1>
        ${this.filename
          ? html`<p class="filename" title="${this.filename}">${this.filename}</p>`
          : ''}
      </div>

      ${this.sessionId
        ? html`
            <div class="tabs">
              <button
                class="tab-button ${this.activeTab === 'outline' ? 'active' : ''}"
                @click=${() => this.handleTabClick('outline')}
              >
                Outline
              </button>
              <button
                class="tab-button ${this.activeTab === 'concepts' ? 'active' : ''}"
                @click=${() => this.handleTabClick('concepts')}
              >
                Concepts
              </button>
              <button
                class="tab-button ${this.activeTab === 'ask' ? 'active' : ''}"
                @click=${() => this.handleTabClick('ask')}
              >
                Ask
              </button>
            </div>
          `
        : ''}

      <div class="tab-content">
        <outline-tab
          class="${this.activeTab === 'outline' ? 'active' : ''}"
          .outline=${this.outline}
          .sessionId=${this.sessionId}
          @navigate-to-page=${this.handleNavigateToPage}
        ></outline-tab>

        <concepts-tab
          class="${this.activeTab === 'concepts' ? 'active' : ''}"
          .concepts=${this.concepts}
          .sessionId=${this.sessionId}
          @navigate-to-page=${this.handleNavigateToPage}
          @highlight-concept=${this.handleHighlightConcept}
        ></concepts-tab>

        <ask-tab
          class="${this.activeTab === 'ask' ? 'active' : ''}"
          .sessionId=${this.sessionId}
          .conversation=${this.conversation}
          .flags=${this.flags}
          .selectedText=${this.selectedText}
          .selectedPage=${this.selectedPage}
          @conversation-updated=${(e: CustomEvent) =>
            this.dispatchEvent(
              new CustomEvent('conversation-updated', {
                detail: e.detail,
                bubbles: true,
                composed: true
              })
            )}
          @flags-updated=${(e: CustomEvent) =>
            this.dispatchEvent(
              new CustomEvent('flags-updated', {
                detail: e.detail,
                bubbles: true,
                composed: true
              })
            )}
          @clear-selection=${() =>
            this.dispatchEvent(
              new CustomEvent('clear-selection', {
                bubbles: true,
                composed: true
              })
            )}
        ></ask-tab>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'left-panel': LeftPanel;
  }
}
