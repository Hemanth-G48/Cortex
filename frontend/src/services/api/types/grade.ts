// Grade / GPA calculator types.
// Extracted from services/api.ts (F8 split).

// ----- Grades types (99-phase plan, Groups 2-3) -----
export interface Grade {
  id: number;
  course_id: number;
  assignment_id: number | null;
  title: string;
  points_earned: number;
  points_possible: number;
  category_id: number | null;
  date: string | null;
}

export interface CourseWeight {
  id: number;
  course_id: number;
  name: string;
  weight: number;
}

export interface GradeCalculateResult {
  course_id: number;
  percentage: number | null;
  letter_grade: string | null;
  is_weighted: boolean;
  total_earned: number | null;
  total_possible: number | null;
  grade_count: number;
}

export interface GPACourse {
  course_id: number;
  title: string;
  credits: number;
  percentage: number | null;
  letter_grade: string | null;
  gpa: number | null;
}

export interface GPAResponse {
  gpa: number | null;
  courses: GPACourse[];
}

export interface NeededOnFinalResponse {
  needed_pct: number;
}
