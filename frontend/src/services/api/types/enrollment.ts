// Enrollment types.
// Extracted from services/api.ts (F8 split).

import type { CurriculumUnit, Subject } from './curriculum'

// ----- SyllabusAI enrollment -----
export interface EnrollmentSummary {
  institution_id: number | null;
  program_id: number | null;
  institution_name: string | null;
  program_name: string | null;
  subjects: Subject[];
  units: CurriculumUnit[];
  material_count: number;
  quiz_attempts: number;
  avg_quiz_percentage: number | null;
  uploaded_materials: number;
}
