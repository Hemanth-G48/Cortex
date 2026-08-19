import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { DomainDetail } from '../pages/DomainDetail';
import { endpoints } from '../services/api';
import type { KbDomainDetail, KbDomainGapsResponse } from '../services/api';

vi.mock('../services/api', () => {
  const getMock = vi.fn();
  const gapsMock = vi.fn();
  const analyzeGapsMock = vi.fn();
  return {
    endpoints: {
      kb: {
        folders: { get: getMock, gaps: gapsMock, analyzeGaps: analyzeGapsMock },
        gaps: { createNote: vi.fn() },
      },
    },
  };
});

const domainDetail: KbDomainDetail = {
  id: 11,
  name: 'Web Security',
  path: 'Cybersecurity/Web Security',
  depth: 1,
  doc_count: 2,
  description: 'Web application security fundamentals.',
  status: 'active',
  color: null,
  course: { id: 1, title: 'Cybersecurity' },
  breadcrumb: [
    { id: null, name: 'Cybersecurity', path: 'Cybersecurity' },
    { id: 11, name: 'Web Security', path: 'Cybersecurity/Web Security' },
  ],
  documents: [
    {
      id: 501,
      title: 'SQL Injection',
      doc_type: 'md',
      path_rel: 'Cybersecurity/Web Security/SQL Injection.md',
      char_count: 1200,
      quality_score: 0.9,
      reading_time_seconds: 300,
      author: null,
      created_at: null,
      updated_at: null,
    },
    {
      id: 502,
      title: 'XSS',
      doc_type: 'md',
      path_rel: 'Cybersecurity/Web Security/XSS.md',
      char_count: 800,
      quality_score: 0.7,
      reading_time_seconds: 200,
      author: null,
      created_at: null,
      updated_at: null,
    },
  ],
  subfolders: [
    {
      id: 21,
      name: 'Authentication',
      path: 'Cybersecurity/Web Security/Authentication',
      depth: 2,
      doc_count: 2,
      description: null,
      status: 'active',
      color: null,
    },
  ],
};

const gapItem = {
  name: 'XXE',
  level: 'Weak' as const,
  priority: 'Medium' as const,
  skill: 'XML parsing',
  domain: 'Web Security',
  importance: 2,
  why: 'XXE can read local files through misconfigured XML parsers.',
  prerequisites: [],
  blocked: false,
  learn: ['XXE fundamentals', 'Mitigation'],
  practice: ['Craft a safe XXE payload'],
  next: null,
  sources: [],
  related_known: [],
  evidence: { strength: 0, exposure: 0, mentions: 0, documents: 0, quiz_errors: 0, retrieval_misses: 0 },
};

const gapsPayload: KbDomainGapsResponse = {
  summary: {
    text: 'You have gaps in Web Security. Your highest-priority missing concepts are XXE. Follow the recommended path below — foundations first.',
    priorities: ['XXE'],
    strong_areas: [],
  },
  strengths: [{ ...gapItem, name: 'CSRF', level: 'Strong', priority: null }],
  gaps: [gapItem],
  path: [{ phase: 1, title: 'Phase 1', items: [{ name: 'XXE', level: 'Weak', priority: 'Medium' }] }],
  next: gapItem,
  domain: 'Web Security',
  coverage: { known: 1, gaps: 1, total: 2, percent: 50 },
  document_count: 2,
  folder: { id: 11, name: 'Web Security', path: 'Cybersecurity/Web Security' },
};

const renderDomain = (initialEntry = '/courses/1/domain/11') =>
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/courses/:courseId/domain/:domainId" element={<DomainDetail />} />
      </Routes>
    </MemoryRouter>,
  );

describe('DomainDetail (folder-derived domain page)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(endpoints.kb.folders.get).mockResolvedValue(domainDetail);
  });

  it('opens the domain from its folder — documents listed with zero gap/LLM calls', async () => {
    renderDomain();
    await waitFor(() => expect(screen.getByRole('heading', { name: /📂 Web Security/ })).toBeInTheDocument());

    // Breadcrumb links back to the owning course.
    expect(screen.getByRole('link', { name: /Cybersecurity/ })).toHaveAttribute('href', '/courses/1');
    // Documents come straight from the folder (no manual assignment).
    expect(screen.getByText('SQL Injection')).toBeInTheDocument();
    expect(screen.getByText('XSS')).toBeInTheDocument();
    expect(screen.getByText(/SQL Injection\.md/)).toBeInTheDocument();
    // Subdomain cards from nested folders.
    expect(screen.getByText('Authentication')).toBeInTheDocument();

    // Opening the page must NOT trigger any gap computation.
    expect(endpoints.kb.folders.gaps).not.toHaveBeenCalled();
    expect(endpoints.kb.folders.analyzeGaps).not.toHaveBeenCalled();
  });

  it('reads the persisted gap analysis on click (cached, no recompute)', async () => {
    vi.mocked(endpoints.kb.folders.gaps).mockResolvedValue({
      ...gapsPayload,
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
      new_notes_since_analysis: 0,
    });

    renderDomain();
    await waitFor(() => expect(screen.getByRole('heading', { name: /📂 Web Security/ })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('domain-gap-analysis-panel')).toBeInTheDocument());

    // The GET returned the saved snapshot — no recompute POST.
    expect(endpoints.kb.folders.gaps).toHaveBeenCalledWith(11);
    expect(endpoints.kb.folders.analyzeGaps).not.toHaveBeenCalled();
    expect(screen.getByTestId('domain-gaps-cached-notice')).toBeInTheDocument();
    expect(screen.getByText(/saved analysis from/)).toBeInTheDocument();
    // Actionable engine renders.
    expect(screen.getByText(/Learn This Next/)).toBeInTheDocument();
    expect(screen.getByText(/Your Strengths/)).toBeInTheDocument();
    expect(screen.getByText(/CSRF/)).toBeInTheDocument();
    expect(screen.getByText(/Knowledge Gaps/)).toBeInTheDocument();
  });

  it('warns when new notes landed in the folder since the saved analysis', async () => {
    vi.mocked(endpoints.kb.folders.gaps).mockResolvedValue({
      ...gapsPayload,
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
      new_notes_since_analysis: 3,
    });

    renderDomain();
    await waitFor(() => expect(screen.getByRole('heading', { name: /📂 Web Security/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('domain-gaps-cached-notice')).toBeInTheDocument());

    const notice = screen.getByTestId('domain-gaps-cached-notice');
    expect(notice.className).toContain('notice-warning');
    expect(screen.getByText(/3 new notes/)).toBeInTheDocument();
    expect(screen.getByText(/were added to this folder since/)).toBeInTheDocument();
  });

  it('recomputes only via the explicit Re-analyze action', async () => {
    vi.mocked(endpoints.kb.folders.gaps).mockResolvedValue({
      ...gapsPayload,
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
      new_notes_since_analysis: 0,
    });
    vi.mocked(endpoints.kb.folders.analyzeGaps).mockResolvedValue({
      ...gapsPayload,
      summary: { text: 'Fresh domain analysis after re-analysis.', priorities: ['XXE'], strong_areas: [] },
      cached: false,
      analyzed_at: '2026-08-10T09:00:00Z',
    });

    renderDomain();
    await waitFor(() => expect(screen.getByRole('heading', { name: /📂 Web Security/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('domain-gap-analysis-panel')).toBeInTheDocument());
    expect(screen.getByTestId('domain-gaps-cached-notice')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Re-analyze/ }));
    await waitFor(() => expect(screen.getByText(/Fresh domain analysis after re-analysis/)).toBeInTheDocument());
    expect(endpoints.kb.folders.analyzeGaps).toHaveBeenCalledWith(11);
    // The cached notice disappears once the fresh result replaces it.
    expect(screen.queryByTestId('domain-gaps-cached-notice')).not.toBeInTheDocument();
  });

  it('does not crash when the gap payload is missing strengths/gaps/path/coverage', async () => {
    // Regression: stored domain-gap payloads are returned verbatim — one
    // missing field must not blank the page (guards + defaults absorb it).
    vi.mocked(endpoints.kb.folders.gaps).mockResolvedValue({
      domain: 'Web Security',
      document_count: 2,
      folder: { id: 11, name: 'Web Security', path: 'Cybersecurity/Web Security' },
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
      new_notes_since_analysis: 0,
    } as unknown as KbDomainGapsResponse);

    renderDomain();
    await waitFor(() => expect(screen.getByRole('heading', { name: /📂 Web Security/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('domain-gap-analysis-panel')).toBeInTheDocument());

    // Empty-state text renders instead of a crash.
    expect(screen.getByText('Gap analysis complete.')).toBeInTheDocument();
    expect(screen.getByText(/Your Strengths \(0\)/)).toBeInTheDocument();
    expect(screen.getByText(/Knowledge Gaps \(0\)/)).toBeInTheDocument();
    expect(screen.queryByText(/Learn This Next/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Recommended Learning Path/)).not.toBeInTheDocument();
  });

  it('shows an API error with a retry instead of a blank page', async () => {
    vi.mocked(endpoints.kb.folders.get).mockRejectedValueOnce(new Error('API 500: boom'));

    renderDomain();
    await waitFor(() => expect(screen.getByText(/API 500: boom/)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Retry/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Retry/ }));
    await waitFor(() => expect(screen.getByRole('heading', { name: /📂 Web Security/ })).toBeInTheDocument());
  });
});
