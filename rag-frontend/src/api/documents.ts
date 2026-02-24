/**
 * src/api/documents.ts
 */

import api from './client';

export interface Document {
  id:                 number;
  title:              string;
  description:        string;
  security_level:     string;
  file_type:          string;
  file_size:          number;
  original_name:      string;
  status:             'pending' | 'processing' | 'indexed' | 'failed';
  chunk_count:        number | null;
  error_message:      string | null;
  uploaded_by_email:  string;
  uploaded_by_role:   string;
  created_at:         string;
  updated_at:         string;
}

export interface UploadPayload {
  file:           File;
  title:          string;
  description?:   string;
  security_level: string;
}

export const documentsApi = {
  list: () =>
    api.get<{ results: Document[] }>('/documents/v1/documents/'),

  upload: (payload: UploadPayload) => {
    const form = new FormData();
    form.append('file',           payload.file);
    form.append('title',          payload.title);
    form.append('security_level', payload.security_level);
    if (payload.description) form.append('description', payload.description);
    return api.post<Document>('/documents/v1/upload/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  delete: (id: number) =>
    api.delete(`/documents/v1/${id}/`),

  download: (id: number) =>
    api.get(`/documents/v1/${id}/download/`, { responseType: 'blob' }),
};