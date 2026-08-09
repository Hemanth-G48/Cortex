import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AiInsightsCard } from '../components/kb/AiInsightsCard';

// Hoisted so the vi.mock factory below can reference it (vitest hoisting).
const SAMPLE = vi.hoisted(() => ({
  insights: '75% of your tasks are complete. Keep the streak alive!',
  stats: {
    user: { level: 5, total_xp: 2340, streak: 3 },
    tasks: { total: 8, completed: 6, completion_rate: 75, recent_completions: [] },
    assignments: { pending: 2, upcoming: [] },
    exams: { upcoming_exams: [] },
    habits: { total: 3, active_streaks: 2, best_streak: 7 },
  },
  cached: false,
  ai_used: false,
}));

vi.mock('../services/api', () => ({
  endpoints: {
    ai: {
      insights: vi.fn().mockResolvedValue(SAMPLE),
    },
  },
}));

describe('AiInsightsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the fetched insights with stats', async () => {
    render(<AiInsightsCard />);
    await waitFor(() => {
      expect(screen.getByText(/75% of your tasks are complete/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Tasks: 6\/8 done/)).toBeInTheDocument();
    expect(screen.getByText(/XP: 2340/)).toBeInTheDocument();
    expect(screen.getByText(/Habits: 2 active/)).toBeInTheDocument();
  });

  it('shows a cached badge when served from the response cache', async () => {
    const { endpoints } = await import('../services/api');
    vi.mocked(endpoints.ai.insights).mockResolvedValueOnce({ ...SAMPLE, cached: true });
    render(<AiInsightsCard />);
    await waitFor(() => {
      expect(screen.getByText('cached')).toBeInTheDocument();
    });
  });

  it('shows offline mode badge for the deterministic fallback', async () => {
    const { endpoints } = await import('../services/api');
    vi.mocked(endpoints.ai.insights).mockResolvedValueOnce({ ...SAMPLE, ai_used: false });
    render(<AiInsightsCard />);
    await waitFor(() => {
      expect(screen.getByText('offline mode')).toBeInTheDocument();
    });
  });

  it('handles fetch failure gracefully', async () => {
    const { endpoints } = await import('../services/api');
    vi.mocked(endpoints.ai.insights).mockRejectedValueOnce(new Error('offline'));
    render(<AiInsightsCard />);
    await waitFor(() => {
      expect(screen.getByText(/Couldn't load insights/)).toBeInTheDocument();
    });
  });
});
