import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SyllabusImport } from '../pages/SyllabusImport';

vi.mock('../services/api', () => {
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({
        user: { id: 1, name: 'Alex', current_level: 5, total_xp: 2340, current_streak: 3, avatar: null, avatar_class: 'Wizard', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
      }),
      courses: {
        list: vi.fn().mockResolvedValue([
          { id: 1, title: 'English 101', credits: 3, user_id: 1, image_url: null, current_assignment: 0, total_assignments: 0, next_exam: null, total_exams: 0, status: 'In progress' },
        ]),
      },
      assignments: {
        list: vi.fn().mockResolvedValue([]),
        create: vi.fn().mockResolvedValue({}),
      },
      ai: {
        syllabus: vi.fn().mockResolvedValue({
          assignments: [
            { title: 'Essay 1: Personal Narrative', due_date: '2026-02-14', course: 'English 101', priority: 'high' },
            { title: 'Midterm Exam', due_date: '2026-03-10', course: 'English 101', priority: 'high' },
          ],
          ai_used: false,
        }),
      },
    },
  };
});

describe('SyllabusImport page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('extracts assignments from pasted text', async () => {
    render(<SyllabusImport />);
    const textarea = screen.getByPlaceholderText('Paste your syllabus text here...');
    fireEvent.change(textarea, { target: { value: 'English 101 syllabus with an essay due in February.' } });
    fireEvent.click(screen.getByText('✨ Extract Assignments'));

    await waitFor(() => expect(screen.getByText('Found 2 assignments')).toBeInTheDocument());
    expect(screen.getByText('Essay 1: Personal Narrative')).toBeInTheDocument();
    expect(screen.getByText('Midterm Exam')).toBeInTheDocument();
  });

  it('imports all extracted assignments', async () => {
    render(<SyllabusImport />);
    const textarea = screen.getByPlaceholderText('Paste your syllabus text here...');
    fireEvent.change(textarea, { target: { value: 'Some syllabus text.' } });
    fireEvent.click(screen.getByText('✨ Extract Assignments'));

    await waitFor(() => expect(screen.getByText('Found 2 assignments')).toBeInTheDocument());
    fireEvent.click(screen.getByText('＋ Add All to Assignments'));
    await waitFor(() => expect(screen.getByText('✅ Imported!')).toBeInTheDocument());
  });
});
