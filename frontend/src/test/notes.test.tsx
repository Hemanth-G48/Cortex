import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Notes } from '../pages/Notes';

const h = vi.hoisted(() => {
  const notes = [
    { id: 1, title: 'Integration Techniques', content: '# U-Substitution\nLet u = g(x)', course_id: 1, created_date: '2026-07-01', pinned: true, updated_at: null },
    { id: 2, title: 'BST Notes', content: 'Inorder traversal', course_id: 2, created_date: '2026-07-02', pinned: false, updated_at: null },
  ];
  return { notes, store: [...notes] };
});

vi.mock('../services/api', () => {
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({
        user: { id: 1, name: 'Alex', current_level: 5, total_xp: 2340, current_streak: 3, avatar: null, avatar_class: 'Wizard', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
      }),
      notes: {
        list: vi.fn().mockImplementation(() => Promise.resolve([...h.store])),
        create: vi.fn().mockImplementation((d) => {
          const created = { id: h.store.length + 1, ...d, pinned: false, updated_at: null };
          h.store.unshift(created);
          return Promise.resolve(created);
        }),
        update: vi.fn().mockImplementation((id, d) => {
          const idx = h.store.findIndex((n) => n.id === id);
          h.store[idx] = { ...h.store[idx], ...d, updated_at: '2026-08-03T00:00:00' };
          return Promise.resolve(h.store[idx]);
        }),
        delete: vi.fn().mockImplementation((id) => {
          const idx = h.store.findIndex((n) => n.id === id);
          if (idx >= 0) h.store.splice(idx, 1);
          return Promise.resolve({ ok: true });
        }),
        pin: vi.fn().mockImplementation((id) => {
          const n = h.store.find((x) => x.id === id)!;
          n.pinned = !n.pinned;
          return Promise.resolve({ id, pinned: n.pinned });
        }),
      },
      courses: {
        list: vi.fn().mockResolvedValue([
          { id: 1, title: 'Computer Science', credits: 3, user_id: 1, image_url: null, current_assignment: 0, total_assignments: 0, next_exam: null, total_exams: 0, status: 'In progress' },
        ]),
      },
    },
  };
});

describe('Notes editor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    h.store.length = 0;
    h.store.push(...h.notes);
  });

  it('renders the note list and selects the first note', async () => {
    render(<Notes />);
    await waitFor(() => expect(screen.getAllByText(/Integration Techniques/).length).toBeGreaterThan(0));
    expect(screen.getByText(/BST Notes/)).toBeInTheDocument();
    // Editor shows the selected note title + content
    expect(screen.getByDisplayValue('Integration Techniques')).toBeInTheDocument();
    expect(screen.getAllByText(/U-Substitution/).length).toBeGreaterThan(0);
  });

  it('edits and saves a note', async () => {
    render(<Notes />);
    await waitFor(() => expect(screen.getByDisplayValue('Integration Techniques')).toBeInTheDocument());

    const titleInput = screen.getByDisplayValue('Integration Techniques');
    fireEvent.change(titleInput, { target: { value: 'Integration — Updated' } });
    fireEvent.click(screen.getByText('💾 Save'));
    await waitFor(() => expect(screen.getByText('Saved ✓')).toBeInTheDocument());
  });

  it('creates a new note', async () => {
    render(<Notes />);
    await waitFor(() => expect(screen.getByDisplayValue('Integration Techniques')).toBeInTheDocument());

    fireEvent.click(screen.getByText('＋ New Note'));
    await waitFor(() => expect(screen.getByDisplayValue('Untitled')).toBeInTheDocument());
  });
});
