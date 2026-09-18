// Actionable gap-analysis engine types.
// Extracted from services/api.ts (F8 split).

export type GapLevel = 'Mastered' | 'Strong' | 'Familiar' | 'Weak' | 'Not Found' | 'Prerequisite Missing';

export type GapPriority = 'High' | 'Medium' | 'Low';

export interface GapPrerequisite {
  name: string;
  level: GapLevel;
  known: boolean;
}

/** One actionable strength or gap entry produced by the gap engine. */
export interface GapItem {
  name: string;
  level: GapLevel;
  skill: string | null;
  domain: string | null;
  importance: number;
  priority?: GapPriority | null;
  why: string | null;
  prerequisites: GapPrerequisite[];
  blocked: boolean;
  learn: string[];
  practice: string[];
  next: string | null;
  sources: { document_id: number; title: string }[];
  related_known: string[];
  evidence: {
    strength: number;
    exposure: number;
    mentions: number;
    documents: number;
    quiz_errors: number;
    retrieval_misses: number;
  };
}

export interface GapPathItem {
  name: string;
  level: GapLevel;
  priority: GapPriority | null;
  // Real Second Brain documents linked to this gap — deep-linkable from the path.
  sources?: { document_id: number; title: string }[];
}

export interface GapPathPhase {
  phase: number;
  title: string;
  items: GapPathItem[];
}

export interface GapCoverage {
  known: number;
  gaps: number;
  total: number;
  percent: number;
}

export interface GapAnalysisResponse {
  goal: string | null;
  goal_key?: string | null;
  domain: string | null;
  summary: { text: string; priorities: string[]; strong_areas: string[] };
  strengths: GapItem[];
  gaps: GapItem[];
  path: GapPathPhase[];
  next: GapItem | null;
  coverage: GapCoverage;
  domain_breakdown?: {
    domain: string;
    total: number;
    strong: string[];
    developing: string[];
    gaps: string[];
    status: string;
    strong_ratio: number;
    gap_ratio: number;
  }[];
  // Saved-analysis metadata: cached=true means this is the previously stored
  // result (reused, not recomputed); analyzed_at is when it was computed.
  cached?: boolean;
  analyzed_at?: string | null;
  // Staleness: how many Second Brain documents were added since this analysis
  // was computed (present on cached loads; 0 when nothing changed since).
  new_notes_since_analysis?: number;
}

export interface GapGoalInfo {
  key: string;
  title: string;
  description: string;
  domains: string[];
}

/** One historical snapshot of a subject's or goal's gap analysis. */
export interface GapHistorySnapshot {
  analyzed_at: string | null;
  document_count?: number | null;
  gap_count: number;
  strength_count: number;
  coverage: GapCoverage | null;
  next: string | null;
  gaps: {
    name: string;
    level: GapLevel | null;
    priority?: GapPriority | null;
    domain?: string | null;
  }[];
  strengths: { name: string; level: GapLevel | null }[];
}

export interface GapHistoryResponse {
  history: GapHistorySnapshot[];
}
