import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { GapAnalysis } from '../pages/GapAnalysis';
import { endpoints } from '../services/api';
import type { GapAnalysisResponse, GapGoalInfo } from '../services/api';

vi.mock('../services/api', () => {
  const domainsMock = vi.fn();
  const goalMock = vi.fn();
  const analyzeGoalMock = vi.fn();
  const goalHistoryMock = vi.fn();
  return {
    endpoints: {
      kb: {
        gaps: {
          domains: domainsMock,
          goal: goalMock,
          analyzeGoal: analyzeGoalMock,
          goalHistory: goalHistoryMock,
        },
      },
    },
  };
});

const goals: GapGoalInfo[] = [
  {
    key: 'ctf',
    title: 'Cybersecurity CTF',
    description: 'Become strong at capture-the-flag competitions.',
    domains: ['Cybersecurity Foundations', 'Web Security', 'Binary Exploitation', 'Cryptography', 'Forensics', 'Reverse Engineering'],
  },
  {
    key: 'software-engineering',
    title: 'Software Engineering',
    description: 'Strengthen programming, data structures, and systems foundations.',
    domains: ['Programming & Data Structures', 'Databases', 'Operating Systems', 'Computer Networks'],
  },
];

const gapItem = {
  name: 'SSRF',
  level: 'Not Found' as const,
  priority: 'High' as const,
  skill: 'Server-Side Attacks',
  domain: 'Web Security',
  importance: 3,
  why: 'Server-Side Request Forgery is a top web vulnerability and a bridge to internal networks and cloud metadata.',
  prerequisites: [
    { name: 'HTTP fundamentals', level: 'Strong' as const, known: true },
    { name: 'Networking fundamentals', level: 'Not Found' as const, known: false },
  ],
  blocked: true,
  learn: ['How SSRF works (server making requests)', 'Accessing localhost / internal services'],
  practice: ['Solve 3 beginner SSRF labs'],
  next: 'XXE',
  sources: [{ document_id: 10, title: 'SSRF Notes' }],
  related_known: ['HTTP fundamentals'],
  evidence: { strength: 0, exposure: 0, mentions: 0, documents: 0, quiz_errors: 0, retrieval_misses: 0 },
};

const ctfResult: GapAnalysisResponse = {
  goal: 'Cybersecurity CTF',
  goal_key: 'ctf',
  domain: null,
  summary: {
    text: 'You are strong in HTTP fundamentals but have gaps in Web Security. Your highest-priority missing concepts are SSRF.',
    priorities: ['SSRF'],
    strong_areas: ['HTTP fundamentals'],
  },
  strengths: [{ ...gapItem, name: 'HTTP fundamentals', level: 'Strong' as const, priority: null }],
  gaps: [gapItem],
  path: [{ phase: 1, title: 'Phase 1', items: [{ name: 'SSRF', level: 'Not Found', priority: 'High' }] }],
  next: gapItem,
  coverage: { known: 1, gaps: 1, total: 2, percent: 50 },
  domain_breakdown: [
    {
      domain: 'Web Security',
      total: 2,
      strong: ['HTTP fundamentals'],
      developing: [],
      gaps: ['SSRF'],
      status: 'Developing',
      strong_ratio: 0.5,
      gap_ratio: 0.5,
    },
  ],
};

const renderPage = () =>
  render(
    <MemoryRouter>
      <GapAnalysis />
    </MemoryRouter>,
  );

describe('GapAnalysis (goal-level page)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(endpoints.kb.gaps.domains).mockResolvedValue({ goals });
    vi.mocked(endpoints.kb.gaps.goal).mockResolvedValue(ctfResult);
  });

  it('loads goals, runs the default analysis, and renders the actionable report', async () => {
    renderPage();

    await waitFor(() => expect(endpoints.kb.gaps.goal).toHaveBeenCalledWith('ctf'));
    expect(screen.getByText('Cybersecurity CTF')).toBeInTheDocument();
    expect(screen.getByText('Software Engineering')).toBeInTheDocument();

    // Narrative + domain readiness + strengths + gap + path.
    await waitFor(() => expect(screen.getByText(/Your highest-priority missing concepts/)).toBeInTheDocument());
    expect(screen.getByText(/Domain Readiness/)).toBeInTheDocument();
    expect(screen.getByText(/Learn This Next/)).toBeInTheDocument();
    expect(screen.getByText(/Your Strengths/)).toBeInTheDocument();
    expect(screen.getByText(/Knowledge Gaps/)).toBeInTheDocument();
    expect(screen.getByText(/Recommended Learning Path/)).toBeInTheDocument();
    // Real Second Brain resource linked to the SSRF gap.
    expect(screen.getByText('📄 SSRF Notes')).toBeInTheDocument();
  });

  it('switching goals refetches with the selected goal', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Software Engineering')).toBeInTheDocument());
    expect(endpoints.kb.gaps.goal).toHaveBeenCalledWith('ctf');
  });

  it('shows an error state when the goal analysis fails', async () => {
    vi.mocked(endpoints.kb.gaps.goal).mockRejectedValueOnce(new Error('API 500: boom'));
    renderPage();
    await waitFor(() => expect(screen.getByText(/API 500: boom/)).toBeInTheDocument());
  });

  it('warns when new notes were added since the saved goal analysis', async () => {
    vi.mocked(endpoints.kb.gaps.goal).mockResolvedValue({
      ...ctfResult,
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
      new_notes_since_analysis: 4,
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('gaps-cached-notice')).toBeInTheDocument());

    const notice = screen.getByTestId('gaps-cached-notice');
    expect(notice.className).toContain('notice-warning');
    expect(screen.getByText(/4 new notes/)).toBeInTheDocument();
    expect(screen.getByText(/were added to your Second Brain since/)).toBeInTheDocument();
  });

  it('toggles the goal history timeline and shows deltas across snapshots', async () => {
    vi.mocked(endpoints.kb.gaps.goal).mockResolvedValue({
      ...ctfResult,
      cached: true,
      analyzed_at: '2026-08-10T09:00:00Z',
      new_notes_since_analysis: 0,
    });
    vi.mocked(endpoints.kb.gaps.goalHistory).mockResolvedValue({
      history: [
        {
          analyzed_at: '2026-08-09T10:30:00Z',
          document_count: 2,
          gap_count: 2,
          strength_count: 0,
          coverage: { known: 0, gaps: 2, total: 2, percent: 0 },
          next: 'SSRF',
          gaps: [
            { name: 'SSRF', level: 'Not Found', priority: 'High' },
            { name: 'XXE', level: 'Not Found', priority: 'Medium' },
          ],
          strengths: [],
        },
        {
          analyzed_at: '2026-08-10T09:00:00Z',
          document_count: 3,
          gap_count: 2,
          strength_count: 1,
          coverage: { known: 0, gaps: 2, total: 2, percent: 0 },
          next: 'SSRF',
          gaps: [
            { name: 'SSRF', level: 'Weak', priority: 'High' },
            { name: 'CSRF', level: 'Not Found', priority: 'High' },
          ],
          strengths: [{ name: 'HTTP fundamentals', level: 'Strong' }],
        },
      ],
    });

    renderPage();
    await waitFor(() => expect(screen.getByTestId('gaps-cached-notice')).toBeInTheDocument());
    expect(screen.queryByTestId('gap-history-view')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /History/ }));
    await waitFor(() => expect(screen.getByTestId('gap-history-view')).toBeInTheDocument());
    expect(endpoints.kb.gaps.goalHistory).toHaveBeenCalledWith('ctf');

    // Deltas vs previous snapshot: SSRF improved, XXE resolved, CSRF new.
    expect(screen.getByText(/\+1 new/)).toBeInTheDocument();
    expect(screen.getByText(/1 resolved/)).toBeInTheDocument();
    expect(screen.getByText(/1 improved/)).toBeInTheDocument();
  });

  it('shows a cached notice and recomputes only via the explicit Re-analyze action', async () => {
    // First GET returns the SAVED copy (cached) — no recompute.
    vi.mocked(endpoints.kb.gaps.goal).mockResolvedValue({
      ...ctfResult,
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
    });
    // The explicit Re-analyze POST returns a fresh (uncached) payload.
    vi.mocked(endpoints.kb.gaps.analyzeGoal).mockResolvedValue({
      ...ctfResult,
      summary: {
        text: 'Fresh goal summary after re-analysis.',
        priorities: ['SSRF'],
        strong_areas: ['HTTP fundamentals'],
      },
      cached: false,
      analyzed_at: '2026-08-10T09:00:00Z',
    });

    renderPage();
    await waitFor(() => expect(endpoints.kb.gaps.goal).toHaveBeenCalledWith('ctf'));

    // Cached notice references the saved timestamp; no recompute happened.
    expect(screen.getByTestId('gaps-cached-notice')).toBeInTheDocument();
    expect(screen.getByText(/saved analysis from/)).toBeInTheDocument();
    expect(endpoints.kb.gaps.analyzeGoal).not.toHaveBeenCalled();

    // Re-analyze is an explicit user action → POST, fresh payload replaces.
    fireEvent.click(screen.getByRole('button', { name: /Re-analyze/ }));
    await waitFor(() => expect(screen.getByText(/Fresh goal summary after re-analysis/)).toBeInTheDocument());
    expect(endpoints.kb.gaps.analyzeGoal).toHaveBeenCalledWith('ctf');
    // Cached notice disappears once the fresh (uncached) result is shown.
    expect(screen.queryByTestId('gaps-cached-notice')).not.toBeInTheDocument();
  });

  it('does not crash when the payload is missing summary/strengths/gaps/path/coverage/domain_breakdown', async () => {
    // Regression: saved payloads are returned verbatim by the backend, so a
    // stored payload written by an older/other engine may lack these fields.
    // The page must render (with empty sections), not unmount.
    vi.mocked(endpoints.kb.gaps.goal).mockResolvedValue({
      goal: 'Cybersecurity CTF',
      goal_key: 'ctf',
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
      new_notes_since_analysis: 0,
    } as unknown as GapAnalysisResponse);

    renderPage();
    await waitFor(() => expect(endpoints.kb.gaps.goal).toHaveBeenCalledWith('ctf'));

    // The page still renders the summary card (with the empty-state text), the
    // empty sections, and the coverage line — instead of crashing blank.
    expect(screen.getByText('Gap analysis complete.')).toBeInTheDocument();
    expect(screen.getByText(/Your Strengths \(0\)/)).toBeInTheDocument();
    expect(screen.getByText(/Knowledge Gaps \(0\)/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence coverage: 0 of 0/)).toBeInTheDocument();
    expect(screen.queryByText(/Domain Readiness/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Recommended Learning Path/)).not.toBeInTheDocument();
  });
});
