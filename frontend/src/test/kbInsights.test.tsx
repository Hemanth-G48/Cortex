import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { KbInsights } from '../pages/KbInsights';

vi.mock('../services/api', () => {
  const health = {
    score: 72.5,
    document_count: 10,
    edge_count: 12,
    signals: {
      orphans: { count: 1, document_ids: [7] },
      dead_links: { count: 0, edges: [] },
      stale_notes: { count: 2, document_ids: [1, 2] },
      unindexed_files: { count: 1, documents: [{ document_id: 3, missing: ['no_embeddings'] }] },
      coverage_gaps: [{ topic: 'untagged', covered: 5, coverage: 0.5 }],
    },
  };
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({ user: null }),
      kb: {
        health: vi.fn().mockResolvedValue(health),
        gaps: {
          all: vi.fn().mockResolvedValue({
            items: [{ topic: 'untagged', coverage: 0.5, is_gap: false }],
            gaps: [{ topic: 'cryptography', coverage: 0.1, is_gap: true }],
            threshold: 0.2,
            total: 1,
          }),
          concepts: vi.fn().mockResolvedValue({ items: [] }),
        },
        missingNotes: {
          list: vi.fn().mockResolvedValue({ items: [] }),
          generate: vi.fn().mockResolvedValue({ ok: true }),
          accept: vi.fn().mockResolvedValue({}),
          dismiss: vi.fn().mockResolvedValue({ ok: true }),
        },
        outdated: {
          review: vi.fn().mockResolvedValue({ items: [] }),
          scan: vi.fn().mockResolvedValue({ ok: true }),
          resolve: vi.fn().mockResolvedValue({ ok: true }),
        },
        memory: {
          get: vi.fn().mockResolvedValue({ items: [] }),
        },
      },
    },
  };
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <KbInsights />
    </MemoryRouter>,
  );

describe('KbInsights page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the health score, signals and gaps', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('73')).toBeInTheDocument());

    expect(screen.getByText('Orphans')).toBeInTheDocument();
    expect(screen.getByText('Dead links')).toBeInTheDocument();
    expect(screen.getByText('Stale notes')).toBeInTheDocument();
    expect(screen.getByText('Unindexed files')).toBeInTheDocument();
    expect(screen.getByText('Coverage gaps')).toBeInTheDocument();

    expect(screen.getByText('cryptography')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Capture note/ })).toBeInTheDocument();
  });

  it('shows doc-level detail for orphans', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Orphans')).toBeInTheDocument());
    // #7 appears in the signal detail and the quick-fix button.
    expect(screen.getAllByText(/#7/).length).toBeGreaterThan(0);
  });
});
