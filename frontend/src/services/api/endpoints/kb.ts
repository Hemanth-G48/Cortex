import { request } from '../core'
import type { KbSearchResponse, KbGraphResponse, KbStats, QuizHistoryItem } from '../types'

// ── Knowledge Base search (defect #12, #89 fix) ─────────────────────────
//
// Backs the KnowledgeBase search box via POST /api/kb/search in hybrid mode,
// and the Tutor chat pre-step that grounds answers in vault chunks.

export const kbSearchApi = {
  query: (q: string, mode: 'keyword' | 'semantic' | 'hybrid' = 'hybrid', page = 1, pageSize = 20) =>
    request<KbSearchResponse>('/api/kb/search', {
      method: 'POST',
      body: JSON.stringify({ query: q, mode, page, page_size: pageSize }),
    }),
}

// ── Knowledge Graph + stats (defect #2 fix) ──────────────────────────────
//
// Wraps GET /api/kb/graph and GET /api/kb/stats so the Dashboard radar can
// be driven by the live vault instead of the static RadarChart.defaultData.

export const kbGraphApi = {
  list: (params?: { source?: string; tag?: string; concept?: string; relation?: string; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.source) qs.set('source', params.source)
    if (params?.tag) qs.set('tag', params.tag)
    if (params?.concept) qs.set('concept', params.concept)
    if (params?.relation) qs.set('relation', params.relation)
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    const q = qs.toString()
    return request<KbGraphResponse>(`/api/kb/graph${q ? `?${q}` : ''}`)
  },
  stats: () => request<KbStats>('/api/kb/stats'),
}

// ── Quiz history (defect #77 fix) ────────────────────────────────────────
//
// GET /quizzes/history returns the server truth for past quiz attempts;
// POST /quizzes/history creates a new entry so the history survives page
// reloads and is shared across devices.

export const quizzesHistoryApi = {
  list: () => request<QuizHistoryItem[]>('/quizzes/history'),
  create: (d: { score: number; total_questions: number }) =>
    request<QuizHistoryItem | null>('/quizzes/history', {
      method: 'POST',
      body: JSON.stringify(d),
    }),
}

// ── Quest completion → KB capture XP (defect #79 fix) ────────────────────
//
// Called after a quest is completed so the Second Brain rewards the user
// for completing structured work, not just for capturing notes.

export const kbCaptureXpApi = {
  award: (amount: number) =>
    request<{ xp_awarded: number }>('/api/kb/capture-xp', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    }),
}
