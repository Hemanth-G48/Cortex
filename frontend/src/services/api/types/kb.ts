// Second Brain / Knowledge Base types (Phases 1-10).
// Extracted from services/api.ts (F8 split).

// ----- Second Brain / Knowledge Base types (Phase 1) -----
export type KbSourceType = 'vault_folder' | 'local_dir' | 'upload' | 'cloud';

export type KbSyncType = 'none' | 'git' | 'drive' | 'clip' | 'local';

export interface KbSource {
  id: number;
  user_id: number;
  name: string;
  source_type: KbSourceType;
  root_path: string | null;
  enabled: boolean;
  last_scanned_at: string | null;
  files_seen: number;
  files_added: number;
  files_changed: number;
  files_removed: number;
  created_at: string | null;
  document_count: number;
  // Phase 9 (Idea 89): external sync adapter + per-source cursor.
  sync_type: KbSyncType;
  sync_cursor: Record<string, unknown> | null;
  // "local" adapter (Copy Recent Notes): external vault dir mirrored into
  // the source's knowledge root (second_brain/notes).
  sync_source_path: string | null;
}

export type KbDocumentStatus = 'new' | 'changed' | 'unchanged' | 'deleted' | 'failed' | 'draft';

export interface KbDocument {
  id: number;
  user_id: number;
  source_id: number | null;
  path_rel: string | null;
  title: string | null;
  doc_type: string;
  content_hash: string | null;
  char_count: number;
  frontmatter: Record<string, unknown> | null;
  outline: { level: number; text: string; char_start: number }[] | null;
  metadata: {
    wikilinks?: string[];
    tags?: string[];
    callouts?: string[];
    arxiv_id?: string;
    authors?: string[];
    abstract?: string;
  } | null;
  ocr_used: boolean;
  needs_ocr: boolean;
  status: KbDocumentStatus;
  doc_date: string | null;
  // Phase 2 metadata fields (Idea 13)
  author: string | null;
  source_url: string | null;
  language: string | null;
  reading_time_seconds: number | null;
  // Phase 2 dirty flags (Idea 20)
  embedding_dirty: boolean;
  graph_dirty: boolean;
  tags_dirty: boolean;
  // Phase 4 note-quality cache (Idea 39)
  quality_score: number | null;
  quality_detail: Record<string, unknown> | null;
  // Phase 9 (Idea 86): summary stale flag consumed by the nightly job.
  summary_dirty: boolean;
  created_at: string | null;
  updated_at: string | null;
  indexed_at: string | null;
  chunk_count: number;
}

export interface KbChunk {
  id: number;
  document_id: number;
  seq: number;
  content: string;
  char_start: number;
  char_end: number;
  heading_path: string | null;
  token_estimate: number;
}

export type KbJobStatus = 'queued' | 'running' | 'done' | 'failed' | 'interrupted';

export interface KbJob {
  id: number;
  user_id: number;
  job_type: string;
  status: KbJobStatus;
  total_items: number;
  processed_items: number;
  error: string | null;
  ref_type: string | null;
  ref_id: number | null;
  created_at: string | null;
  finished_at: string | null;
  summary: Record<string, number> | null;
}

export interface KbScanResult {
  job: KbJob;
  summary: Record<string, number> | null;
}

// Vault mastery read model (audit defects #40, #71, #76, #82, #96).
// GET /api/kb/mastery — scores derived from LearningEvent practice logs.
export interface KbMasteryTopic {
  topic_id: number;
  name: string;
  score: number;
  score_pct: number;
  classification: string;
  evidence: number;
}

export interface KbMastery {
  subject_id: number | null;
  subject_name: string | null;
  topics_total: number;
  topics_mastered: number;
  topics_weak: number;
  topics_unknown: number;
  avg_score: number;
  score_pct: number;
  classification: string;
  coverage_pct: number;
  hours_logged: number;
  evidence_events: number;
  events: Record<string, number>;
  trend: { date: string; score: number; score_pct: number }[];
  topics: KbMasteryTopic[];
}

// Flat vault-domain list for non-study surfaces (audit defect #83).
// GET /api/kb/domains — top-level KbFolder rows with live doc_count.
export interface KbDomainSummary {
  id: number;
  name: string;
  path: string;
  depth: number;
  doc_count: number;
  description: string | null;
  status: string | null;
  color: string | null;
  created_at: string | null;
  updated_at: string | null;
  course_id: number | null;
}

export interface KbDomainsResponse {
  domains: KbDomainSummary[];
  total_documents: number;
}

// Auto-detected course subjects from the vault (audit defect #27).
// GET /api/kb/auto-subjects/preview — no tags are written by this call.
export interface KbAutoSubjectPreview {
  sample_size: number;
  documents_with_subjects: number;
  subjects_detected: number;
  top_subjects: [string, number][];
  samples: { id: number; title: string; subjects: string[] }[];
}

// POST /api/kb/auto-subjects/detect — analyzes and tags documents.
export interface KbAutoSubjectDetectResult {
  total_documents: number;
  tagged: number;
  skipped_already_tagged: number;
  subjects_detected: number;
  top_subjects: [string, number][];
  dry_run: boolean;
}

// Result of appending a line to today's daily-life note (defects #52, #66).
// ``ok: false`` + ``reason`` when no daily-life folder is reachable.
export interface DailyNoteWriteResult {
  ok: boolean;
  reason: string | null;
  date: string | null;
  path: string | null;
  created: boolean;
}

// Pre-flight check for a candidate source root (audit defect #20).
// GET /api/kb/sources/validate?path= — mirrors what the scanner would index.
export interface KbSourcePathValidation {
  path: string;
  absolute_path: string | null;
  valid: boolean;
  reason: string | null;
  exists: boolean;
  is_dir: boolean;
  readable: boolean;
  writable: boolean;
  markdown_count: number;
  document_count: number;
  sample_files: string[];
  already_registered: { id: number; name: string } | null;
  inside_source: { id: number; name: string; root_path: string | null } | null;
}

export interface KbDocumentListResponse {
  items: KbDocument[];
  total: number;
  page: number;
  page_size: number;
}

export interface KbUploadResult {
  document: KbDocument | null;
  deduped: boolean;
  duplicate_of_id: number | null;
}

export interface KbVersion {
  id: number;
  document_id: number;
  version_seq: number;
  content_hash: string | null;
  snapshot_text: string | null;
  created_at: string | null;
}

export interface KbDiffResponse {
  from_version: number;
  to_version: number;
  changed: boolean;
  diff: string;
}

// ----- Second Brain Phase 2 types (Embeddings, Indexing & Knowledge Graph) -----
export interface KbStats {
  document_count: number;
  chunk_count: number;
  embedding_count: number;
  embedded_documents: number;
  tag_count: number;
  concept_count: number;
  edge_count: number;
  duplicate_count: number;
  total_tokens: number;
  embeddings_today: number;
  embeddings_limit: number;
  inferences_today: number;
  inference_limit: number;
  dirty_documents: number;
  // Audit defect #67: the vault's activity window (first/last indexed note).
  oldest_document_date?: string | null;
  newest_document_date?: string | null;
}

export interface KbRelatedItem {
  id: number;
  title: string;
  relation: string | null;
  weight: number | null;
  provenance?: string | null;
  direction?: string | null;
}

export interface KbRelatedResponse {
  document_id: number;
  related: KbRelatedItem[];
  method: string;
}

export interface KbTagSuggestion {
  tag_id: number;
  name: string;
  provenance: string;
  confidence: number;
}

export interface KbDocumentTagsResponse {
  document_id: number;
  tags: KbTagSuggestion[];
  // Rule + manual tags already linked to the document (applied chips).
  applied?: KbTagSuggestion[];
}

export interface KbConcept {
  id: number;
  canonical_name: string;
  definition: string | null;
  aliases: string[] | null;
  document_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface KbDuplicateItem {
  document_id: number;
  duplicate_of_id: number;
  similarity: number;
  method: string;
  created_at: string | null;
}

export interface KbDuplicatesResponse {
  items: KbDuplicateItem[];
  total: number;
  method: string;
}

export interface KbMetadataUpdate {
  author?: string | null;
  source_url?: string | null;
  language?: string | null;
  reading_time_seconds?: number | null;
  metadata?: Record<string, unknown> | null;
}

// ----- Knowledge Graph types (Group 8, Phase 2) -----
export type KbGraphNodeKind = 'document' | 'concept' | 'tag';

export interface KbGraphNode {
  id: string;
  kind: KbGraphNodeKind;
  label: string;
  doc_type?: string | null;
  status?: string | null;
  degree: number;
}

export interface KbGraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
  provenance: string;
}

export interface KbGraphResponse {
  nodes: KbGraphNode[];
  edges: KbGraphEdge[];
  truncated: boolean;
  total_nodes: number;
  total_edges: number;
}

// ----- Second Brain Phase 3 types (Search & Retrieval, Ideas 21-30) -----
export type KbSearchMode = 'keyword' | 'semantic' | 'hybrid';

export interface KbSearchItem {
  chunk_id: number;
  document_id: number;
  seq: number;
  title: string;
  snippet: string;
  score: number;
  mode: string;
  source_path: string | null;
  heading_path: string | null;
  doc_type: string;
  doc_date: string | null;
  char_start: number;
  char_end: number;
  sources: string[] | null;
}

export interface KbSearchResponse {
  items: KbSearchItem[];
  total: number;
  page: number;
  page_size: number;
  mode: string;
  original_query: string;
  expanded_query: string;
}

export interface KbSearchEventItem {
  id: number;
  query: string;
  mode: string;
  clicked_id: number | null;
  rating: number | null;
  created_at: string | null;
}

export interface KbHealth {
  score: number;
  document_count: number;
  edge_count: number;
  signals: {
    orphans: { count: number; document_ids: number[] };
    dead_links: {
      count: number;
      edges: {
        edge_id: number;
        source_document_id: number | null;
        target_document_id: number | null;
        relation: string;
      }[];
    };
    stale_notes: { count: number; document_ids: number[] };
    unindexed_files: {
      count: number;
      documents: { document_id: number; missing: string[] }[];
    };
    coverage_gaps: { topic: string; covered: number; coverage: number }[];
    // Phase 4 (Idea 39, phrase 90)
    avg_quality?: { average: number; weight: number };
  };
}

export interface KbGapItem {
  topic: string;
  coverage: number;
  is_gap: boolean;
}

export interface KbGapsResponse {
  items: KbGapItem[];
  gaps: KbGapItem[];
  threshold: number;
  total: number;
}

// ----- Second Brain Phase 4 types (Note Intelligence & Content Generation, Ideas 31-40) -----
export interface KbSummaryResponse {
  document_id: number;
  cached: boolean;
  summary: {
    content: string;
    key_points: string[];
    definitions: { term: string; definition: string }[];
    open_questions: string[];
  };
}

export interface KbExplainCitation {
  chunk_id: number;
  document_id: number | null;
  title: string | null;
  snippet: string;
  source_path: string | null;
  heading_path: string | null;
}

export interface KbExplainResponse {
  concept: string;
  depth: string;
  explanation: string;
  citations: KbExplainCitation[];
  fallback: boolean;
  document_ids: number[];
}

export interface KbFlashcardCandidate {
  id: number;
  document_id: number;
  document_title?: string;
  question: string;
  answer: string;
  source_chunk_id: number | null;
  status: string;
  // Phase 9 (Idea 85): manual | auto
  source?: string;
  created_at?: string | null;
}

export interface KbFlashcardGenerateResult {
  document_id: number;
  generated: number;
  skipped_duplicates: number;
  fallback: boolean;
  candidates: KbFlashcardCandidate[];
}

export interface KbCitation {
  id: number;
  document_id: number | null;
  cite_key: string;
  title: string | null;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  arxiv_id: string | null;
  raw_text: string | null;
  created_at?: string | null;
}

export interface KbMindMapNode {
  id: string;
  label: string;
  children: KbMindMapNode[];
  concepts: string[];
  chunk_ids: number[];
}

export interface KbDailyNoteDoc {
  id: number;
  title: string;
  doc_type: string;
  char_count: number;
  reading_time_seconds: number | null;
  quality_score: number | null;
}

export interface KbDailyNoteSchedule {
  id: number;
  time_range: string;
  activity: string;
  category: string;
  done: boolean;
}

export interface KbDailyNoteJournal {
  id: number;
  mood: string | null;
  content: string;
  tags: string | null;
}

export interface KbDailyNotes {
  date: string;
  documents: KbDailyNoteDoc[];
  schedule: KbDailyNoteSchedule[];
  journal: KbDailyNoteJournal[];
}

export interface KbQualitySuggestion {
  id: number;
  action: string;
  detail: string | null;
  status: string;
}

export interface KbQualityResult {
  document_id: number;
  score: number;
  components: Record<string, number>;
  weights: Record<string, number>;
  computed_at?: string;
  suggestions: KbQualitySuggestion[];
}

export interface KbQualityItem {
  document_id: number;
  title: string;
  doc_type: string;
  score: number;
  components: Record<string, number>;
  suggestions: number;
}

export interface KbLinksResponse {
  document_id: number;
  concepts: { concept_id: number; edge_id?: number; name: string; weight: number }[];
  related: { id: number; edge_id?: number; title: string; relation: string; weight: number }[];
}

export interface GlobalSearchHit {
  id: number;
  title: string;
  domain: string;
  snippet: string;
  url: string;
  score: number;
}

export interface GlobalSearchResponse {
  items: GlobalSearchHit[];
  groups: Record<string, GlobalSearchHit[]>;
  total: number;
  query: string;
  domains: string[];
}

export interface KbMemoryItem {
  concept_id: number;
  concept: string;
  strength: number;
  exposure_count: number;
  last_seen: string | null;
  source: string;
}

export interface KbRecommendItem {
  topic_id: number;
  topic_name: string;
  subject_id: number;
  score: number;
  ready: boolean;
  blocked_by: number[];
  session_length_mins: number;
  reasons: Record<string, number>;
}

export interface KbConnectSuggestion {
  document_id: number;
  title: string;
  shared_concepts: string[];
  reasons: string[];
  target_status: string;
}

export interface KbConnectSuggestionsResponse {
  items: KbConnectSuggestion[];
  contradiction_hints: number[];
}

export interface KbMissingNoteSuggestion {
  id: number;
  concept_id: number | null;
  concept: string | number;
  reason: string;
  outline: string[];
  linked_material_ids: number[];
  status: 'suggested' | 'accepted' | 'dismissed';
}

export interface KbOutdatedNote {
  id: number;
  document_id: number;
  title: string;
  reason: 'contradiction' | 'stale' | 'material_changed';
  evidence: Record<string, unknown> | null;
  status: 'open' | 'updated' | 'archived' | 'dismissed';
  created_at: string | null;
}

export interface KbPersonalizedExplainResponse extends KbExplainResponse {
  anchors: string[];
  personalized: boolean;
}

export interface KbAdaptation {
  roadmap_id: number | null;
  version: number | null;
  status: string | null;
  topic_ids: number[];
  diff: {
    added_reviews: number;
    added_topic_ids: number[];
    removed_topics: number[];
    removed_topic_ids: number[];
    reordered: number[];
    reason: string;
    reasons: string[];
  };
}

// ----- Second Brain Phase 9 types (Automation, Ideas 81-90) -----
export interface KbAutomationJob {
  name: string;
  enabled: boolean;
  toggle: string;
  cap: number | null;
  budget_kind: string | null;
  description: string;
}

export interface KbAutomationRunResult {
  job?: string;
  job_id?: number;
  status?: string;
  skipped?: boolean;
  reason?: string;
  results?: { job: string; skipped?: boolean; reason?: string }[];
  count?: number;
}

export interface KbSourceSyncResult {
  source_id: number;
  sync_type?: string;
  changes?: number;
  imported?: number;
  unchanged?: number;
  skipped_stale?: number;
  failed?: number;
  skipped?: boolean;
  reason?: string;
  // "local" adapter (Copy Recent Notes) counters.
  copied?: number;
  removed?: number;
  scanned?: Record<string, number | undefined>;
}

export interface KbSourceSyncStatus {
  source_id: number;
  name: string;
  sync_type: string;
  last_scanned_at: string | null;
  cursor: Record<string, unknown>;
}

// ----- Second Brain Phase 10 types (Advanced AI, Analytics & Platform, Ideas 91-100) -----
export interface KbAgentStep {
  agent: string;
  status?: string;
  output?: Record<string, unknown>;
  error?: string | null;
  latency_ms?: number;
}

export interface KbAgentRun {
  id?: number;
  run_id?: number;
  request: string;
  status?: string;
  plan?: { agent: string; inputs: Record<string, unknown>; expected_output?: string; budget?: number }[];
  steps?: KbAgentStep[];
  result?: string | null;
  latency_ms?: number;
  cost_estimate?: number;
  created_at?: string | null;
}

export interface KbMemoryEpisode {
  id: number;
  event_type: string;
  summary: string;
  refs: Record<string, unknown> | null;
  created_at: string | null;
}

export interface KbMemoryTimeline {
  episodes: KbMemoryEpisode[];
  durable_facts: { concept: string; strength: number }[];
  total: number;
}

export interface KbContextBundle {
  active_subject: { subject_id: number | null; subject_name: string | null } | null;
  upcoming_exams: { exam_id: number; title: string; subject_id: number; days_until: number; date: string }[];
  recent_topics: { topic_id: number; topic_name: string; subject_id: number | null }[];
  question_history: { attempts_7d: number; avg_accuracy_7d: number | null };
  session_length_mins: number;
  memory: { concepts_known: number; anchors: number; concept_rows: number };
  override: Record<string, unknown>;
}

export interface KbResearchContribution {
  statement: string;
  novelty?: string;
  limitation?: string;
}

export interface KbRelatedPaper {
  document_id: number;
  title: string | null;
  doc_type: string;
  score: number;
  signals: { shared_concepts: number; title_overlap: number; shared_citations: number };
}

export interface KbResearchExplainResult {
  document_id: number;
  title: string | null;
  summary: { content: string; key_points: string[]; definitions: unknown[]; open_questions: string[] } | null;
  cached?: boolean;
  contributions: KbResearchContribution[];
  related: KbRelatedPaper[];
  synthesis: {
    answer: string;
    faithfulness_score: number;
    ai_used: boolean;
    citations: { chunk_id: number; document_id: number | null; title: string | null; source_path: string | null }[];
    grounded: boolean;
  } | null;
}

export type KbRecommendationDomain = 'study' | 'revisit' | 'read' | 'practice';

export interface KbRecommendationItem {
  id: string;
  domain: KbRecommendationDomain;
  target: number;
  title: string;
  reason: string;
  score: number;
  urgency: number;
  weakness: number;
  readiness: number;
}

export interface KbReflection {
  id: number;
  week_start: string;
  content: string;
  insights: { worked: string[]; struggled: string[]; change: string[]; insights: string[] };
  created_at: string | null;
  pushed?: boolean;
}

export interface KbDerivedGoal {
  subject_id: number;
  title: string;
  quarter: string;
  year: number;
  target_date: string;
  roadmap_id?: number | null;
}

export interface KbGoalItem {
  id: number;
  title: string;
  quarter: string;
  year: number;
  subject_id: number | null;
  roadmap_id: number | null;
  target_date: string | null;
  progress_percentage: number;
  is_completed: boolean;
}

export interface KbForecastPoint {
  date: string;
  value: number;
  events: number;
  ewma?: number;
}

export interface KbForecast {
  subject_id: number;
  points: KbForecastPoint[];
  model: string;
  forecast: number;
  readiness: number;
  at_risk: boolean;
  risk_threshold?: number;
  exam_days_until: number | null;
  series_points: number;
}

export interface KbObservabilityPayload {
  total: number;
  cost_estimate: number;
  tokens: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  feedback: { positive: number; negative: number; neutral: number };
  avg_faithfulness: number | null;
  by_feature: Record<string, { count: number; cost_estimate: number; avg_latency_ms: number; feedback: number }>;
  recent?: { id: number; feature: string; request: string | null; latency_ms: number; feedback: number; created_at: string | null }[];
}

export interface KbPromptVersion {
  id: number;
  feature: string;
  version: number;
  is_active: boolean;
  template: string;
  created_at: string | null;
}
