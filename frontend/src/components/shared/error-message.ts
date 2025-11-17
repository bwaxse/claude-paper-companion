import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('error-message')
export class ErrorMessage extends LitElement {
  @property({ type: String }) message = 'An error occurred';
  @property({ type: Boolean }) dismissible = false;

  static styles = css`
    :host {
      display: block;
    }

    .error {
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      padding: 12px 16px;
      color: #991b1b;
      font-size: 14px;
      line-height: 1.5;
      display: flex;
      align-items: start;
      gap: 12px;
    }

    .icon {
      flex-shrink: 0;
      font-size: 18px;
    }

    .content {
      flex: 1;
    }

    .dismiss {
      background: none;
      border: none;
      color: #991b1b;
      cursor: pointer;
      font-size: 20px;
      padding: 0;
      line-height: 1;
      opacity: 0.6;
    }

    .dismiss:hover {
      opacity: 1;
    }
  `;

  private handleDismiss() {
    this.dispatchEvent(new CustomEvent('dismiss', { bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="error">
        <div class="icon">⚠️</div>
        <div class="content">${this.message}</div>
        ${this.dismissible
          ? html`<button class="dismiss" @click=${this.handleDismiss}>×</button>`
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'error-message': ErrorMessage;
  }
}
