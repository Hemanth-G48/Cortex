import { describe, expect, it } from 'vitest';
import { computeDeadline } from './deadline';

// Local-time ISO date (toISOString() is UTC and shifts the day when the clock
// is early, making the far-future expectation flaky). Matches how the app
// serializes dates via toIso() in utils/vaultDates.ts.
const isoDays = (offset: number): string => {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

describe('computeDeadline', () => {
  it('completed project → Completed', () => {
    expect(computeDeadline('Completed', isoDays(-5)).deadline_status).toBe('Completed');
  });

  it('no deadline → No deadline', () => {
    expect(computeDeadline('Not started', null).deadline_status).toBe('No deadline');
  });

  it('past deadline → Overdue', () => {
    const r = computeDeadline('Not started', isoDays(-2));
    expect(r.deadline_status).toBe('Overdue');
    expect(r.days_to_go).toBeLessThan(0);
  });

  it('deadline within 7 days → 7 Days to go', () => {
    expect(computeDeadline('Not started', isoDays(3)).deadline_status).toBe('7 Days to go');
  });

  it('deadline far future → "N Days to go"', () => {
    expect(computeDeadline('Not started', isoDays(20)).deadline_status).toBe('20 Days to go');
  });
});
