import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Flashcards } from '../pages/Flashcards';

vi.mock('../services/api', () => {
  const decks = [
    {
      id: 1,
      name: 'Integration Techniques',
      course_id: 1,
      created_at: '2026-08-01T00:00:00',
      card_count: 2,
      cards: [
        { id: 11, deck_id: 1, front: 'What is u-substitution?', back: "Let u = g(x), du = g'(x)dx.", difficulty: 'easy', streak: 2, next_review: null, created_at: null },
        { id: 12, deck_id: 1, front: 'What does LIATE stand for?', back: 'Logs, Inverse trig, Algebraic, Trig, Exponential.', difficulty: 'basic', streak: 1, next_review: null, created_at: null },
      ],
    },
    {
      id: 2,
      name: 'Data Structures',
      course_id: 2,
      created_at: '2026-08-02T00:00:00',
      card_count: 0,
      cards: [],
    },
  ];
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({
        user: { id: 1, name: 'Alex', current_level: 5, total_xp: 2340, current_streak: 3, avatar: null, avatar_class: 'Wizard', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
      }),
      flashcards: {
        list: vi.fn().mockResolvedValue(decks),
        get: vi.fn().mockResolvedValue(decks[0]),
        create: vi.fn().mockResolvedValue({}),
        delete: vi.fn().mockResolvedValue({ ok: true }),
        cards: vi.fn().mockResolvedValue(decks[0].cards),
        addCard: vi.fn().mockResolvedValue({}),
        updateCard: vi.fn().mockResolvedValue({}),
        deleteCard: vi.fn().mockResolvedValue({ ok: true }),
      },
      notes: { list: vi.fn().mockResolvedValue([]) },
      ai: {
        health: vi.fn().mockResolvedValue({ available: false, mode: 'Offline', model: null, models: [] }),
        flashcards: vi.fn().mockResolvedValue({
          cards: [
            { front: 'Q1?', back: 'A1' },
            { front: 'Q2?', back: 'A2' },
          ],
          ai_used: false,
        }),
        gradeAnswer: vi.fn().mockResolvedValue({ correct: true, explanation: 'Correct!', ai_used: false }),
      },
    },
  };
});

describe('Flashcards page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the deck grid with card counts', async () => {
    render(<Flashcards />);
    await waitFor(() => expect(screen.getByText('Integration Techniques')).toBeInTheDocument());
    expect(screen.getByText('Data Structures')).toBeInTheDocument();
    expect(screen.getByText('2 cards')).toBeInTheDocument();
  });

  it('enters study mode and flips a card', async () => {
    render(<Flashcards />);
    await waitFor(() => expect(screen.getByText('Integration Techniques')).toBeInTheDocument());

    fireEvent.click(screen.getAllByText('Study')[0]);
    await waitFor(() => expect(screen.getByText(/click to flip/i)).toBeInTheDocument());

    // Front shown
    expect(screen.getByText('What is u-substitution?')).toBeInTheDocument();
    // Flip
    fireEvent.click(screen.getByText('What is u-substitution?'));
    expect(screen.getByText(/Let u = g\(x\)/)).toBeInTheDocument();

    // Next card
    fireEvent.click(screen.getByText('Next →'));
    expect(screen.getByText('What does LIATE stand for?')).toBeInTheDocument();
  });

  it('grades a written answer', async () => {
    render(<Flashcards />);
    await waitFor(() => expect(screen.getByText('Integration Techniques')).toBeInTheDocument());

    fireEvent.click(screen.getAllByText('Study')[0]);
    await waitFor(() => expect(screen.getByText(/click to flip/i)).toBeInTheDocument());

    fireEvent.click(screen.getByText('Written'));
    const textarea = screen.getByPlaceholderText('Type your answer…');
    fireEvent.change(textarea, { target: { value: 'some answer' } });
    fireEvent.click(screen.getByText('Submit Answer'));

    await waitFor(() => expect(screen.getByText(/Correct! \+5 XP/i)).toBeInTheDocument());
  });

  it('opens the generate modal', async () => {
    render(<Flashcards />);
    await waitFor(() => expect(screen.getByText('Integration Techniques')).toBeInTheDocument());

    fireEvent.click(screen.getAllByText('Study')[0]);
    await waitFor(() => expect(screen.getByText(/click to flip/i)).toBeInTheDocument());

    fireEvent.click(screen.getByText('✨ Generate'));
    expect(screen.getByText('✨ Generate with AI')).toBeInTheDocument();
    expect(screen.getByText('Basic')).toBeInTheDocument();
  });
});
