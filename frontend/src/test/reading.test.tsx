import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Reading } from '../pages/Reading';

vi.mock('../services/api', () => {
  const books = [
    {
      id: 1,
      title: 'The Pragmatic Programmer',
      author: 'David Thomas',
      category: 'reading' as const,
      cover_url: null,
      file_url: 'https://example.com/pragmatic.pdf',
      created_at: '2026-08-01T00:00:00',
    },
    {
      id: 2,
      title: 'Design Patterns',
      author: 'Gang of Four',
      category: 'finished' as const,
      cover_url: null,
      file_url: null,
      created_at: '2026-07-15T00:00:00',
    },
  ];
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({ user: null }),
    },
    bookApi: {
      list: vi.fn().mockResolvedValue({ items: books, total: 2, page: 1, page_size: 20 }),
      create: vi.fn().mockResolvedValue(books[0]),
      update: vi.fn().mockResolvedValue(books[0]),
      remove: vi.fn().mockResolvedValue({ ok: true }),
      insights: vi.fn().mockResolvedValue({
        total: 2,
        finished: 1,
        reading: 1,
        want: 0,
        completion_pct: 50,
        per_author: { 'David Thomas': 1, 'Gang of Four': 1 },
      }),
      uploadFile: vi.fn().mockResolvedValue({ url: 'https://example.com/uploaded.pdf', filename: 'test.pdf' }),
    },
  };
});

describe('Reading page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders book titles', async () => {
    render(<Reading />);
    await waitFor(() => expect(screen.getByText('The Pragmatic Programmer')).toBeInTheDocument());
    expect(screen.getByText('Design Patterns')).toBeInTheDocument();
  });

  it('renders the tab bar', async () => {
    render(<Reading />);
    await waitFor(() => expect(screen.getByText('The Pragmatic Programmer')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reading' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Finished' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Want' })).toBeInTheDocument();
  });

  it('renders the insights section', async () => {
    render(<Reading />);
    await waitFor(() => expect(screen.getByText('📊 Reading Insights')).toBeInTheDocument());
    expect(screen.getByText('Total')).toBeInTheDocument();
    expect(screen.getByText('Completion')).toBeInTheDocument();
  });
});