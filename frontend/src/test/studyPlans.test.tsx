import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { StudyPlans } from '../pages/StudyPlans';

vi.mock('../services/api', () => {
  const saved = [
    {
      id: 1,
      subject: 'Biology Final',
      exam_date: null,
      weeks: [
        { week: 1, topic: 'Cell Biology', tasks: ['Read Ch 1-2', 'Make flashcards'] },
        { week: 2, topic: 'Genetics', tasks: ['Punnett squares'] },
      ],
      created_at: '2026-08-01T00:00:00',
    },
  ];
  const store = [...saved];
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({
        user: { id: 1, name: 'Alex', current_level: 5, total_xp: 2340, current_streak: 3, avatar: null, avatar_class: 'Wizard', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
      }),
      studyPlans: {
        list: vi.fn().mockImplementation(() => Promise.resolve([...store])),
        create: vi.fn().mockImplementation((d) => {
          const created = { id: store.length + 1, ...d, created_at: null };
          store.unshift(created);
          return Promise.resolve(created);
        }),
        delete: vi.fn().mockResolvedValue({ ok: true }),
      },
      ai: {
        health: vi.fn().mockResolvedValue({ available: false, mode: 'Offline', model: null, models: [] }),
        studyPlan: vi.fn().mockResolvedValue({
          plan: { subject: 'Physics', exam_date: '2026-06-01', weeks: saved[0].weeks },
          ai_used: false,
        }),
      },
    },
  };
});

describe('StudyPlans page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the seeded plan with week cards', async () => {
    render(<StudyPlans />);
    await waitFor(() => expect(screen.getAllByText('Biology Final').length).toBeGreaterThan(0));
    expect(screen.getByText('Cell Biology')).toBeInTheDocument();
    expect(screen.getByText('Genetics')).toBeInTheDocument();
    expect(screen.getByText('Read Ch 1-2')).toBeInTheDocument();
    expect(screen.getByText('W1')).toBeInTheDocument();
  });

  it('generates and saves a new plan', async () => {
    render(<StudyPlans />);
    await waitFor(() => expect(screen.getAllByText('Biology Final').length).toBeGreaterThan(0));

    const input = screen.getByPlaceholderText('Subject or topic (e.g. Calculus Final)');
    fireEvent.change(input, { target: { value: 'Physics' } });
    fireEvent.click(screen.getByText('✨ Generate'));

    await waitFor(() => expect(screen.getByText('Physics', { selector: 'h2' })).toBeInTheDocument());
  });
});
