import type { Task } from '../services/api';

/** Client-side task filters mirroring `GET /vault/tasks?tab=...` (fallback path). */

/** Tasks due today (not completed). */
export function today(tasks: Task[]): Task[] {
  const d = new Date().toISOString().split('T')[0];
  return tasks.filter((t) => t.due_date === d && t.status !== 'Completed');
}

/** Tasks with no linked project (not completed). */
export function unrelated(tasks: Task[]): Task[] {
  return tasks.filter((t) => t.project_id == null && t.status !== 'Completed');
}

/** Tasks due within the current Mon..Sun week (not completed). */
export function thisWeek(tasks: Task[]): Task[] {
  const now = new Date();
  const start = new Date(now);
  start.setDate(now.getDate() - now.getDay() + (now.getDay() === 0 ? -6 : 1)); // Monday
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  const s = start.toISOString().split('T')[0];
  const e = end.toISOString().split('T')[0];
  return tasks.filter((t) => t.due_date && t.due_date >= s && t.due_date <= e && t.status !== 'Completed');
}

/** Tasks with no due date (not completed). */
export function inbox(tasks: Task[]): Task[] {
  return tasks.filter((t) => t.due_date == null && t.status !== 'Completed');
}

/** Completed tasks. */
export function completed(tasks: Task[]): Task[] {
  return tasks.filter((t) => t.status === 'Completed');
}
