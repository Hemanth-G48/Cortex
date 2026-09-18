// SyllabusAI summary types.
// Extracted from services/api.ts (F8 split).

// ----- SyllabusAI summaries -----
export interface Summary {
  id: number;
  unit_ids: number[];
  content: string;
  key_points: string[];
  created_at?: string | null;
}

export interface SummaryGenerateResponse {
  summary: { content: string; key_points: string[] };
  cached: boolean;
}
