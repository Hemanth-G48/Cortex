import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { VaultSearch } from '../pages/VaultSearch';

vi.mock('../services/api', () => {
  const items = [
    {
      chunk_id: 11,
      document_id: 1,
      seq: 0,
      title: 'notes/hello.md',
      snippet: 'The <mark>quick</mark> brown fox',
      score: 0.9,
      mode: 'hybrid',
      source_path: 'notes/hello.md',
      heading_path: 'Intro',
      doc_type: 'md',
      doc_date: null,
      char_start: 12,
      char_end: 100,
      sources: ['fts', 'semantic'],
    },
    {
      chunk_id: 22,
      document_id: 2,
      seq: 1,
      title: 'papers/paper.pdf',
      snippet: 'another result',
      score: 0.7,
      mode: 'hybrid',
      source_path: 'papers/paper.pdf',
      heading_path: null,
      doc_type: 'pdf',
      doc_date: '2024-06-15',
      char_start: 3500,
      char_end: 4200,
      sources: ['fts'],
    },
  ];
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({ user: null }),
      kb: {
        search: {
          run: vi.fn().mockResolvedValue({
            items,
            total: 2,
            page: 1,
            page_size: 10,
            mode: 'hybrid',
            original_query: 'quick',
            expanded_query: 'quick',
          }),
          feedback: vi.fn().mockResolvedValue({ ok: true, event_id: 1 }),
          events: vi.fn(),
          purge: vi.fn(),
        },
      },
    },
  };
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <VaultSearch />
    </MemoryRouter>,
  );

describe('VaultSearch page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows an empty state before any query', () => {
    renderPage();
    expect(screen.getByText(/Search your vault/)).toBeInTheDocument();
  });

  it('runs a search and renders citation cards with highlighted snippets', async () => {
    renderPage();
    const input = screen.getByLabelText('Search query');
    fireEvent.change(input, { target: { value: 'quick' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => expect(screen.getByText('notes/hello.md')).toBeInTheDocument());
    // The path appears both as the title and the citation line.
    expect(screen.getAllByText(/papers\/paper\.pdf/).length).toBeGreaterThan(0);
    // <mark> highlight from FTS snippet tokens + retriever source chips.
    expect(screen.getByText('quick')).toBeInTheDocument();
    expect(screen.getAllByText('fts').length).toBeGreaterThan(0);
    expect(screen.getByText('semantic')).toBeInTheDocument();
  });

  it('shows the expanded-query hint when the query was rewritten', async () => {
    const { endpoints } = await import('../services/api');
    (endpoints.kb.search.run as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      mode: 'hybrid',
      original_query: 'ml',
      expanded_query: 'ml OR machine learning',
    });

    renderPage();
    const input = screen.getByLabelText('Search query');
    // Typing auto-runs the search (debounced by the effect) — that call
    // consumes the mockResolvedValueOnce with the expanded query.
    fireEvent.change(input, { target: { value: 'ml' } });

    await waitFor(() => expect(screen.getByText(/expanded:/)).toBeInTheDocument());
    expect(screen.getByText(/machine learning/)).toBeInTheDocument();
  });

  it('renders the mode toggle and switches modes', async () => {
    const { endpoints } = await import('../services/api');
    renderPage();
    expect(screen.getByRole('button', { name: 'Keyword' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Semantic' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Hybrid' })).toBeInTheDocument();

    // Give the page a query first so mode switches actually trigger a fetch.
    const input = screen.getByLabelText('Search query');
    fireEvent.change(input, { target: { value: 'ml' } });
    await waitFor(() => expect(endpoints.kb.search.run).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: 'Semantic' }));
    await waitFor(() =>
      expect(endpoints.kb.search.run).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ mode: 'semantic' })),
    );
  });
});
