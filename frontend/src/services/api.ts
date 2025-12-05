import type { Session, SessionFull, ZoteroItem } from '../types/session';
import type { QueryRequest, QueryResponse } from '../types/query';
import type { OutlineItem } from '../types/pdf';

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiClient {
  private baseUrl = '';

  /**
   * Create a new session by uploading a PDF
   */
  async createSession(file: File): Promise<Session> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/sessions/new`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new ApiError(
        `Failed to create session: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Create a new session from a Zotero paper
   */
  async createSessionFromZotero(zoteroKey: string): Promise<Session> {
    const formData = new FormData();
    formData.append('zotero_key', zoteroKey);

    const response = await fetch(`${this.baseUrl}/sessions/new`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new ApiError(
        `Failed to create session from Zotero: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Get full session details including conversation history
   */
  async getSession(sessionId: string): Promise<SessionFull> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to get session: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Get document outline (table of contents)
   */
  async getOutline(sessionId: string): Promise<OutlineItem[]> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/outline`);

    if (!response.ok) {
      if (response.status === 404) {
        return []; // No outline available
      }
      throw new ApiError(
        `Failed to get outline: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Get extracted key concepts from the document
   */
  async getConcepts(sessionId: string, force: boolean = false, cacheOnly: boolean = false): Promise<any> {
    const params = new URLSearchParams();
    if (force) params.append('force', 'true');
    if (cacheOnly) params.append('cache_only', 'true');

    const url = params.toString()
      ? `${this.baseUrl}/sessions/${sessionId}/concepts?${params}`
      : `${this.baseUrl}/sessions/${sessionId}/concepts`;
    const response = await fetch(url);

    if (!response.ok) {
      if (response.status === 404) {
        return null; // No insights available
      }
      throw new ApiError(
        `Failed to get concepts: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * List all sessions
   */
  async listSessions(limit = 50, offset = 0): Promise<Session[]> {
    const response = await fetch(
      `${this.baseUrl}/sessions?limit=${limit}&offset=${offset}`
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to list sessions: ${response.statusText}`,
        response.status
      );
    }

    const data = await response.json();
    // Backend returns {sessions: [...], total: n}, extract just the sessions array
    return data.sessions || [];
  }

  /**
   * Query the paper with optional highlighted text
   */
  async query(sessionId: string, request: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Query failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  }

  /**
   * Toggle flag on an exchange
   */
  async toggleFlag(sessionId: string, exchangeId: number, note?: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/sessions/${sessionId}/exchanges/${exchangeId}/flag`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note })
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to toggle flag: ${response.statusText}`,
        response.status
      );
    }
  }

  /**
   * Remove flag from an exchange
   */
  async unflag(sessionId: string, exchangeId: number): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/sessions/${sessionId}/exchanges/${exchangeId}/flag`,
      {
        method: 'DELETE'
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to unflag: ${response.statusText}`,
        response.status
      );
    }
  }

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new ApiError(
        `Failed to delete session: ${response.statusText}`,
        response.status
      );
    }
  }

  /**
   * Export session as markdown
   */
  async exportSession(sessionId: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/export`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to export session: ${response.statusText}`,
        response.status
      );
    }

    return response.text();
  }

  /**
   * Search Zotero library
   */
  async searchZotero(query: string, limit = 20): Promise<ZoteroItem[]> {
    const response = await fetch(
      `${this.baseUrl}/zotero/search?query=${encodeURIComponent(query)}&limit=${limit}`
    );

    if (!response.ok) {
      throw new ApiError(
        `Zotero search failed: ${response.statusText}`,
        response.status
      );
    }

    const data = await response.json();
    // Backend returns {items: [...], total: n}
    return data.items || [];
  }

  /**
   * Get recent papers from Zotero
   */
  async getRecentPapers(limit = 20): Promise<ZoteroItem[]> {
    const response = await fetch(`${this.baseUrl}/zotero/recent?limit=${limit}`);

    if (!response.ok) {
      throw new ApiError(
        `Failed to get recent papers: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Get attachment files linked to a Zotero paper
   */
  async getPaperAttachments(zoteroKey: string): Promise<ZoteroItem[]> {
    const response = await fetch(
      `${this.baseUrl}/zotero/attachments/${zoteroKey}`
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to get attachments: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Load supplement paper text for reference in conversation
   */
  async loadSupplement(sessionId: string, zoteroKey: string): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/zotero/load-supplement?session_id=${sessionId}&zotero_key=${zoteroKey}`,
      { method: 'POST' }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to load supplement: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  /**
   * Upload a supplemental PDF to Zotero
   */
  async uploadSupplement(sessionId: string, zoteroKey: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('zotero_key', zoteroKey);
    formData.append('file', file);

    const response = await fetch(
      `${this.baseUrl}/zotero/upload-supplement`,
      {
        method: 'POST',
        body: formData
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Failed to upload supplement: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }
}

// Export singleton instance
export const api = new ApiClient();
