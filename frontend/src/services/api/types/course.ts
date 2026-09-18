// Course / Subject Details page types (Second Brain + Classroom).
// Extracted from services/api.ts (F8 split).

import type { GapAnalysisResponse, GapCoverage, GapItem, GapPathPhase } from './gap'
import type { KbGraphResponse } from './kb'
import type { KbConceptGap } from './subject'

export interface Course {
  id: number; title: string; image_url: string | null;
  current_assignment: number; total_assignments: number;
  next_exam: number | null; total_exams: number;
  status: string; user_id: number;
  credits: number;
  progress_percentage?: number;
  kb_document_count?: number;
  // SyllabusAI G12 (Phase 78): optional link to a catalog subject.
  curriculum_subject_id?: number | null;
  // Origin of the row: manual | classroom | kb_tag | kb_folder.
  source_type?: string | null;
  kb_tag_id?: number | null;
  // Set when derived from a top-level vault folder (source + folder path).
  kb_source_id?: number | null;
  kb_folder_path?: string | null;
  // Folder-derived subjects: metadata read from the folder's index.md
  // frontmatter (description / status / color keys).
  description?: string | null;
  color?: string | null;
  google_id?: string | null;
  classroom_url?: string | null;
}

export interface CourseDocument {
  id: number;
  title: string;
  doc_type: string;
  path_rel: string | null;
  char_count: number;
  outline: { level: number; text: string; char_start: number }[] | null;
  tags: string[] | null;
  wikilinks: string[] | null;
  quality_score: number | null;
  reading_time_seconds: number | null;
  author: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CourseSyncResult {
  created: number;
  updated: number;
  removed: number;
  courses: number;
  // Always returned by the backend derivation summary.
  sources: number;
  documents: number;
  course_tags: number;
  course_folders: number;
  errors: string[];
  synced_at: string;
}

export interface CourseSyncLog {
  created: number;
  updated: number;
  removed: number;
  courses: number;
  sources: number;
  documents: number;
  course_tags: number;
  course_folders: number;
  errors: string[];
  synced_at: string | null;
}

export interface CourseSyncStatus {
  sources: number;
  documents: number;
  course_tags: number;
  course_folders: number;
  last_sync: CourseSyncLog | null;
  google: { configured: boolean; connected: boolean; email: string | null };
}

/** One nested topic/subtopic with the documents that contain its heading. */
export interface CourseTopicNode {
  id: string;
  name: string;
  level: number;
  // folder → this topic is a vault folder under the subject (folder-derived
  // subjects only; the UI shows a folder icon + path breadcrumb); heading →
  // built from document headings. Absent on older payloads → treat as heading.
  origin?: 'folder' | 'heading';
  documents: CourseDocument[];
  children: CourseTopicNode[];
}

/** A concept mentioned by the subject's documents (related concepts). */
export interface CourseConcept {
  concept_id: number;
  name: string;
  definition: string | null;
  mentions: number;
  document_count: number;
  sources: { document_id: number; title: string }[];
}

/** A Classroom-sourced assignment for this course. */
export interface CourseClassroomAssignment {
  id: number;
  title: string;
  description: string | null;
  status: string;
  due_date: string | null;
}

/** One canonical folder/domain under a course (Second Brain folder hierarchy). */
export interface KbDomainNode {
  id: number;
  name: string;
  path: string;
  depth: number;
  doc_count: number;
  description: string | null;
  status: string | null;
  color: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  // Present on tree payloads (domain page / course domains grid).
  children?: KbDomainNode[];
}

export interface KbDomainListResponse {
  items: KbDomainNode[];
}

export interface KbDomainDetail {
  id: number;
  name: string;
  path: string;
  depth: number;
  doc_count: number;
  description: string | null;
  status: string | null;
  color: string | null;
  course: { id: number; title: string } | null;
  breadcrumb: { id: number | null; name: string; path: string }[];
  documents: {
    id: number;
    title: string;
    doc_type: string;
    path_rel: string | null;
    char_count: number;
    quality_score: number | null;
    reading_time_seconds: number | null;
    author: string | null;
    created_at: string | null;
    updated_at: string | null;
  }[];
  subfolders: KbDomainNode[];
}

/** Domain-scoped gap analysis — same actionable engine shape as course gaps. */
export interface KbDomainGapsResponse {
  summary?: GapAnalysisResponse['summary'] | null;
  strengths?: GapItem[];
  gaps?: GapItem[];
  path?: GapPathPhase[];
  next?: GapItem | null;
  domain?: string | null;
  coverage?: GapCoverage;
  document_count: number;
  folder: { id: number; name: string; path: string };
  // Saved-analysis metadata: cached=true means reused, not recomputed.
  cached?: boolean;
  analyzed_at?: string | null;
  new_notes_since_analysis?: number;
}

export interface CourseContentResponse {
  course: Course;
  second_brain: {
    documents: CourseDocument[];
    topics: CourseTopicNode[];
    // Canonical folder-derived domains (the Second Brain hierarchy).
    domains?: KbDomainNode[];
    unorganized_documents: CourseDocument[];
    concepts: CourseConcept[];
    graph: KbGraphResponse;
    document_count: number;
  };
  classroom: {
    linked: boolean;
    google_id: string | null;
    course_url: string | null;
    assignments: CourseClassroomAssignment[];
    total_assignments: number;
  };
}

/** Topic coverage gap reported by the subject gap analysis. */
export interface CourseTopicGap {
  topic: string;
  normalized: string;
  coverage: number;
  documents: number;
  is_gap: boolean;
}

export interface CourseGapsResponse {
  topics: CourseTopicGap[];
  concepts: KbConceptGap[];
  classroom: { assignments: CourseClassroomAssignment[]; total: number; pending: number };
  threshold: number;
  document_count: number;
  // Redesigned actionable gap engine (absent only on legacy backends).
  summary?: GapAnalysisResponse['summary'] | null;
  strengths?: GapItem[];
  gaps?: GapItem[];
  path?: GapPathPhase[];
  next?: GapItem | null;
  domain?: string | null;
  coverage?: GapCoverage;
  // Saved-analysis metadata: cached=true means this is the previously stored
  // result (reused, not recomputed); analyzed_at is when it was computed.
  cached?: boolean;
  analyzed_at?: string | null;
  // Staleness: how many Second Brain documents were added since this analysis
  // was computed (present on cached loads; 0 when nothing changed since).
  new_notes_since_analysis?: number;
}

export interface CourseResyncResult {
  kb: CourseSyncResult;
  classroom: {
    courses?: number;
    assignments?: number;
    source?: string;
    warning?: string;
    error?: string;
  } | null;
  course_removed?: boolean;
  content: CourseContentResponse | null;
}

export interface AcademicResource {
  id: string;
  title: string;
  type: string;
  /** Authoritative document type from the vault (defect #26) — drives the icon. */
  doc_type?: string | null;
  url: string | null;
  description: string | null;
}
