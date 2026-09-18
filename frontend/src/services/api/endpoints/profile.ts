import { request } from '../core'
import type { User } from '../types/user'

export const profileApi = {
  get: () => request<{ user: User }>('/profile'),
  update: (d: Partial<User>) =>
    request<{ user: User }>('/profile', { method: 'PUT', body: JSON.stringify(d) }),
  // Server-persisted client prefs (audit defect #96 — AI model etc.).
  getPrefs: () => request<{ prefs: Record<string, unknown> }>('/profile/prefs'),
  updatePrefs: (d: Record<string, unknown>) =>
    request<{ prefs: Record<string, unknown> }>('/profile/prefs', { method: 'PUT', body: JSON.stringify(d) }),
}

// ── Mood analytics (for Journal mood chips) ──────────────────────────────

export interface MoodDistributionItem {
  mood: string
  count: number
}

export interface MoodAnalytics {
  total_entries: number
  avg_energy: number | null
  dominant_mood: string | null
  distribution: MoodDistributionItem[]
  daily_trend: Array<{ date: string; avg_energy: number; mood: string }>
}

export const moodApi = {
  analytics: (days = 30) => request<MoodAnalytics>(`/api/mood/analytics?days=${days}`),
}

// ── Knowledge Base related documents (defect #42 fix) ────────────────────
//
// Backed by GET /api/kb/documents/:document_id/related (kb_related.py).
// Returns RELATED / WIKILINK / BACKLINK neighbors with weights.

export interface KbRelatedDoc {
  id: number
  title: string
  relation: string | null
  weight: number | null
}

export interface KbRelatedResponse {
  document_id: number
  related: KbRelatedDoc[]
  method: string
}

export const kbRelatedApi = {
  forDocument: (documentId: number) =>
    request<KbRelatedResponse>(`/api/kb/documents/${documentId}/related`),
}
