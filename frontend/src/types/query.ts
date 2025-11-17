export interface QueryRequest {
  query: string;
  highlighted_text?: string;
  page?: number;
  use_sonnet?: boolean;
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
