import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Today } from '../pages/Today';
import { endpoints } from '../services/api';
import type { TodayOverview, MicroSession } from '../services/api';

vi.mock('../services/api', () => {
  const overviewMock = vi.fn();
  const startMock = vi.fn();
  const completeMock = vi.fn();
  const pomodoroMock = vi.fn();
  return {
    endpoints: {
      kb: {
        today: { overview: overviewMock },
        sessions: { start: startMock, complete: completeMock, pomodoro: pomodoroMock },
      },
    },
  };
});

const overview: TodayOverview = {
  date: '2026-08-11',
  day_name: 'Tuesday',
  morning: {
    reviews_due: [],
    next_actions: [
      {
        topic_id: 7,
        topic_name: 'SQL Injection',
        subject_id: 3,
        score: 0.9,
        ready: true,
        blocked_by: [],
        session_length_mins: 25,
        reasons: { readiness: 1, weakness: 0.8, due_reviews: 0, concept_gaps: 0, exam_proximity: 0, subject_coverage: 0 },
      },
    ],
    schedule: [],
    deadlines: [],
    captured_documents: [],
  },
  evening: { focus_minutes: 0, pomodoros: [], journal: [], daily: { date: '2026-08-11', documents: [], schedule: [], journal: [] } },
  captured_today_count: 0,
};

const session: MicroSession = {
  id: 42,
  topic_id: 7,
  topic_name: 'SQL Injection',
  chunk_id: null,
  practice_task: 'Explain SQL Injection in your own words, then check against your notes.',
  duration_mins: 25,
  status: 'started',
  created_at: '2026-08-11T09:00:00Z',
  completed_at: null,
};

const renderPage = () =>
  render(
    <MemoryRouter>
      <Today />
    </MemoryRouter>,
  );

describe('Today (start-session flow)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(endpoints.kb.today.overview).mockResolvedValue(overview);
  });

  it('renders next actions with a Start button', async () => {
    renderPage();
    await waitFor(() => expect(endpoints.kb.today.overview).toHaveBeenCalled());
    expect(screen.getByText('SQL Injection')).toBeInTheDocument();
    expect(screen.getByTestId('start-session-7')).toBeInTheDocument();
  });

  it('starts a micro-session and shows the running panel', async () => {
    vi.mocked(endpoints.kb.sessions.start).mockResolvedValue({ session });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('start-session-7')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('start-session-7'));
    await waitFor(() => expect(endpoints.kb.sessions.start).toHaveBeenCalledWith(7, 25));

    expect(screen.getByTestId('launched-session')).toBeInTheDocument();
    expect(screen.getByText(/Session running/)).toBeInTheDocument();
    // Topic name appears in both the next-action row and the running panel.
    expect(screen.getAllByText(/SQL Injection/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Explain SQL Injection in your own words/)).toBeInTheDocument();
  });

  it('launches a pomodoro from the running session', async () => {
    vi.mocked(endpoints.kb.sessions.start).mockResolvedValue({ session });
    vi.mocked(endpoints.kb.sessions.pomodoro).mockResolvedValue({
      ok: true,
      pomodoro_id: 9,
      duration_minutes: 25,
      task_description: 'Explain SQL Injection…',
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('start-session-7')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('start-session-7'));
    await waitFor(() => expect(screen.getByTestId('launched-session')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Launch pomodoro/ }));
    await waitFor(() => expect(endpoints.kb.sessions.pomodoro).toHaveBeenCalledWith(42));
    expect(screen.getByText(/Pomodoro launched \(25m\)/)).toBeInTheDocument();
  });

  it('completes the session and refreshes the overview', async () => {
    vi.mocked(endpoints.kb.sessions.start).mockResolvedValue({ session });
    vi.mocked(endpoints.kb.sessions.complete).mockResolvedValue({ ok: true, session });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('start-session-7')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('start-session-7'));
    await waitFor(() => expect(screen.getByTestId('launched-session')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Complete/ }));
    await waitFor(() => expect(endpoints.kb.sessions.complete).toHaveBeenCalledWith(42));
    expect(screen.getByText(/Session completed/)).toBeInTheDocument();
    // Running panel closes after completion.
    await waitFor(() => expect(screen.queryByTestId('launched-session')).not.toBeInTheDocument());
    // Overview refetched after completion.
    await waitFor(() => expect(endpoints.kb.today.overview).toHaveBeenCalledTimes(2));
  });

  it('disables the Start button for the topic whose session is already running', async () => {
    vi.mocked(endpoints.kb.sessions.start).mockResolvedValue({ session });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('start-session-7')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('start-session-7'));
    await waitFor(() => expect(screen.getByTestId('launched-session')).toBeInTheDocument());
    expect(screen.getByTestId('start-session-7')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Running' })).toBeInTheDocument();
  });

  it('shows an error when starting fails', async () => {
    vi.mocked(endpoints.kb.sessions.start).mockRejectedValue(new Error('API 500: boom'));
    renderPage();
    await waitFor(() => expect(screen.getByTestId('start-session-7')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('start-session-7'));
    await waitFor(() => expect(screen.getByTestId('session-notice')).toHaveTextContent(/API 500: boom/));
    expect(screen.queryByTestId('launched-session')).not.toBeInTheDocument();
  });
});
