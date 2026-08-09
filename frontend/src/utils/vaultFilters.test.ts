import { describe, expect, it } from 'vitest';
import { today, unrelated, thisWeek, inbox, completed } from './vaultFilters';
import type { Task } from '../services/api';

const d = new Date();
const iso = (x: Date) => x.toISOString().split('T')[0];
const todayD = iso(new Date());
const monday = new Date(d);
monday.setDate(d.getDate() - d.getDay() + (d.getDay() === 0 ? -6 : 1));
// Pick a Mon..Sat day within this week that is NOT today, so the `today`
// filter never accidentally matches the 'this week'/'no project' fixtures
// (the previous Monday+3 choice made the test fail whenever today is Thursday).
const weekDays = [1, 2, 3, 4, 5, 6].map((n) => {
  const x = new Date(monday);
  x.setDate(monday.getDate() + n);
  return x;
});
const wed = weekDays.find((x) => iso(x) !== todayD) ?? weekDays[0];
const nextMon = new Date(monday);
nextMon.setDate(monday.getDate() + 7);

const tasks: Task[] = [
  { id: 1, title: 'due today', due_date: todayD, status: 'Not started', project_id: 1, subject_tag: null, priority_tag: null, priority_quadrant: null, user_id: 1 },
  { id: 2, title: 'this week', due_date: iso(wed), status: 'Not started', project_id: null, subject_tag: null, priority_tag: null, priority_quadrant: null, user_id: 1 },
  { id: 3, title: 'inbox no date', due_date: null, status: 'Not started', project_id: null, subject_tag: null, priority_tag: null, priority_quadrant: null, user_id: 1 },
  { id: 4, title: 'no project', due_date: iso(wed), status: 'Not started', project_id: null, subject_tag: null, priority_tag: null, priority_quadrant: null, user_id: 1 },
  { id: 5, title: 'done', due_date: todayD, status: 'Completed', project_id: null, subject_tag: null, priority_tag: null, priority_quadrant: null, user_id: 1 },
  { id: 6, title: 'next week', due_date: iso(nextMon), status: 'Not started', project_id: null, subject_tag: null, priority_tag: null, priority_quadrant: null, user_id: 1 },
];

describe('vaultFilters', () => {
  it('today: only not-completed tasks due today', () => {
    const r = today(tasks).map((t) => t.title);
    expect(r).toEqual(['due today']);
  });

  it('unrelated: only tasks with no project', () => {
    const r = unrelated(tasks).map((t) => t.title);
    expect(r).toContain('this week');
    expect(r).toContain('no project');
    expect(r).not.toContain('due today');
    expect(r).not.toContain('done');
  });

  it('thisWeek: tasks due within Mon..Sun, not completed', () => {
    const r = thisWeek(tasks).map((t) => t.title);
    expect(r).toContain('this week');
    expect(r).not.toContain('next week');
    expect(r).not.toContain('done');
  });

  it('inbox: only tasks with no due date', () => {
    expect(inbox(tasks).map((t) => t.title)).toEqual(['inbox no date']);
  });

  it('completed: only completed tasks', () => {
    expect(completed(tasks).map((t) => t.title)).toEqual(['done']);
  });
});
