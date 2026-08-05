import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Grades } from '../pages/Grades';

// Mock the whole API module — the page fetches on mount.
vi.mock('../services/api', () => {
  const grades = [
    { id: 1, course_id: 1, assignment_id: null, title: 'HW 1', points_earned: 48, points_possible: 50, category_id: null, date: null },
    { id: 2, course_id: 1, assignment_id: null, title: 'Midterm', points_earned: 138, points_possible: 150, category_id: null, date: null },
    { id: 3, course_id: 2, assignment_id: null, title: 'Quiz', points_earned: 95, points_possible: 100, category_id: null, date: null },
  ];
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({
        user: { id: 1, name: 'Alex', current_level: 5, total_xp: 2340, current_streak: 3, avatar: null, avatar_class: 'Wizard', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
      }),
      courses: {
        list: vi.fn().mockResolvedValue([
          { id: 1, title: 'Computer Science', status: 'In progress', credits: 3, user_id: 1, image_url: null, current_assignment: 0, total_assignments: 0, next_exam: null, total_exams: 0 },
          { id: 2, title: 'OOP', status: 'In progress', credits: 4, user_id: 1, image_url: null, current_assignment: 0, total_assignments: 0, next_exam: null, total_exams: 0 },
        ]),
        create: vi.fn().mockResolvedValue({}),
      },
      grades: {
        list: vi.fn().mockResolvedValue(grades),
        gpa: vi.fn().mockResolvedValue({
          gpa: 3.7,
          courses: [
            { course_id: 1, title: 'Computer Science', credits: 3, percentage: 93.0, letter_grade: 'A', gpa: 4.0 },
            { course_id: 2, title: 'OOP', credits: 4, percentage: 90.0, letter_grade: 'A-', gpa: 3.7 },
            { course_id: 3, title: 'Algorithms', credits: 3, percentage: null, letter_grade: null, gpa: null },
          ],
        }),
        weights: vi.fn().mockResolvedValue([]),
        neededOnFinal: vi.fn().mockResolvedValue({ needed_pct: 101.7 }),
        create: vi.fn().mockResolvedValue({}),
        createWeight: vi.fn().mockResolvedValue({}),
        deleteWeight: vi.fn().mockResolvedValue({ ok: true }),
      },
    },
  };
});

describe('Grades page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the cumulative GPA and course cards', async () => {
    render(<Grades />);

    await waitFor(() => expect(screen.getByText('3.70')).toBeInTheDocument());

    // Course cards with letters + percentages
    expect(screen.getAllByText('Computer Science').length).toBeGreaterThan(0);
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByText('A-')).toBeInTheDocument();
    expect(screen.getByText(/93% · 3 credits/)).toBeInTheDocument();
    // Ungraded course shows a placeholder
    expect(screen.getAllByText('Algorithms').length).toBeGreaterThan(0);
    expect(screen.getByText(/No grades yet/)).toBeInTheDocument();
  });

  it('shows the grade predictor result', async () => {
    render(<Grades />);
    await waitFor(() => expect(screen.getByText('101.7%')).toBeInTheDocument());
    expect(screen.getByText('Not achievable — aim higher now!')).toBeInTheDocument();
  });

  it('opens the Add Course modal and submits', async () => {
    render(<Grades />);
    await waitFor(() => expect(screen.getByText('3.70')).toBeInTheDocument());

    fireEvent.click(screen.getByText('＋ Add Course'));
    expect(screen.getByText('Add Course', { selector: 'h2' })).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText('e.g. AP Biology');
    fireEvent.change(nameInput, { target: { value: 'Chemistry' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add Course' }));

    await waitFor(() => {
      expect(screen.queryByText('Add Course', { selector: 'h2' })).not.toBeInTheDocument();
    });
  });

  it('opens the weights modal', async () => {
    render(<Grades />);
    await waitFor(() => expect(screen.getByText('3.70')).toBeInTheDocument());

    const weightButtons = screen.getAllByText('⚖ Weights');
    fireEvent.click(weightButtons[0]);

    expect(screen.getByText('Weighted Categories')).toBeInTheDocument();
    expect(screen.getByText(/no weighted categories/i)).toBeInTheDocument();
  });
});
