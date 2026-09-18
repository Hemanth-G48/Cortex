// Endpoint client for this domain — extracted from services/api.ts (F8 split).

import { api, BASE } from '../core'
import type { Book, BookCategory, BookGapAnalysis, BookGapChapter, BookGapDashboard, BookGapItem, BookGapOverview, BookGapStatus, BookGapTopic, BookInsights, BookListResponse } from '../types/book'

export const bookGapApi = {
  overview: () => api.get<BookGapOverview>('/kb/books/overview'),
  analyze: (bookId: number) =>
    api.post<{
      analysis: BookGapAnalysis;
      chapters: BookGapChapter[];
      topics: BookGapTopic[];
      items: number;
    }>(`/kb/books/${bookId}/analyze`),
  dashboard: (bookId: number) => api.get<BookGapDashboard>(`/kb/books/${bookId}/dashboard`),
  topics: (bookId: number) => api.get<{ topics: BookGapTopic[] }>(`/kb/books/${bookId}/topics`),
  analyzeTopic: (bookId: number, topicId: number) =>
    api.post<BookGapTopic>(`/kb/books/${bookId}/topics/${topicId}/analyze`),
  addTopicToBrain: (bookId: number, topicId: number) =>
    api.post<{
      document: { id: number; title: string; status: string };
      created: boolean;
      topic_id: number;
    }>(`/kb/books/${bookId}/topics/${topicId}/add-to-brain`),
  items: (bookId: number, params?: { status?: BookGapStatus; chapter?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.chapter) qs.set('chapter', params.chapter);
    const q = qs.toString();
    return api.get<{ items: BookGapItem[] }>(`/kb/books/${bookId}/items${q ? `?${q}` : ''}`);
  },
  queue: (bookId: number) => api.get<{ items: BookGapItem[] }>(`/kb/books/${bookId}/queue`),
  setStatus: (bookId: number, itemId: number, status: 'learning' | 'learned' | 'mastered') =>
    api.post<BookGapItem>(`/kb/books/${bookId}/items/${itemId}/status`, { status }),
};


export const bookApi = {
  list: (params?: { category?: BookCategory; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set('category', params.category);
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    const q = qs.toString();
    return api.get<BookListResponse>(`/books${q ? `?${q}` : ''}`);
  },
  create: (d: { title: string; author?: string | null; category?: BookCategory }) => api.post<Book>('/books', d),
  update: (id: number, d: Partial<Omit<Book, 'id' | 'created_at'>>) => api.put<Book>(`/books/${id}`, d),
  remove: (id: number) => api.del<{ ok: boolean }>(`/books/${id}`),
  insights: () => api.get<BookInsights>('/books/insights'),
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return fetch(`${BASE}/books/upload`, {
      method: 'POST',
      body: form,
    }).then(async (r) => {
      if (!r.ok) {
        // Surface the backend's detail (e.g. "File too large (max 100 MB)")
        // instead of a raw status line.
        let detail: string | null = null;
        try {
          const body = await r.json();
          detail = body?.detail?.error ?? body?.detail ?? null;
        } catch {
          /* non-JSON error body */
        }
        throw new Error(detail ? `Upload failed: ${detail}` : `Upload ${r.status}: ${r.statusText}`);
      }
      return r.json();
    }) as Promise<{ url: string; filename: string }>;
  },
};

