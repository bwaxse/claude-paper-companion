export interface Session {
  session_id: string;
  filename: string;
  created_at: string;
  initial_analysis: string;
  page_count?: number;
  zotero_key?: string;  // Zotero item key if session was loaded from Zotero
}

export interface ConversationMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  highlighted_text?: string;
  page?: number;
  timestamp: string;
  model?: string;
  flagged?: boolean;
}

export interface SessionFull extends Session {
  conversation: ConversationMessage[];
  flags: number[];
  highlights: Highlight[];
}

export interface Highlight {
  id?: number;
  text: string;
  page: number;
  exchange_id?: number;
  coords?: BoundingBox;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ZoteroItem {
  key: string;
  title: string;
  authors: string;
  year?: string;
  publication?: string;
  item_type: string;
}
