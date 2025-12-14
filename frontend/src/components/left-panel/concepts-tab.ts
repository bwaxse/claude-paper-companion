import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { api, ApiError } from '../../services/api';
import type { LinkedInPostResponse } from '../../types/query';
import type {
  NotionProject,
  NotionProjectContext
} from '../../types/notion';
import '../shared/loading-spinner';

interface Insights {
  summary?: string;
  learnings?: string[];
  assessment?: {
    strengths?: string[];
    limitations?: string[];
  };
  open_questions?: string[];
  bibliographic?: {
    title?: string;
    authors?: string;
    year?: string;
  };
  metadata?: {
    total_exchanges?: number;
    flagged_count?: number;
  };
  _cache_info?: {
    no_new_exchanges: boolean;
    cached_at?: string;
    exchange_count?: number;
  };
}

@customElement('concepts-tab')
export class ConceptsTab extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: String }) zoteroKey?: string;

  @state() private loading = false;
  @state() private error = '';
  @state() private insights: Insights | null = null;
  @state() private savingToZotero = false;
  @state() private zoteroSaveSuccess = false;
  @state() private showReextractConfirm = false;
  @state() private generatingLinkedIn = false;
  @state() private linkedInPost: LinkedInPostResponse | null = null;
  @state() private showLinkedInModal = false;
  @state() private selectedEnding: 'question' | 'declarative' | 'forward_looking' = 'question';

  // Notion export state
  @state() private showNotionModal = false;
  @state() private notionStep: 1 | 2 | 3 | 4 = 1;
  @state() private openingNotionModal = false;
  @state() private loadingNotionProjects = false;
  @state() private notionProjects: NotionProject[] = [];
  @state() private selectedProject: NotionProject | null = null;
  @state() private notionSearchQuery = '';
  @state() private projectContext: NotionProjectContext | null = null;
  @state() private loadingContext = false;
  @state() private generatingRelevance = false;
  @state() private suggestedTheme = '';
  @state() private relevanceStatement = '';
  @state() private selectedTheme = '';
  @state() private includeSessionNotes = true;
  @state() private generatingContent = false;
  @state() private notionContent = '';
  @state() private exportingToNotion = false;
  @state() private notionExportUrl = '';
  @state() private literatureReviewHeading = 'Literature Review';

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
    }

    .subsection-title {
      font-weight: 600;
      font-size: 12px;
      color: #666;
      margin-top: 8px;
      margin-bottom: 6px;
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

    .cache-warning {
      padding: 12px;
      margin-bottom: 16px;
      background: #fef3c7;
      border: 1px solid #f59e0b;
      border-radius: 6px;
      font-size: 12px;
      color: #92400e;
    }

    .cache-warning p {
      margin: 0 0 8px 0;
    }

    .cache-warning-btn {
      padding: 6px 12px;
      background: #f59e0b;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
    }

    .cache-warning-btn:hover {
      background: #d97706;
    }

    .reextract-container {
      position: sticky;
      bottom: 0;
      padding: 16px 0;
      border-top: 1px solid #e0e0e0;
      margin-top: 16px;
      display: flex;
      justify-content: center;
      gap: 12px;
      background: white;
      z-index: 10;
    }

    .reextract-btn {
      padding: 8px 16px;
      background: #f0f0f0;
      color: #333;
      border: 1px solid #ccc;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
    }

    .reextract-btn:hover {
      background: #e0e0e0;
    }

    .save-to-zotero-btn {
      padding: 8px 16px;
      background: #1a73e8;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .save-to-zotero-btn:hover {
      background: #1557b0;
    }

    .save-to-zotero-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    .save-success {
      padding: 12px;
      margin: 16px 16px 0 16px;
      background: #d4edda;
      border: 1px solid #c3e6cb;
      border-radius: 6px;
      color: #155724;
      font-size: 13px;
      text-align: center;
    }

    .confirm-overlay {
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

    .confirm-dialog {
      background: white;
      border-radius: 8px;
      padding: 24px;
      max-width: 400px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .confirm-message {
      font-size: 14px;
      color: #333;
      line-height: 1.5;
      margin-bottom: 20px;
    }

    .confirm-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }

    .confirm-btn {
      padding: 8px 16px;
      border-radius: 4px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      border: none;
      transition: background 0.2s;
    }

    .confirm-btn-cancel {
      background: #f0f0f0;
      color: #333;
    }

    .confirm-btn-cancel:hover {
      background: #e0e0e0;
    }

    .confirm-btn-primary {
      background: #1a73e8;
      color: white;
    }

    .confirm-btn-primary:hover {
      background: #1557b0;
    }

    /* LinkedIn Modal Styles */
    .linkedin-modal {
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
      padding: 20px;
    }

    .linkedin-dialog {
      background: white;
      border-radius: 8px;
      padding: 24px;
      max-width: 600px;
      width: 100%;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .linkedin-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .linkedin-title {
      font-size: 18px;
      font-weight: 600;
      color: #333;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: #666;
      padding: 0;
      line-height: 1;
    }

    .close-btn:hover {
      color: #333;
    }

    .post-preview {
      background: #f8f9fa;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 16px;
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
      color: #333;
    }

    .post-preview .paper-link {
      background: #fff3cd;
      border: 1px dashed #ffc107;
      padding: 2px 6px;
      border-radius: 3px;
      font-weight: 500;
    }

    .ending-selector {
      margin-bottom: 20px;
    }

    .ending-label {
      font-size: 13px;
      font-weight: 600;
      color: #333;
      margin-bottom: 8px;
    }

    .ending-options {
      display: flex;
      gap: 8px;
    }

    .ending-option {
      flex: 1;
      padding: 8px 12px;
      background: #f0f0f0;
      border: 2px solid transparent;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      text-align: center;
      transition: all 0.2s;
    }

    .ending-option:hover {
      background: #e0e0e0;
    }

    .ending-option.selected {
      background: #e3f2fd;
      border-color: #1a73e8;
      color: #1a73e8;
      font-weight: 500;
    }

    .linkedin-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }

    .copy-btn {
      padding: 10px 20px;
      background: #1a73e8;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .copy-btn:hover {
      background: #1557b0;
    }

    .copy-btn.copied {
      background: #059669;
    }

    .share-to-linkedin-btn {
      padding: 8px 16px;
      background: #0a66c2;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .share-to-linkedin-btn:hover {
      background: #084d92;
    }

    .share-to-linkedin-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    /* Notion Export Styles */
    .add-to-notion-btn {
      padding: 8px 16px;
      background: #000;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .add-to-notion-btn:hover {
      background: #333;
    }

    .add-to-notion-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    .notion-modal {
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
      padding: 20px;
    }

    .notion-dialog {
      background: white;
      border-radius: 8px;
      padding: 24px;
      max-width: 600px;
      width: 100%;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .notion-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .notion-title {
      font-size: 18px;
      font-weight: 600;
      color: #333;
    }

    .notion-step-indicator {
      font-size: 12px;
      color: #666;
      margin-top: 4px;
    }

    .search-input {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }

    .search-input:focus {
      border-color: #1a73e8;
    }

    .project-list {
      max-height: 300px;
      overflow-y: auto;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
    }

    .project-item {
      padding: 12px;
      border-bottom: 1px solid #e0e0e0;
      cursor: pointer;
      transition: background 0.2s;
    }

    .project-item:last-child {
      border-bottom: none;
    }

    .project-item:hover {
      background: #f8f9fa;
    }

    .project-item.selected {
      background: #e3f2fd;
      border-left: 3px solid #1a73e8;
    }

    .project-title {
      font-weight: 500;
      color: #333;
      margin-bottom: 4px;
    }

    .form-group {
      margin-bottom: 16px;
    }

    .form-label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #333;
      margin-bottom: 6px;
    }

    .form-hint {
      font-size: 12px;
      color: #666;
      margin-bottom: 8px;
      font-style: italic;
    }

    .form-input,
    .form-select,
    .form-textarea {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 13px;
      font-family: inherit;
    }

    .form-textarea {
      min-height: 80px;
      resize: vertical;
    }

    .form-checkbox {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .content-preview {
      background: #f8f9fa;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 16px;
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      max-height: 400px;
      overflow-y: auto;
    }

    .notion-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 20px;
    }

    .notion-btn {
      padding: 10px 20px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: background 0.2s;
    }

    .notion-btn-secondary {
      background: #f0f0f0;
      color: #333;
    }

    .notion-btn-secondary:hover {
      background: #e0e0e0;
    }

    .notion-btn-primary {
      background: #000;
      color: white;
    }

    .notion-btn-primary:hover {
      background: #333;
    }

    .notion-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    .refresh-context-btn {
      padding: 6px 12px;
      background: #f0f0f0;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      margin-bottom: 12px;
    }

    .refresh-context-btn:hover {
      background: #e0e0e0;
    }

    .success-icon {
      font-size: 48px;
      color: #059669;
      text-align: center;
      margin-bottom: 16px;
    }

    .success-message {
      text-align: center;
      margin-bottom: 20px;
    }

    .success-message h3 {
      margin: 0 0 8px 0;
      color: #333;
    }

    .success-message p {
      margin: 0;
      color: #666;
      font-size: 14px;
    }

    .view-notion-btn {
      display: inline-block;
      padding: 10px 20px;
      background: #000;
      color: white;
      text-decoration: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
    }

    .view-notion-btn:hover {
      background: #333;
    }
  `;

  firstUpdated() {
    // Load cached insights on initial render if session exists
    if (this.sessionId) {
      this.loadCachedInsights();
    }
  }

  updated(changedProperties: Map<string, unknown>) {
    if (changedProperties.has('sessionId') && this.sessionId) {
      // Clear insights and try to load cached when session changes
      this.insights = null;
      this.error = '';
      this.loadCachedInsights();
    }
  }

  private async loadCachedInsights() {
    // Try to load cached insights without showing loading state
    // This gives instant feedback if insights were previously extracted
    try {
      const insights = await api.getConcepts(this.sessionId, false, true); // cache_only=true
      if (insights) {
        this.insights = insights;
      }
    } catch {
      // Silently fail - user can click Extract button
    }
  }

  private async extractInsights(force: boolean = false) {
    if (!this.sessionId) return;

    this.loading = true;
    this.error = '';

    try {
      const insights = await api.getConcepts(this.sessionId, force);
      this.insights = insights;
    } catch (err) {
      console.error('Failed to extract insights:', err);
      this.error = 'Failed to extract insights. Please try again.';
    } finally {
      this.loading = false;
    }
  }

  private forceExtract() {
    // Check if there are no new exchanges and show confirm dialog
    if (this.insights?._cache_info?.no_new_exchanges) {
      this.showReextractConfirm = true;
    } else {
      this.extractInsights(true);
    }
  }

  private handleConfirmReextract() {
    this.showReextractConfirm = false;
    this.extractInsights(true);
  }

  private handleCancelReextract() {
    this.showReextractConfirm = false;
  }

  private async handleSaveToZotero() {
    if (!this.sessionId || !this.zoteroKey) {
      this.error = 'Cannot save to Zotero: missing session or Zotero key';
      return;
    }

    this.savingToZotero = true;
    this.zoteroSaveSuccess = false;
    this.error = '';

    try {
      await api.saveInsightsToZotero(this.sessionId, this.zoteroKey);
      this.zoteroSaveSuccess = true;
      // Hide success message after 3 seconds
      setTimeout(() => {
        this.zoteroSaveSuccess = false;
      }, 3000);
    } catch (err) {
      console.error('Failed to save to Zotero:', err);
      if (err instanceof ApiError) {
        this.error = `Failed to save to Zotero: ${err.message}`;
      } else {
        this.error = 'Failed to save to Zotero. Please try again.';
      }
    } finally {
      this.savingToZotero = false;
    }
  }

  private async handleGenerateLinkedIn() {
    if (!this.sessionId) {
      this.error = 'Cannot generate LinkedIn post: missing session';
      return;
    }

    this.generatingLinkedIn = true;
    this.error = '';

    try {
      const post = await api.generateLinkedInPost(this.sessionId);
      this.linkedInPost = post;
      this.showLinkedInModal = true;
      this.selectedEnding = 'question'; // Reset to default
    } catch (err) {
      console.error('Failed to generate LinkedIn post:', err);
      if (err instanceof ApiError) {
        this.error = `Failed to generate LinkedIn post: ${err.message}`;
      } else {
        this.error = 'Failed to generate LinkedIn post. Please try again.';
      }
    } finally {
      this.generatingLinkedIn = false;
    }
  }

  private handleCloseLinkedInModal() {
    this.showLinkedInModal = false;
  }

  private handleSelectEnding(ending: 'question' | 'declarative' | 'forward_looking') {
    this.selectedEnding = ending;
  }

  private async handleCopyPost() {
    if (!this.linkedInPost) return;

    // Get the selected ending index
    const endingIndex = this.selectedEnding === 'question' ? 0 : this.selectedEnding === 'declarative' ? 1 : 2;
    const fullPost = this.linkedInPost.full_post_options[endingIndex];

    try {
      await navigator.clipboard.writeText(fullPost);

      // Show visual feedback
      const button = this.shadowRoot?.querySelector('.copy-btn');
      if (button) {
        button.classList.add('copied');
        button.textContent = 'Copied!';
        setTimeout(() => {
          button.classList.remove('copied');
          button.textContent = 'Copy to Clipboard';
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      this.error = 'Failed to copy to clipboard';
    }
  }

  private searchDebounceTimer?: number;

  // Notion export handlers
  private async handleOpenNotionModal() {
    if (!this.sessionId) return;

    this.openingNotionModal = true;
    this.error = '';

    try {
      await this.loadNotionProjects();
      this.showNotionModal = true;
      this.notionStep = 1;
      this.notionSearchQuery = '';
    } finally {
      this.openingNotionModal = false;
    }
  }

  private async loadNotionProjects(query?: string) {
    this.loadingNotionProjects = true;
    try {
      const result = await api.listNotionProjects(query || undefined);
      this.notionProjects = result.projects;
    } catch (err) {
      console.error('Failed to load Notion projects:', err);
      if (err instanceof ApiError) {
        this.error = `Failed to load Notion projects: ${err.message}`;
      } else {
        this.error = 'Failed to load Notion projects. Please check your Notion authentication.';
      }
    } finally {
      this.loadingNotionProjects = false;
    }
  }

  private handleNotionSearch(e: Event) {
    const input = e.target as HTMLInputElement;
    this.notionSearchQuery = input.value;

    // Clear existing timer
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }

    // Debounce search by 300ms
    this.searchDebounceTimer = window.setTimeout(() => {
      this.loadNotionProjects(this.notionSearchQuery);
    }, 300);
  }

  private handleCloseNotionModal() {
    this.showNotionModal = false;
    this.notionStep = 1;
    this.notionSearchQuery = '';
    this.selectedProject = null;
    this.projectContext = null;
    this.suggestedTheme = '';
    this.relevanceStatement = '';
    this.selectedTheme = '';
    this.notionContent = '';
    this.notionExportUrl = '';
  }

  private handleSelectProject(project: NotionProject) {
    this.selectedProject = project;
  }

  private async handleNotionStep1Continue() {
    if (!this.selectedProject || !this.sessionId) return;

    this.notionStep = 2;
    this.loadingContext = true;
    this.generatingRelevance = true;
    this.error = '';

    try {
      // Load project context and generate relevance in parallel
      const [context, relevance] = await Promise.all([
        api.getNotionProjectContext(this.selectedProject.id),
        api.generateNotionRelevance(this.sessionId, this.selectedProject.id)
      ]);

      this.projectContext = context;
      this.suggestedTheme = relevance.suggested_theme;
      this.relevanceStatement = relevance.relevance_statement;

      // Set selected theme to suggested theme
      if (relevance.suggested_theme.startsWith('NEW:')) {
        this.selectedTheme = relevance.suggested_theme;
      } else {
        this.selectedTheme = relevance.suggested_theme;
      }
    } catch (err) {
      console.error('Failed to load context/relevance:', err);
      if (err instanceof ApiError) {
        this.error = `Failed to generate relevance: ${err.message}`;
      } else {
        this.error = 'Failed to generate relevance. Please try again.';
      }
    } finally {
      this.loadingContext = false;
      this.generatingRelevance = false;
    }
  }

  private async handleRefreshContext() {
    if (!this.selectedProject) return;

    this.loadingContext = true;
    this.error = '';

    try {
      const context = await api.getNotionProjectContext(this.selectedProject.id, true);
      this.projectContext = context;
    } catch (err) {
      console.error('Failed to refresh context:', err);
      if (err instanceof ApiError) {
        this.error = `Failed to refresh context: ${err.message}`;
      } else {
        this.error = 'Failed to refresh context. Please try again.';
      }
    } finally {
      this.loadingContext = false;
    }
  }

  private async handleNotionStep2Continue() {
    if (!this.selectedProject || !this.sessionId) return;

    this.generatingContent = true;
    this.error = '';

    try {
      const result = await api.generateNotionContent(
        this.sessionId,
        this.selectedProject.id,
        this.selectedTheme,
        this.relevanceStatement,
        this.includeSessionNotes
      );

      this.notionContent = result.content;
      this.notionStep = 3;
    } catch (err) {
      console.error('Failed to generate content:', err);
      if (err instanceof ApiError) {
        this.error = `Failed to generate content: ${err.message}`;
      } else {
        this.error = 'Failed to generate content. Please try again.';
      }
    } finally {
      this.generatingContent = false;
    }
  }

  private async handleNotionStep3Continue() {
    if (!this.selectedProject || !this.sessionId) return;

    this.exportingToNotion = true;
    this.error = '';

    try {
      const result = await api.exportToNotion(
        this.sessionId,
        this.selectedProject.id,
        this.selectedTheme,
        this.notionContent,
        this.literatureReviewHeading
      );

      this.notionExportUrl = result.page_url;
      this.notionStep = 4;
    } catch (err) {
      console.error('Failed to export to Notion:', err);
      if (err instanceof ApiError) {
        this.error = `Failed to export to Notion: ${err.message}`;
      } else {
        this.error = 'Failed to export to Notion. Please try again.';
      }
    } finally {
      this.exportingToNotion = false;
    }
  }

  private handleNotionStepBack() {
    if (this.notionStep > 1) {
      this.notionStep = (this.notionStep - 1) as 1 | 2 | 3 | 4;
    }
  }

  private renderSection(title: string, items: string[] | undefined) {
    if (!items || items.length === 0) return '';

    return html`
      <div class="section">
        <div class="section-title">${title}</div>
        <ul class="insight-list">
          ${items.map(item => html`<li class="insight-item">${item}</li>`)}
        </ul>
      </div>
    `;
  }

  private renderSummary() {
    if (!this.insights?.summary) return '';

    return html`
      <div class="section">
        <div class="section-title">Summary</div>
        <div class="insight-item">${this.insights.summary}</div>
      </div>
    `;
  }

  private renderAssessment() {
    const assessment = this.insights?.assessment;
    if (!assessment || (!assessment.strengths?.length && !assessment.limitations?.length)) {
      return '';
    }

    return html`
      <div class="section">
        <div class="section-title">Paper Assessment</div>
        ${assessment.strengths && assessment.strengths.length > 0 ? html`
          <div class="subsection-title">Strengths</div>
          <ul class="insight-list">
            ${assessment.strengths.map(item => html`<li class="insight-item">${item}</li>`)}
          </ul>
        ` : ''}
        ${assessment.limitations && assessment.limitations.length > 0 ? html`
          <div class="subsection-title">Limitations</div>
          <ul class="insight-list">
            ${assessment.limitations.map(item => html`<li class="insight-item">${item}</li>`)}
          </ul>
        ` : ''}
      </div>
    `;
  }

  private renderLinkedInModal() {
    if (!this.showLinkedInModal || !this.linkedInPost) return '';

    // Get the selected ending index
    const endingIndex = this.selectedEnding === 'question' ? 0 : this.selectedEnding === 'declarative' ? 1 : 2;
    const fullPost = this.linkedInPost.full_post_options[endingIndex];

    // Highlight [PAPER LINK] placeholder
    const highlightedPost = fullPost.replace(
      /\[PAPER LINK\]/g,
      '<span class="paper-link">[PAPER LINK]</span>'
    );

    return html`
      <div class="linkedin-modal" @click=${this.handleCloseLinkedInModal}>
        <div class="linkedin-dialog" @click=${(e: Event) => e.stopPropagation()}>
          <div class="linkedin-header">
            <div class="linkedin-title">LinkedIn Post</div>
            <button class="close-btn" @click=${this.handleCloseLinkedInModal}>&times;</button>
          </div>

          <div class="post-preview" .innerHTML=${highlightedPost}></div>

          <div class="ending-selector">
            <div class="ending-label">Select Ending:</div>
            <div class="ending-options">
              <button
                class="ending-option ${this.selectedEnding === 'question' ? 'selected' : ''}"
                @click=${() => this.handleSelectEnding('question')}
              >
                Question
              </button>
              <button
                class="ending-option ${this.selectedEnding === 'declarative' ? 'selected' : ''}"
                @click=${() => this.handleSelectEnding('declarative')}
              >
                Declarative
              </button>
              <button
                class="ending-option ${this.selectedEnding === 'forward_looking' ? 'selected' : ''}"
                @click=${() => this.handleSelectEnding('forward_looking')}
              >
                Forward-looking
              </button>
            </div>
          </div>

          <div class="linkedin-actions">
            <button class="copy-btn" @click=${this.handleCopyPost}>
              Copy to Clipboard
            </button>
          </div>
        </div>
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
      this.insights.summary ||
      (this.insights.learnings && this.insights.learnings.length > 0) ||
      (this.insights.assessment?.strengths && this.insights.assessment.strengths.length > 0) ||
      (this.insights.assessment?.limitations && this.insights.assessment.limitations.length > 0) ||
      (this.insights.open_questions && this.insights.open_questions.length > 0);

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
            ${this.insights.metadata.flagged_count ? ` • ${this.insights.metadata.flagged_count} starred` : ''}
          </div>
        ` : ''}

        ${this.renderSummary()}
        ${this.renderSection('What I Learned', this.insights.learnings)}
        ${this.renderAssessment()}
        ${this.renderSection('Open Questions', this.insights.open_questions)}

        ${this.zoteroSaveSuccess ? html`
          <div class="save-success">
            ✓ Insights saved to Zotero as a note!
          </div>
        ` : ''}

        <div class="reextract-container">
          <button class="reextract-btn" @click=${this.forceExtract}>
            Re-extract Insights
          </button>
          ${this.zoteroKey ? html`
            <button
              class="save-to-zotero-btn"
              @click=${this.handleSaveToZotero}
              ?disabled=${this.savingToZotero}
            >
              ${this.savingToZotero ? 'Saving...' : 'Send to Zotero'}
            </button>
          ` : ''}
          <button
            class="share-to-linkedin-btn"
            @click=${this.handleGenerateLinkedIn}
            ?disabled=${this.generatingLinkedIn}
          >
            ${this.generatingLinkedIn ? 'Generating...' : 'Share to LinkedIn'}
          </button>
          <button
            class="add-to-notion-btn"
            @click=${this.handleOpenNotionModal}
            ?disabled=${this.openingNotionModal}
          >
            ${this.openingNotionModal ? 'Loading...' : 'Add to Notion'}
          </button>
        </div>

        ${this.showReextractConfirm ? html`
          <div class="confirm-overlay" @click=${this.handleCancelReextract}>
            <div class="confirm-dialog" @click=${(e: Event) => e.stopPropagation()}>
              <div class="confirm-message">
                No new questions since last extraction.<br><br>
                The insights will be the same unless you've asked new questions.
              </div>
              <div class="confirm-actions">
                <button class="confirm-btn confirm-btn-cancel" @click=${this.handleCancelReextract}>
                  Cancel
                </button>
                <button class="confirm-btn confirm-btn-primary" @click=${this.handleConfirmReextract}>
                  Re-extract
                </button>
              </div>
            </div>
          </div>
        ` : ''}

        ${this.renderLinkedInModal()}
        ${this.renderNotionModal()}
      </div>
    `;
  }

  private renderNotionModal() {
    if (!this.showNotionModal) return '';

    return html`
      <div class="notion-modal" @click=${this.handleCloseNotionModal}>
        <div class="notion-dialog" @click=${(e: Event) => e.stopPropagation()}>
          <div class="notion-header">
            <div>
              <div class="notion-title">Add to Notion</div>
              <div class="notion-step-indicator">Step ${this.notionStep} of 4</div>
            </div>
            <button class="close-btn" @click=${this.handleCloseNotionModal}>&times;</button>
          </div>

          ${this.notionStep === 1 ? this.renderNotionStep1() : ''}
          ${this.notionStep === 2 ? this.renderNotionStep2() : ''}
          ${this.notionStep === 3 ? this.renderNotionStep3() : ''}
          ${this.notionStep === 4 ? this.renderNotionStep4() : ''}
        </div>
      </div>
    `;
  }

  private renderNotionStep1() {
    return html`
      <div>
        <p style="margin-bottom: 12px; color: #666; font-size: 14px;">
          Select a Notion page to add this paper to:
        </p>

        <div style="margin-bottom: 16px;">
          <input
            type="text"
            class="search-input"
            placeholder="Search pages..."
            .value=${this.notionSearchQuery}
            @input=${this.handleNotionSearch}
          />
        </div>

        ${this.loadingNotionProjects ? html`
          <div style="text-align: center; padding: 40px;">
            <loading-spinner></loading-spinner>
            <div style="margin-top: 12px; color: #666; font-size: 13px;">
              Loading your Notion pages...
            </div>
          </div>
        ` : html`
          ${this.notionProjects.length === 0 ? html`
            <div style="text-align: center; padding: 40px; color: #666;">
              <p>No Notion pages found.</p>
              <p style="font-size: 13px; margin-top: 8px;">
                Make sure you've granted Scholia access to your Notion pages.
              </p>
            </div>
          ` : html`
            <div class="project-list">
              ${this.notionProjects.map(project => html`
                <div
                  class="project-item ${this.selectedProject?.id === project.id ? 'selected' : ''}"
                  @click=${() => this.handleSelectProject(project)}
                >
                  <div class="project-title">${project.title}</div>
                </div>
              `)}
            </div>
          `}
        `}

        <div class="notion-actions">
          <button
            class="notion-btn notion-btn-secondary"
            @click=${this.handleCloseNotionModal}
          >
            Cancel
          </button>
          <button
            class="notion-btn notion-btn-primary"
            @click=${this.handleNotionStep1Continue}
            ?disabled=${!this.selectedProject}
          >
            Continue
          </button>
        </div>
      </div>
    `;
  }

  private renderNotionStep2() {
    const themes = this.projectContext?.themes || [];
    const isNewTheme = this.selectedTheme.startsWith('NEW:');

    return html`
      <div>
        <p style="margin-bottom: 8px; color: #333; font-size: 14px;">
          <strong>${this.selectedProject?.title}</strong>
        </p>
        ${this.projectContext ? html`
          <div style="margin-bottom: 16px; padding: 12px; background: #f5f5f5; border-radius: 4px; font-size: 13px;">
            ${this.projectContext.hypothesis ? html`
              <p style="margin: 0 0 8px 0; color: #666;">
                <strong>Hypothesis:</strong> ${this.projectContext.hypothesis}
              </p>
            ` : ''}
            ${this.projectContext.fetched_at ? html`
              <p style="margin: 0; color: #999; font-size: 12px; font-style: italic;">
                Context from: ${new Date(this.projectContext.fetched_at).toLocaleDateString()}
              </p>
            ` : ''}
          </div>
        ` : ''}

        ${this.loadingContext || this.generatingRelevance ? html`
          <div style="text-align: center; padding: 40px;">
            <loading-spinner></loading-spinner>
            <div style="margin-top: 12px; color: #666; font-size: 13px;">
              ${this.loadingContext ? 'Loading project context...' : 'Generating relevance...'}
            </div>
          </div>
        ` : html`
          <button
            class="refresh-context-btn"
            @click=${this.handleRefreshContext}
            ?disabled=${this.loadingContext}
          >
            ${this.loadingContext ? 'Refreshing...' : '↻ Refresh Project Context'}
          </button>

          <div class="form-group">
            <label class="form-label">Save Location</label>
            <div class="form-hint">
              Name of the section in your Notion page where papers are organized
            </div>
            <input
              type="text"
              class="form-input"
              .value=${this.literatureReviewHeading}
              @input=${(e: Event) => {
                this.literatureReviewHeading = (e.target as HTMLInputElement).value;
              }}
              placeholder="Literature Review"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Theme</label>
            <select
              class="form-select"
              .value=${this.selectedTheme}
              @change=${(e: Event) => {
                this.selectedTheme = (e.target as HTMLSelectElement).value;
              }}
            >
              ${themes.map(theme => html`
                <option value=${theme}>${theme}</option>
              `)}
              ${this.suggestedTheme.startsWith('NEW:') ? html`
                <option value=${this.suggestedTheme}>${this.suggestedTheme.substring(5)} (suggested)</option>
              ` : ''}
              <option value="NEW: ">+ Create new theme</option>
            </select>
          </div>

          ${isNewTheme ? html`
            <div class="form-group">
              <label class="form-label">New Theme Name</label>
              <input
                type="text"
                class="form-input"
                .value=${this.selectedTheme.substring(5)}
                @input=${(e: Event) => {
                  this.selectedTheme = 'NEW: ' + (e.target as HTMLInputElement).value;
                }}
                placeholder="Enter theme name"
              />
            </div>
          ` : ''}

          <div class="form-group">
            <label class="form-label">Relevance Statement</label>
            <div class="form-hint">
              This frames how Claude will interpret the paper's insights for your project. Edit to match your thinking.
            </div>
            <textarea
              class="form-textarea"
              .value=${this.relevanceStatement}
              @input=${(e: Event) => {
                this.relevanceStatement = (e.target as HTMLTextAreaElement).value;
              }}
              placeholder="How does this paper relate to your project?"
            ></textarea>
          </div>

          <div class="form-group">
            <label class="form-checkbox">
              <input
                type="checkbox"
                .checked=${this.includeSessionNotes}
                @change=${(e: Event) => {
                  this.includeSessionNotes = (e.target as HTMLInputElement).checked;
                }}
              />
              <span>Include session notes</span>
            </label>
            <div class="form-hint" style="margin-top: 4px; margin-left: 24px;">
              Adds a "Session notes" section with condensed takeaways from your conversation about the paper
            </div>
          </div>
        `}

        <div class="notion-actions">
          <button
            class="notion-btn notion-btn-secondary"
            @click=${this.handleNotionStepBack}
          >
            Back
          </button>
          <button
            class="notion-btn notion-btn-primary"
            @click=${this.handleNotionStep2Continue}
            ?disabled=${this.generatingContent || !this.relevanceStatement || !this.selectedTheme}
          >
            ${this.generatingContent ? 'Generating...' : 'Generate Preview'}
          </button>
        </div>
      </div>
    `;
  }

  private renderNotionStep3() {
    return html`
      <div>
        <p style="margin-bottom: 16px; color: #666; font-size: 14px;">
          Preview of your Notion entry:
        </p>

        <div class="content-preview">${this.notionContent}</div>

        <div class="notion-actions">
          <button
            class="notion-btn notion-btn-secondary"
            @click=${this.handleNotionStepBack}
          >
            Back
          </button>
          <button
            class="notion-btn notion-btn-primary"
            @click=${this.handleNotionStep3Continue}
            ?disabled=${this.exportingToNotion}
          >
            ${this.exportingToNotion ? 'Exporting...' : 'Add to Project'}
          </button>
        </div>
      </div>
    `;
  }

  private renderNotionStep4() {
    return html`
      <div>
        <div class="success-icon">✓</div>
        <div class="success-message">
          <h3>Added to ${this.selectedProject?.title}</h3>
          <p>Your paper has been successfully added to your Notion project.</p>
        </div>

        <div style="text-align: center;">
          <a
            href=${this.notionExportUrl}
            target="_blank"
            rel="noopener noreferrer"
            class="view-notion-btn"
          >
            View in Notion
          </a>
        </div>

        <div class="notion-actions">
          <button
            class="notion-btn notion-btn-primary"
            @click=${this.handleCloseNotionModal}
          >
            Done
          </button>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'concepts-tab': ConceptsTab;
  }
}
