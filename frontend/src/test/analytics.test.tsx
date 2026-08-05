import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Analytics } from '../pages/Analytics';

vi.mock('../services/api', () => {
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({
        user: { id: 1, name: 'Alex', current_level: 5, total_xp: 2340, current_streak: 3, avatar: null, avatar_class: 'Wizard', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
      }),
      analytics: {
        summary: vi.fn().mockResolvedValue({
          total_focus_minutes: 3250,
          weekly_focus_minutes: 260,
          completed_assignments: 8,
          total_assignments: 12,
          completion_rate: 66.7,
          gpa: 3.5,
          total_xp: 2340,
          level: 5,
          current_streak: 3,
        }),
        weeklyFocus: vi.fn().mockResolvedValue([
          { week: '2026-07-01', label: '2026-07-01', minutes: 120 },
          { week: '2026-07-08', label: '2026-07-08', minutes: 240 },
          { week: '2026-07-15', label: '2026-07-15', minutes: 0 },
          { week: '2026-07-22', label: '2026-07-22', minutes: 90 },
        ]),
        heatmap: vi.fn().mockResolvedValue(
          Array.from({ length: 52 * 7 }, (_, i) => ({
            date: `2026-07-${String((i % 28) + 1).padStart(2, '0')}`,
            minutes: i % 3 === 0 ? 30 : 0,
          })),
        ),
      },
      grades: {
        gpa: vi.fn().mockResolvedValue({
          gpa: 3.5,
          courses: [{ course_id: 1, title: 'Computer Science', credits: 3, percentage: 93.0, letter_grade: 'A', gpa: 4.0 }],
        }),
        list: vi.fn().mockResolvedValue([
          { id: 1, course_id: 1, assignment_id: null, title: 'HW', points_earned: 48, points_possible: 50, category_id: null, date: null },
        ]),
      },
    },
  };
});

describe('Analytics page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders stat cards from the summary', async () => {
    render(<Analytics />);
    await waitFor(() => expect(screen.getByText('54h 10m')).toBeInTheDocument());
    expect(screen.getByText(/This Week/)).toBeInTheDocument();
    expect(screen.getByText('66.7%')).toBeInTheDocument();
    expect(screen.getByText('3.50')).toBeInTheDocument();
    expect(screen.getByText('Lv.5')).toBeInTheDocument();
    expect(screen.getByText('3d')).toBeInTheDocument();
  });

  it('renders weekly bars and the heatmap sections', async () => {
    render(<Analytics />);
    await waitFor(() => expect(screen.getByText('📊 Weekly Focus')).toBeInTheDocument());
    expect(screen.getByText('🔥 Focus Heatmap (last 52 weeks)')).toBeInTheDocument();
    expect(screen.getByText('📈 Grade Trend')).toBeInTheDocument();
  });
});
