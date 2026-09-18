import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Quiz } from '../pages/Quiz';

vi.mock('../services/api', () => {
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({
        user: { id: 1, name: 'Alex', current_level: 5, total_xp: 2340, current_streak: 3, avatar: null, avatar_class: 'Wizard', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
      }),
      notes: { list: vi.fn().mockResolvedValue([]) },
      quizzes: {
        history: vi.fn().mockResolvedValue([]),
        historyCreate: vi.fn().mockResolvedValue(null),
      },
      ai: {
        health: vi.fn().mockResolvedValue({ available: false, mode: 'Offline', model: null, models: [] }),
        quiz: vi.fn().mockResolvedValue({
          questions: [
            { q: 'What is 2+2?', opts: ['3', '4', '5', '6'], ans: 1 },
            { q: 'What is the capital of France?', opts: ['Berlin', 'Madrid', 'Paris', 'Rome'], ans: 2 },
          ],
          ai_used: false,
        }),
      },
    },
  };
});

describe('Quiz page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('runs the full quiz flow and shows results', async () => {
    render(<Quiz />);
    expect(screen.getByText('🧠 Quiz Generator')).toBeInTheDocument();

    fireEvent.click(screen.getByText('✨ Start Quiz'));
    await waitFor(() => expect(screen.getByText('What is 2+2?')).toBeInTheDocument());

    // Answer Q1 correctly (index 1)
    fireEvent.click(screen.getByText('4'));
    await waitFor(() => expect(screen.getByText('What is the capital of France?')).toBeInTheDocument());

    // Answer Q2 correctly (index 2)
    fireEvent.click(screen.getByText('Paris'));
    await waitFor(() => expect(screen.getByText('2 / 2')).toBeInTheDocument());
    expect(screen.getByText('Perfect score!')).toBeInTheDocument();
    expect(screen.getByText('+20 XP earned')).toBeInTheDocument();
  });
});
