// Study plan types.
// Extracted from services/api.ts (F8 split).

// ----- Study plans types (99-phase plan, Groups 6-7) -----
export interface StudyPlanWeek {
  week: number;
  topic: string;
  tasks: string[];
}

export interface StudyPlan {
  id: number;
  subject: string;
  exam_date: string | null;
  weeks: StudyPlanWeek[];
  created_at: string | null;
}
