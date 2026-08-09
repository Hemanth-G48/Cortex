import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CommandPalette } from '../components/kb/CommandPalette';

vi.mock('../services/api', () => {
  const groups = {
    vault: [{ id: 1, title: 'hello.md', domain: 'vault', snippet: 'the quick fox', url: '/knowledge-base', score: 0.9 }],
    tasks: [{ id: 5, title: 'Finish essay', domain: 'tasks', snippet: 'task', url: '/dashboard', score: 1 }],
    materials: [{ id: 9, title: 'lecture notes', domain: 'materials', snippet: 'desc', url: '/curriculum', score: 1 }],
  };
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({ user: null }),
      search: {
        global: vi.fn().mockResolvedValue({
          items: Object.values(groups).flat(),
          groups,
          total: 3,
          query: 'quick',
          domains: ['vault', 'tasks', 'materials'],
        }),
      },
    },
  };
});

const openWithShortcut = () => {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, shiftKey: true }));
};

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('opens on Ctrl+Shift+K and shows the idle prompt', async () => {
    render(
      <MemoryRouter>
        <CommandPalette />
      </MemoryRouter>,
    );
    openWithShortcut();
    await waitFor(() => expect(screen.getByLabelText('Global search query')).toBeInTheDocument());
    expect(screen.getByText(/Start typing to search/)).toBeInTheDocument();
  });

  it('runs the global search and groups results by domain', async () => {
    render(
      <MemoryRouter>
        <CommandPalette />
      </MemoryRouter>,
    );
    openWithShortcut();
    const input = await screen.findByLabelText('Global search query');
    fireEvent.change(input, { target: { value: 'quick' } });

    await waitFor(() => expect(screen.getByText('hello.md')).toBeInTheDocument());
    expect(screen.getByText('Finish essay')).toBeInTheDocument();
    expect(screen.getByText('lecture notes')).toBeInTheDocument();
    // Group headers render the capitalized label (CSS uppercases the display).
    expect(screen.getByText(/Vault \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/Tasks \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/Materials \(1\)/)).toBeInTheDocument();
  });

  it('closes on Escape', async () => {
    render(
      <MemoryRouter>
        <CommandPalette />
      </MemoryRouter>,
    );
    openWithShortcut();
    const input = await screen.findByLabelText('Global search query');
    fireEvent.keyDown(input, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByLabelText('Global search query')).not.toBeInTheDocument());
  });
});
