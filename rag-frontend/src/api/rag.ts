/**
 * src/api/rag.ts
 */

import api from './client';

export interface Source {
  document_title:  string;
  similarity_score: number;
  chunk_index:     number;
}

export interface QueryResponse {
  success:     boolean;
  query_id:    number;
  answer:      string;
  source:      string;
  model:       string | null;
  chunks_used: number;
  latency_ms:  number;
  token_count: number;
  sources:     Source[];
}

export interface HistoryItem {
  id:              number;
  query:           string;
  response:        string;
  response_source: string;
  created_at:      string;
  security_level:  string;
  is_flagged:      boolean;
  username:        string;
  sources:         Source[];
}

export const ragApi = {
  query: (query: string, mode: 'quick' | 'detailed' = 'quick') =>
    api.post<QueryResponse>('/rag/v1/query/', { query, mode }),

  history: () =>
    api.get<{ results: HistoryItem[] }>('/rag/v1/history/'),

  historyDetail: (id: number) =>
    api.get<HistoryItem>(`/rag/v1/history/${id}/`),
};