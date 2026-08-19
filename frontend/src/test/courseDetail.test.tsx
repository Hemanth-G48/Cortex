import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { CourseDetail } from '../pages/CourseDetail';
import { endpoints } from '../services/api';
import type { CourseContentResponse } from '../services/api';

// Sigma draws to <canvas> (jsdom cannot) — stub the canvas out of this page test.
vi.mock('../components/kb/KnowledgeGraphCanvas', () => ({
  KnowledgeGraphCanvas: () => <div data-testid="subject-graph">graph</div>,
}));

vi.mock('../components/NotificationsBell', () => ({
  NotificationsBell: () => null,
}));

vi.mock('../services/api', () => {
  const contentMock = vi.fn();
  const gapsMock = vi.fn();
  const analyzeGapsMock = vi.fn();
  const resyncMock = vi.fn();
  const gapHistoryMock = vi.fn();
  return {
    endpoints: {
      courses: {
        content: contentMock,
        gaps: gapsMock,
        analyzeGaps: analyzeGapsMock,
        resync: resyncMock,
        gapHistory: gapHistoryMock,
      },
    },
  };
});

const content: CourseContentResponse = {
  course: {
    id: 1,
    title: 'Operating Systems',
    image_url: null,
    current_assignment: 2,
    total_assignments: 5,
    next_exam: null,
    total_exams: 0,
    status: 'In progress',
    user_id: 1,
    credits: 3,
    source_type: 'kb_tag',
    kb_tag_id: 42,
    kb_document_count: 2,
    // Folder-level metadata (from the vault's index.md frontmatter) surfaces
    // in the Course Information panel.
    description: 'Processes, memory and scheduling fundamentals.',
    color: '#8b5cf6',
  },
  second_brain: {
    document_count: 2,
    documents: [
      {
        id: 101,
        title: 'Processes',
        doc_type: 'md',
        path_rel: 'os/processes.md',
        char_count: 500,
        outline: [{ level: 1, text: 'Scheduling', char_start: 0 }],
        tags: ['course:Operating Systems'],
        wikilinks: [],
        quality_score: 0.8,
        reading_time_seconds: 300,
        author: null,
        created_at: null,
        updated_at: null,
      },
      {
        id: 102,
        title: 'Threads',
        doc_type: 'md',
        path_rel: 'os/threads.md',
        char_count: 300,
        outline: null,
        tags: ['course:Operating Systems'],
        wikilinks: [],
        quality_score: null,
        reading_time_seconds: null,
        author: null,
        created_at: null,
        updated_at: null,
      },
    ],
    topics: [
      {
        id: 't0',
        name: 'Scheduling',
        level: 1,
        documents: [{
          id: 101,
          title: 'Processes',
          doc_type: 'md',
          path_rel: 'os/processes.md',
          char_count: 500,
          outline: [{ level: 1, text: 'Scheduling', char_start: 0 }],
          tags: ['course:Operating Systems'],
          wikilinks: [],
          quality_score: 0.8,
          reading_time_seconds: 300,
          author: null,
          created_at: null,
          updated_at: null,
        }],
        children: [
          {
            id: 't1',
            name: 'Round Robin',
            level: 2,
            documents: [],
            children: [],
          },
        ],
      },
    ],
    unorganized_documents: [{
      id: 102,
      title: 'Threads',
      doc_type: 'md',
      path_rel: 'os/threads.md',
      char_count: 300,
      outline: null,
      tags: ['course:Operating Systems'],
      wikilinks: [],
      quality_score: null,
      reading_time_seconds: null,
      author: null,
      created_at: null,
      updated_at: null,
    }],
    concepts: [
      { concept_id: 7, name: 'scheduling', definition: null, mentions: 2, document_count: 1, sources: [{ document_id: 101, title: 'Processes' }] },
    ],
    graph: {
      nodes: [{ id: 'doc:101', kind: 'document', label: 'Processes', doc_type: 'md', status: 'unchanged', degree: 1 }],
      edges: [],
      truncated: false,
      total_nodes: 1,
      total_edges: 0,
    },
  },
  classroom: {
    linked: false,
    google_id: null,
    course_url: null,
    assignments: [],
    total_assignments: 0,
  },
};

const renderDetail = (initialEntry = '/courses/1') =>
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/courses/:id" element={<CourseDetail />} />
      </Routes>
    </MemoryRouter>,
  );

describe('CourseDetail (Subject Details page)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(endpoints.courses.content).mockResolvedValue(content);
  });

  it('renders Second Brain topics with their documents and no Progress tile', async () => {
    renderDetail();
    await waitFor(() => expect(screen.getByText('Scheduling')).toBeInTheDocument());

    expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument();
    // Topic carries its document (also listed in the full documents section).
    expect(screen.getAllByText('Processes').length).toBeGreaterThan(0);
    expect(screen.getByText('Round Robin')).toBeInTheDocument();
    // The old Progress stat tile is gone (its label and tile both absent).
    expect(screen.queryByText('Progress', { selector: '.label' })).not.toBeInTheDocument();
    expect(screen.queryByText('Progress')).not.toBeInTheDocument();
  });

  it('shows a folder path breadcrumb on folder-derived topics', async () => {
    const folderContent: CourseContentResponse = {
      ...content,
      second_brain: {
        ...content.second_brain,
        topics: [
          {
            id: 'f0',
            name: 'Memory',
            level: 1,
            origin: 'folder',
            documents: [],
            children: [
              {
                id: 'f1',
                name: 'Virtual Memory',
                level: 2,
                origin: 'folder',
                documents: [],
                children: [],
              },
            ],
          },
          {
            id: 'h0',
            name: 'Scheduling',
            level: 1,
            origin: 'heading',
            documents: [],
            children: [],
          },
        ],
      },
    };
    vi.mocked(endpoints.courses.content).mockResolvedValueOnce(folderContent);

    renderDetail();
    await waitFor(() => expect(screen.getByText('Memory')).toBeInTheDocument());

    // The nested folder topic shows the full vault trail as a breadcrumb.
    expect(screen.getByText('Memory / Virtual Memory')).toBeInTheDocument();
    expect(screen.getByTitle('Vault folder: Memory / Virtual Memory')).toBeInTheDocument();
    // Top-level folder (breadcrumb == name) and heading topics don't show one.
    expect(screen.queryByText('Memory / Memory')).not.toBeInTheDocument();
    // Heading topics keep the book icon, folders the folder icon.
    const folderIcon = screen.getAllByText('📁');
    expect(folderIcon.length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('📖').length).toBeGreaterThanOrEqual(1);
  });

  it('renders the domains-first grid from the folder hierarchy before the flat lists', async () => {
    const withDomains: CourseContentResponse = {
      ...content,
      second_brain: {
        ...content.second_brain,
        domains: [
          { id: 11, name: 'Web Security', path: 'Cybersecurity/Web Security', depth: 1, doc_count: 4, description: null, status: 'active', color: null },
          { id: 12, name: 'Reverse Engineering', path: 'Cybersecurity/Reverse Engineering', depth: 1, doc_count: 3, description: null, status: 'active', color: null },
        ],
      },
    };
    vi.mocked(endpoints.courses.content).mockResolvedValueOnce(withDomains);

    renderDetail();
    await waitFor(() => expect(screen.getByTestId('domains-grid')).toBeInTheDocument());

    // Domains (folders) are the primary organization — one card each.
    expect(screen.getByRole('heading', { name: /Domains/ })).toBeInTheDocument();
    expect(screen.getByText('Web Security')).toBeInTheDocument();
    expect(screen.getByText('Reverse Engineering')).toBeInTheDocument();
    // Each card shows its folder document count + a gap-analysis entry point.
    expect(screen.getByText('4 docs')).toBeInTheDocument();
    expect(screen.getByText('3 docs')).toBeInTheDocument();
    expect(screen.getAllByText('🕳️ Gap Analysis').length).toBeGreaterThanOrEqual(2);
    // The heading tree is still below (not replaced).
    expect(screen.getByRole('heading', { name: /Topics & Subtopics/ })).toBeInTheDocument();
  });

  it('renders folder-metadata description and accent color in Course Information', async () => {
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument());

    expect(screen.getByText('Processes, memory and scheduling fundamentals.')).toBeInTheDocument();
    expect(screen.getByText(/Description:/)).toBeInTheDocument();
    expect(screen.getByText(/Accent:/)).toBeInTheDocument();
    // The swatch is a child of the info-value row and carries the accent
    // inline (jsdom serialises the hex as its rgb form in the attribute).
    const swatch = screen.getByText('#8b5cf6').querySelector('.course-color-dot');
    expect(swatch).toHaveAttribute('style', expect.stringContaining('rgb(139, 92, 246)'));
  });

  it('renders the embedded subject knowledge graph', async () => {
    renderDetail();
    await waitFor(() => expect(screen.getByTestId('subject-graph')).toBeInTheDocument());
  });

  it('shows Google Classroom section with empty state when unlinked', async () => {
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: /Google Classroom/ })).toBeInTheDocument());
    expect(screen.getByText(/No assignments synced/)).toBeInTheDocument();
  });

  it('runs gap analysis on click and renders the actionable engine (strengths, gaps, path, next)', async () => {
    const gapItem = {
      name: 'Scheduling',
      level: 'Weak' as const,
      priority: 'Medium' as const,
      skill: 'Processes',
      domain: 'Operating Systems',
      importance: 2,
      why: 'CPU scheduling policies decide responsiveness and fairness.',
      prerequisites: [{ name: 'Processes & threads', level: 'Strong' as const, known: true }],
      blocked: false,
      learn: ['FCFS/SJF/RR/priority', 'Scheduling metrics'],
      practice: ['Simulate RR with a fixed quantum'],
      next: 'Processes & threads',
      sources: [{ document_id: 101, title: 'Processes' }],
      related_known: [],
      evidence: { strength: 0, exposure: 0, mentions: 1, documents: 1, quiz_errors: 0, retrieval_misses: 0 },
    };
    vi.mocked(endpoints.courses.gaps).mockResolvedValue({
      topics: [
        { topic: 'Virtualization', normalized: 'virtualization', coverage: 0.25, documents: 1, is_gap: true },
        { topic: 'Scheduling', normalized: 'scheduling', coverage: 1.0, documents: 2, is_gap: false },
      ],
      concepts: [{
        concept_id: 7,
        concept: 'scheduling',
        definition: null,
        score: 0.55,
        evidence: { strength: 0.0, exposure_count: 0, quiz_errors: 2, retrieval_misses: 0 },
        sources: [{ document_id: 101, title: 'Processes' }],
      }],
      classroom: { assignments: [], total: 0, pending: 0 },
      threshold: 0.5,
      document_count: 2,
      summary: {
        text: 'You have gaps in Operating Systems. Your highest-priority missing concepts are Scheduling. Follow the recommended path below — foundations first.',
        priorities: ['Scheduling'],
        strong_areas: [],
      },
      domain: 'Operating Systems',
      strengths: [{ ...gapItem, name: 'Processes & threads', level: 'Strong', priority: null }],
      gaps: [gapItem],
      path: [{ phase: 1, title: 'Phase 1', items: [{ name: 'Scheduling', level: 'Weak', priority: 'Medium' }] }],
      next: gapItem,
      coverage: { known: 1, gaps: 1, total: 2, percent: 50 },
    });

    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('gap-analysis-panel')).toBeInTheDocument());

    expect(endpoints.courses.gaps).toHaveBeenCalledWith(1);
    // Actionable engine: narrative, learn-next, strengths, gaps, path.
    expect(screen.getByText(/Your highest-priority missing concepts/)).toBeInTheDocument();
    expect(screen.getByText(/Learn This Next/)).toBeInTheDocument();
    expect(screen.getByText(/Your Strengths/)).toBeInTheDocument();
    expect(screen.getAllByText(/Processes & threads/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Knowledge Gaps/)).toBeInTheDocument();
    expect(screen.getByText(/Recommended Learning Path/)).toBeInTheDocument();
    expect(screen.getAllByText('Scheduling').length).toBeGreaterThan(0);
    // The gap's real Second Brain resource is linked (appears in the gap card
    // and in the Related Concepts section).
    expect(screen.getAllByText('📄 Processes').length).toBeGreaterThan(0);
  });

  it('shows a cached notice and recomputes only via the explicit Re-analyze action', async () => {
    const gapItem = {
      name: 'Scheduling',
      level: 'Weak' as const,
      priority: 'Medium' as const,
      skill: 'Processes',
      domain: 'Operating Systems',
      importance: 2,
      why: 'CPU scheduling policies decide responsiveness and fairness.',
      prerequisites: [],
      blocked: false,
      learn: ['FCFS/SJF/RR/priority'],
      practice: ['Simulate RR with a fixed quantum'],
      next: null,
      sources: [{ document_id: 101, title: 'Processes' }],
      related_known: [],
      evidence: { strength: 0, exposure: 0, mentions: 1, documents: 1, quiz_errors: 0, retrieval_misses: 0 },
    };
    const base = {
      topics: [],
      concepts: [],
      classroom: { assignments: [], total: 0, pending: 0 },
      threshold: 0.5,
      document_count: 2,
      summary: { text: 'Saved summary.', priorities: ['Scheduling'], strong_areas: [] },
      domain: 'Operating Systems',
      strengths: [],
      gaps: [gapItem],
      path: [],
      next: gapItem,
      coverage: { known: 0, gaps: 1, total: 1, percent: 0 },
    };
    // First GET returns the SAVED copy (cached) — no recompute.
    vi.mocked(endpoints.courses.gaps).mockResolvedValue({
      ...base,
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
    });
    // The explicit Re-analyze POST returns a fresh (uncached) payload.
    vi.mocked(endpoints.courses.analyzeGaps).mockResolvedValue({
      ...base,
      summary: { text: 'Fresh summary after re-analysis.', priorities: ['Scheduling'], strong_areas: [] },
      cached: false,
      analyzed_at: '2026-08-10T09:00:00Z',
    });

    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('gap-analysis-panel')).toBeInTheDocument());

    // Cached notice references the saved timestamp; gaps endpoint called once.
    expect(screen.getByTestId('gaps-cached-notice')).toBeInTheDocument();
    expect(screen.getByText(/saved analysis from/)).toBeInTheDocument();
    expect(endpoints.courses.gaps).toHaveBeenCalledTimes(1);
    expect(endpoints.courses.analyzeGaps).not.toHaveBeenCalled();

    // Re-analyze is an explicit user action → POST, fresh payload replaces.
    fireEvent.click(screen.getByRole('button', { name: /Re-analyze/ }));
    await waitFor(() => expect(screen.getByText(/Fresh summary after re-analysis/)).toBeInTheDocument());
    expect(endpoints.courses.analyzeGaps).toHaveBeenCalledWith(1);
    // Cached notice disappears once the fresh (uncached) result is shown.
    expect(screen.queryByTestId('gaps-cached-notice')).not.toBeInTheDocument();
  });

  it('warns when new notes were added since the saved analysis', async () => {
    const gapItem = {
      name: 'Scheduling',
      level: 'Weak' as const,
      priority: 'Medium' as const,
      skill: 'Processes',
      domain: 'Operating Systems',
      importance: 2,
      why: 'CPU scheduling policies decide responsiveness and fairness.',
      prerequisites: [],
      blocked: false,
      learn: [],
      practice: [],
      next: null,
      sources: [{ document_id: 101, title: 'Processes' }],
      related_known: [],
      evidence: { strength: 0, exposure: 0, mentions: 1, documents: 1, quiz_errors: 0, retrieval_misses: 0 },
    };
    vi.mocked(endpoints.courses.gaps).mockResolvedValue({
      topics: [],
      concepts: [],
      classroom: { assignments: [], total: 0, pending: 0 },
      threshold: 0.5,
      document_count: 2,
      summary: { text: 'Saved summary.', priorities: ['Scheduling'], strong_areas: [] },
      domain: 'Operating Systems',
      strengths: [],
      gaps: [gapItem],
      path: [],
      next: gapItem,
      coverage: { known: 0, gaps: 1, total: 1, percent: 0 },
      cached: true,
      analyzed_at: '2026-08-09T10:30:00Z',
      // The user added 3 documents since the analysis was computed.
      new_notes_since_analysis: 3,
    });

    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('gap-analysis-panel')).toBeInTheDocument());

    const notice = screen.getByTestId('gaps-cached-notice');
    expect(notice.className).toContain('notice-warning');
    expect(screen.getByText(/3 new notes/)).toBeInTheDocument();
    expect(screen.getByText(/were added to this subject since/)).toBeInTheDocument();
  });

  it('toggles the gap history timeline and shows deltas across snapshots', async () => {
    const gapItem = {
      name: 'Scheduling',
      level: 'Weak' as const,
      priority: 'Medium' as const,
      skill: 'Processes',
      domain: 'Operating Systems',
      importance: 2,
      why: 'x',
      prerequisites: [],
      blocked: false,
      learn: [],
      practice: [],
      next: null,
      sources: [],
      related_known: [],
      evidence: { strength: 0, exposure: 0, mentions: 1, documents: 1, quiz_errors: 0, retrieval_misses: 0 },
    };
    vi.mocked(endpoints.courses.gaps).mockResolvedValue({
      topics: [],
      concepts: [],
      classroom: { assignments: [], total: 0, pending: 0 },
      threshold: 0.5,
      document_count: 2,
      summary: { text: 'Saved summary.', priorities: [], strong_areas: [] },
      domain: 'Operating Systems',
      strengths: [],
      gaps: [gapItem],
      path: [],
      next: gapItem,
      coverage: { known: 0, gaps: 1, total: 1, percent: 0 },
      cached: true,
      analyzed_at: '2026-08-10T09:00:00Z',
      new_notes_since_analysis: 0,
    });
    vi.mocked(endpoints.courses.gapHistory).mockResolvedValue({
      history: [
        {
          analyzed_at: '2026-08-09T10:30:00Z',
          document_count: 2,
          gap_count: 2,
          strength_count: 0,
          coverage: { known: 0, gaps: 2, total: 2, percent: 0 },
          next: 'Scheduling',
          gaps: [
            { name: 'Scheduling', level: 'Not Found', priority: 'High' },
            { name: 'Virtualization', level: 'Not Found', priority: 'Medium' },
          ],
          strengths: [],
        },
        {
          analyzed_at: '2026-08-10T09:00:00Z',
          document_count: 3,
          gap_count: 1,
          strength_count: 1,
          coverage: { known: 1, gaps: 1, total: 2, percent: 50 },
          next: 'Scheduling',
          gaps: [{ name: 'Scheduling', level: 'Familiar', priority: 'High' }],
          strengths: [{ name: 'Virtualization', level: 'Strong' }],
        },
      ],
    });

    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('gap-analysis-panel')).toBeInTheDocument());

    // History hidden until toggled.
    expect(screen.queryByTestId('gap-history-view')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /History/ }));
    await waitFor(() => expect(screen.getByTestId('gap-history-view')).toBeInTheDocument());

    expect(endpoints.courses.gapHistory).toHaveBeenCalledWith(1);
    // Deltas computed against the previous snapshot: 1 resolved, 1 improved.
    expect(screen.getByText(/1 resolved/)).toBeInTheDocument();
    expect(screen.getByText(/1 improved/)).toBeInTheDocument();
    // No NEW-gap delta — both snapshots share the Scheduling gap.
    expect(screen.queryByText(/\+\d+ new/)).not.toBeInTheDocument();

    // Toggle off hides it again.
    fireEvent.click(screen.getByRole('button', { name: /Hide History/ }));
    expect(screen.queryByTestId('gap-history-view')).not.toBeInTheDocument();
  });

  it('renders the legacy gap fallback when the engine payload is absent', async () => {
    vi.mocked(endpoints.courses.gaps).mockResolvedValue({
      topics: [{ topic: 'Virtualization', normalized: 'virtualization', coverage: 0.25, documents: 1, is_gap: true }],
      concepts: [],
      classroom: { assignments: [], total: 0, pending: 0 },
      threshold: 0.5,
      document_count: 2,
    });

    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Gap Analysis/ }));
    await waitFor(() => expect(screen.getByTestId('gap-analysis-panel')).toBeInTheDocument());
    expect(screen.getByText(/Topics with thin coverage/)).toBeInTheDocument();
  });

  it('runs resync and shows the idempotent sync feedback', async () => {
    vi.mocked(endpoints.courses.resync).mockResolvedValue({
      kb: { created: 0, updated: 1, removed: 0, courses: 1, sources: 1, documents: 2, course_tags: 1, course_folders: 0, errors: [], synced_at: '2026-08-09T10:00:00' },
      classroom: { courses: 0, assignments: 0, source: 'mock' },
      content,
    });

    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Resync/ }));
    await waitFor(() => expect(screen.getByTestId('resync-message')).toBeInTheDocument());

    expect(endpoints.courses.resync).toHaveBeenCalledWith(1);
    expect(screen.getByText(/Second Brain synced/)).toBeInTheDocument();
    expect(screen.getByText(/Google Classroom: 0 course/)).toBeInTheDocument();
  });

  it('shows an API error state with a Retry action instead of a blank page', async () => {
    vi.mocked(endpoints.courses.content).mockRejectedValueOnce(new Error('API 500: boom'));

    renderDetail();
    await waitFor(() => expect(screen.getByText(/API 500: boom/)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Retry/ })).toBeInTheDocument();

    // Retry succeeds → the page renders normally.
    fireEvent.click(screen.getByRole('button', { name: /Retry/ }));
    await waitFor(() => expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument());
  });

  it('shows a graceful empty state when the subject has no documents', async () => {
    const empty = {
      ...content,
      second_brain: {
        ...content.second_brain,
        document_count: 0,
        documents: [],
        topics: [],
        unorganized_documents: [],
        concepts: [],
        graph: { nodes: [], edges: [], truncated: false, total_nodes: 0, total_edges: 0 },
      },
    };
    vi.mocked(endpoints.courses.content).mockResolvedValueOnce(empty);

    renderDetail();
    await waitFor(() => expect(screen.getByText(/No topics yet/)).toBeInTheDocument());
    expect(screen.getByText(/No documents found/)).toBeInTheDocument();
    expect(screen.getByTestId('subject-graph')).toBeInTheDocument(); // graph canvas empty-state
  });
});
