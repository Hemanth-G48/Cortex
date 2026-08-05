import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Teacher } from '../pages/Teacher';

vi.mock('../services/api', () => ({
  teacherApi: {
    students: vi.fn().mockResolvedValue([
      {
        id: 1,
        name: 'Alice Johnson',
        stats: { courses: 3, assignments: 5, todos: 2, books: 1, braindump: true },
      },
      {
        id: 2,
        name: 'Bob Smith',
        stats: { courses: 2, assignments: 3, todos: 4, books: 0, braindump: false },
      },
    ]),
  },
  endpoints: {
    login: vi.fn().mockResolvedValue({
      user: { id: 1, name: 'Teacher', current_level: 10, total_xp: 5000, current_streak: 7, avatar: null, avatar_class: 'Professor', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null, role: 'teacher', token: 'fake' },
    }),
  },
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ role: 'teacher', isAuthenticated: true, loading: false }),
}));

vi.mock('../hooks/useToast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

describe('Teacher page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders student names', async () => {
    render(<Teacher />);

    await waitFor(() => {
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
      expect(screen.getByText('Bob Smith')).toBeInTheDocument();
    });
  });

  it('renders the header', async () => {
    render(<Teacher />);

    await waitFor(() => {
      expect(screen.getByText('Teacher Dashboard')).toBeInTheDocument();
    });
  });
});
