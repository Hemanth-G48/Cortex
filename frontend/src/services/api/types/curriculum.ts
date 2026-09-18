// SyllabusAI curriculum catalog types.
// Extracted from services/api.ts (F8 split).

// ----- SyllabusAI curriculum types -----
export interface Institution {
  id: number;
  name: string;
  short_name: string;
  description: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface Program {
  id: number;
  institution_id: number;
  name: string;
  code: string;
  description: string | null;
  duration: number;
  is_active: boolean;
  created_at?: string | null;
}

export interface Subject {
  id: number;
  program_id: number;
  name: string;
  code: string;
  semester: number | null;
  /** Display label resolved by the backend (defect #9) — render verbatim. */
  semester_label?: string | null;
  credits: number;
  description: string | null;
  is_active: boolean;
  unit_count: number;
  created_at?: string | null;
}

export interface CurriculumUnit {
  id: number;
  subject_id: number;
  unit_number: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at?: string | null;
}
