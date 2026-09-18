// Books + Book Gap Analyzer types.
// Extracted from services/api.ts (F8 split).

export type BookCategory = 'reading' | 'finished' | 'want';

export interface Book {
  id: number;
  title: string;
  author: string | null;
  category: BookCategory;
  cover_url: string | null;
  file_url: string | null;
  created_at: string;
}

export interface BookInsights {
  total: number;
  finished: number;
  reading: number;
  want: number;
  completion_pct: number;
  per_author: Record<string, number>;
}

export interface BookListResponse {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
}

// ----- Book Knowledge Gap Analyzer types (TOC-first workflow) -----
export type BookGapStatus = 'KNOWN' | 'PARTIALLY_KNOWN' | 'UNKNOWN' | 'NEEDS_REVIEW';

export type BookGapMyStatus = 'UNKNOWN' | 'LEARNING' | 'LEARNED' | 'MASTERED';

// Stage-2 per-topic deep-analysis state.
export type BookGapDeepStatus = 'NOT_ANALYZED' | 'ANALYZING' | 'ANALYZED' | 'FAILED';

export interface BookGapAnalysis {
  book_id: number;
  status: string;
  total_pages: number;
  chapters: number;
  total_concepts: number;
  known: number;
  partial: number;
  unknown: number;
  needs_review?: number;
  deep_analyzed?: number;
  historical: number;
  recommended_pages: number;
  recommended_pct: number;
  analyzed_at: string | null;
  errors: string[];
}

/** One missing sub-concept found by a deep topic analysis (page evidence). */
export interface BookGapItem {
  id: number;
  book_id: number;
  deep_topic_id?: number | null;
  concept: string;
  display_name: string;
  chapter: string | null;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  snippet: string | null;
  why: string | null;
  status: BookGapStatus;
  my_status: BookGapMyStatus;
  knowledge_level: number;
  difficulty: string;
  est_minutes: number;
  is_historical: boolean;
  historical_note: string | null;
}

/** A deep-analysis missing sub-concept with its page evidence + rationale. */
export interface BookGapDeepMissing {
  concept: string;
  why: string | null;
  deterministic?: boolean;
}

/** Persisted Stage-2 result for one topic. */
export interface BookGapDeepResult {
  summary: string | null;
  covered: string[];
  missing: BookGapDeepMissing[];
  ai_used: boolean;
  deterministic?: boolean;
  error?: string;
}

/** One Stage-1 TOC topic (chapter/section/subsection) with its SB match. */
export interface BookGapTopic {
  id: number;
  book_id: number;
  title: string;
  level: number;
  parent_title: string | null;
  page_start: number | null;
  page_end: number | null;
  status: BookGapStatus;
  match_source: string | null;
  second_brain_match: string | null;
  confidence: number;
  deep_status: BookGapDeepStatus;
  deep_result: BookGapDeepResult | null;
  analyzed_at: string | null;
}

export interface BookGapOverviewBook {
  book_id: number;
  title: string;
  author: string | null;
  file_url: string | null;
  analyzed: boolean;
  total_concepts: number;
  known: number;
  partial: number;
  unknown: number;
  needs_review?: number;
  deep_analyzed?: number;
  recommended_pct: number;
}

export interface BookGapOverview {
  books: BookGapOverviewBook[];
  total_concepts: number;
  total_known: number;
  total_partial: number;
  total_unknown: number;
  learned_concepts: number;
  recommended_minutes: number;
}

export interface BookGapChapter {
  chapter: string;
  known: number;
  partial: number;
  unknown: number;
  historical: number;
}

export interface BookGapDashboard {
  analysis: BookGapAnalysis | null;
  chapters: BookGapChapter[];
  topics: BookGapTopic[];
}
