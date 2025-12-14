import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { ConversationMessage } from '../../types/session';
import './ask-tab';
import './concepts-tab';

export type TabType = 'concepts' | 'ask';

@customElement('left-panel')
export class LeftPanel extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: String }) filename = '';
  @property({ type: String }) zoteroKey?: string;  // Zotero key if session was loaded from Zotero
  @property({ type: Array }) conversation: ConversationMessage[] = [];
  @property({ type: Array }) flags: number[] = [];
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
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .header-content {
      flex: 1;
      min-width: 0; /* Allow shrinking */
      overflow: hidden; /* Prevent overflow */
    }

    .header-title {
      margin-bottom: 8px;
    }

    .home-button {
      padding: 6px 12px;
      background: transparent;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      color: #666;
      transition: all 0.2s;
      flex-shrink: 0; /* Prevent button from shrinking */
      margin-left: 12px;
      align-self: flex-start; /* Align to top */
    }

    .home-button:hover {
      background: #f5f5f5;
      border-color: #ccc;
      color: #333;
    }

    .panel-header h1 {
      margin: 0 0 2px 0;
      font-size: 18px;
      color: #333;
    }

    .panel-header .tagline {
      margin: 0;
      font-size: 11px;
      color: #999;
      font-style: italic;
      font-weight: 300;
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

  private handleHomeClick() {
    this.dispatchEvent(
      new CustomEvent('home-click', {
        bubbles: true,
        composed: true
      })
    );
  }

  render() {
    return html`
      <div class="panel-header">
        <div class="header-content">
          <div class="header-title">
            <h1>Scholia</h1>
            <p class="tagline">Critical reading, captured.</p>
          </div>
          ${this.filename
            ? html`<p class="filename" title="${this.filename}">${this.filename}</p>`
            : ''}
        </div>
        ${this.sessionId
          ? html`<button class="home-button" @click=${this.handleHomeClick}>Home</button>`
          : ''}
      </div>

      ${this.sessionId
        ? html`
            <div class="tabs">
              <button
                class="tab-button ${this.activeTab === 'concepts' ? 'active' : ''}"
                @click=${() => this.handleTabClick('concepts')}
              >
                Insights
              </button>
              <button
                class="tab-button ${this.activeTab === 'ask' ? 'active' : ''}"
                @click=${() => this.handleTabClick('ask')}
              >
                Discuss
              </button>
            </div>
          `
        : ''}

      <div class="tab-content">
        <concepts-tab
          class="${this.activeTab === 'concepts' ? 'active' : ''}"
          .sessionId=${this.sessionId}
          .zoteroKey=${this.zoteroKey}
        ></concepts-tab>

        <ask-tab
          class="${this.activeTab === 'ask' ? 'active' : ''}"
          .sessionId=${this.sessionId}
          .zoteroKey=${this.zoteroKey}
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
