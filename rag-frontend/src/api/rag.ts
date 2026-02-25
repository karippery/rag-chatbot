/**
 * src/api/rag.ts
 *
 * Chat-session-based RAG API.
 *
 * Backend routes:
 *   GET    /rag/chats/                     → list sessions
 *   POST   /rag/chats/                     → create session
 *   DELETE /rag/chats/<id>/                → soft-delete session
 *   GET    /rag/chats/<id>/messages/       → get messages in session
 *   POST   /rag/chats/<id>/message/        → send message (RAG query)
 */

import api from './client';

// ── Domain types ───────────────────────────────────────────────────────────

export interface Source {
  chunk_id:       number;
  document_id:    number;
  document_title: string;
  chunk_index:    number;
  similarity_score?: number;
}

export interface ChatSession {
  id:                   number;
  title:                string;
  created_at:           string;
  updated_at:           string;
  message_count:        number;
  last_message_preview: string | null;
}

export interface ChatMessage {
  id:              number;
  query:           string;
  response:        string;
  response_source: 'LLM' | 'EXTRACTIVE' | 'NO_RESULTS' | 'ERROR';
  created_at:      string;
  security_level:  string;
  username:        string;
  sources:         Source[];
}

export interface SendMessageResponse {
  success:     boolean;
  query_id:    number;
  answer:      string;
  source:      string;
  model:       string | null;
  chunks_used: number;
  latency_ms:  number;
  token_count: number;
  sources:     Source[];
  error?:      string;
}

// ── API calls ──────────────────────────────────────────────────────────────

export const chatApi = {
  /** List all chat sessions for the current user */
  listSessions: () =>
    api.get<{ results: ChatSession[]; count: number }>('/rag/v1/chats/'),

  /** Create a new chat session, optionally with an initial title */
  createSession: (title = '') =>
    api.post<ChatSession>('/rag/v1/chats/', { title }),

  /** Soft-delete a chat session */
  deleteSession: (id: number) =>
    api.delete(`/rag/v1/chats/${id}/`),

  /** Fetch all messages for a session (paginated, oldest-first) */
  getMessages: (chatId: number) =>
    api.get<{ results: ChatMessage[]; count: number }>(`/rag/v1/chats/${chatId}/messages/`),

  /** Send a user message and receive the RAG response */
  sendMessage: (chatId: number, query: string, mode: 'quick' | 'detailed' = 'quick') =>
    api.post<SendMessageResponse>(`/rag/v1/chats/${chatId}/messages/`, { query, mode }),
};