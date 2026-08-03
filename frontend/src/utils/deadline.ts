/** Deadline label logic mirroring GET /projects/{id}/summary (Phase 68). */

export interface DeadlineInfo {
  days_to_go: number | null;
  deadline_status: string;
}

/**
 * Compute days-to-go and a human label for a project deadline.
 * Mirrors the backend so client-side cards never need a fetch for the badge.
 */
export function computeDeadline(status: string, deadline: string | null): DeadlineInfo {
  if (status === 'Completed') return { days_to_go: null, deadline_status: 'Completed' };

  if (!deadline) return { days_to_go: null, deadline_status: 'No deadline' };

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${deadline}T00:00:00`);
  const days_to_go = Math.round((target.getTime() - today.getTime()) / 86_400_000);

  if (days_to_go < 0) return { days_to_go, deadline_status: 'Overdue' };
  if (days_to_go <= 7) return { days_to_go, deadline_status: '7 Days to go' };
  return { days_to_go, deadline_status: `${days_to_go} Days to go` };
}
