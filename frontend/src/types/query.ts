export interface QueryRequest {
  query: string;
  highlighted_text?: string;
  page?: number;
  model?: 'sonnet' | 'haiku';
}

export interface QueryResponse {
  exchange_id: number;
  response: string;
  model_used: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

export interface LinkedInPostEndings {
  question: string;
  declarative: string;
  forward_looking: string;
}

export interface LinkedInPostResponse {
  hook: string;
  body: string;
  endings: LinkedInPostEndings;
  full_post_options: string[];
}
