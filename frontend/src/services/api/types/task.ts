// Task / project / schedule / notification types.
// Extracted from services/api.ts (F8 split).

export interface Task {
  id: number; title: string; subject_tag: string | null;
  priority_tag: string | null; priority_quadrant: string | null;
  due_date: string | null;
  status: string; user_id: number; project_id: number | null;
}

export interface Assignment {
  id: number; title: string; description: string | null;
  course_id: number; due_date: string; status: string;
  type?: string | null;
  type_color?: string | null;
  time_estimate?: number | null;
  file_url?: string | null;
}

export interface Exam {
  id: number; title: string; course_id: number;
  date: string; status: string;
}

export interface Note {
  id: number; title: string; content: string | null;
  course_id: number; created_date: string;
  pinned: boolean;
  updated_at: string | null;
}

export interface Goal {
  id: number; title: string; quarter: string;
  progress_percentage: number; year: number;
  habit_id: number | null; target_date: string | null;
  is_completed: boolean;
  /** Confirmed curriculum subject this goal is linked to (defect #40). */
  subject_id?: number | null;
  roadmap_id?: number | null;
}

export interface Reminder {
  id: number; title: string; time: string | null;
  date: string; is_completed: boolean;
}

export interface Project {
  id: number; user_id: number; name: string;
  description: string | null; status: string; deadline: string | null;
}

export interface ProjectTask {
  id: number; project_id: number; title: string; completed: boolean;
}

export interface ProjectSummary {
  total_tasks: number;
  incomplete_tasks: number;
  days_to_go: number | null;
  deadline_status: string;
}

export interface QuickTask {
  id: number;
  type: 'reminder' | 'task' | 'event';
  title: string;
  time: string | null;
  date: string | null;
  completed: boolean;
}

export interface EisenhowerTask {
  id: number; title: string; subject_tag: string | null;
  priority_tag: string | null; priority_quadrant: string | null;
  due_date: string | null; status: string;
}

export interface EisenhowerMatrix {
  urgent_important: EisenhowerTask[];
  important_not_urgent: EisenhowerTask[];
  urgent_not_important: EisenhowerTask[];
  not_important: EisenhowerTask[];
}

export interface BrainDump {
  id: number;
  user_id: number;
  content: string | null;
  updated_at: string | null;
  // Phase 4 (Idea 40): the draft KbDocument this dump upserts, if any.
  linked_document_id?: number | null;
}

export type DailyCategory = 'School' | 'Study Time' | 'Break';

export type EnergyLevel = 'High' | 'Medium' | 'Low';

export interface DailyScheduleItem {
  id: number;
  date: string;
  time_range: string;
  activity: string;
  category: DailyCategory;
  cat_class: string | null;
  location: string | null;
  energy: EnergyLevel;
  e_class: string | null;
  notes: string | null;
  done: boolean;
  created_at: string;
}

export interface DailyScheduleStats {
  date: string;
  total: number;
  done: number;
  ratio: number;
}

export interface AppNotification {
  id: number;
  user_id: number;
  kind: string;
  title: string;
  body: string | null;
  ref_type: string | null;
  ref_id: number | null;
  read: boolean;
  created_at: string;
}
