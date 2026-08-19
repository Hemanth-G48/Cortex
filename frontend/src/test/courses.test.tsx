import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Courses } from '../pages/Courses';
import { endpoints } from '../services/api';

const renderPage = () => render(<MemoryRouter><Courses /></MemoryRouter>);

vi.mock('../services/api', () => ({
  endpoints: {
    courses: {
      list: vi.fn().mockResolvedValue([]),
      syncStatus: vi.fn().mockResolvedValue({
        sources: 2,
        documents: 12,
        course_tags: 1,
        course_folders: 1,
        last_sync: {
          created: 1,
          updated: 0,
          removed: 0,
          courses: 1,
          sources: 2,
          documents: 12,
          course_tags: 1,
          course_folders: 1,
          errors: [],
          synced_at: '2026-08-09T10:00:00',
        },
        google: { configured: true, connected: false, email: null },
      }),
      syncKb: vi.fn().mockResolvedValue({ created: 0, updated: 0, removed: 0, courses: 0, course_tags: 0, course_folders: 0 }),
      resources: vi.fn().mockResolvedValue([]),
    },
    classroom: {
      courses: vi.fn().mockResolvedValue({ courses: [], source: 'mock' }),
    },
  },
}));

// The header renders NotificationsBell; keep it inert for this page test.
vi.mock('../components/NotificationsBell', () => ({
  NotificationsBell: () => null,
}));

describe('Courses page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the sync-status strip with KB counters and Google state', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('sync-status')).toBeInTheDocument());
    expect(screen.getByText(/2 sources/)).toBeInTheDocument();
    expect(screen.getByText(/12 documents/)).toBeInTheDocument();
    expect(screen.getByText(/1 course tag/)).toBeInTheDocument();
    expect(screen.getByText(/Google not connected/)).toBeInTheDocument();
  });

  it('shows empty-state guidance when no courses exist', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/No courses yet/)).toBeInTheDocument());
    // The guidance mentions the course:<name> tagging convention (both in the
    // empty-state notice and the Second Brain group hint).
    expect(screen.getAllByText(/course:<name>/).length).toBeGreaterThan(0);
  });

  it('shows all subjects grouped by source in fully-visible grids', async () => {
    vi.mocked(endpoints.courses.list).mockResolvedValue([
      { id: 1, title: 'Operating Systems', image_url: null, user_id: 1, credits: 3, source_type: 'kb_tag', kb_tag_id: 5, kb_document_count: 12, status: 'In progress', current_assignment: 0, total_assignments: 12, next_exam: null, total_exams: 0 },
      { id: 2, title: 'Networks', image_url: null, user_id: 1, credits: 3, source_type: 'kb_tag', kb_tag_id: 6, kb_document_count: 3, status: 'Not started', current_assignment: 0, total_assignments: 3, next_exam: null, total_exams: 0 },
      { id: 3, title: 'Biology 101', image_url: null, user_id: 1, credits: 3, source_type: 'classroom', status: 'In progress', current_assignment: 2, total_assignments: 5, next_exam: null, total_exams: 0 },
      { id: 4, title: 'Spanish', image_url: null, user_id: 1, credits: 3, source_type: 'manual', status: 'Completed', current_assignment: 0, total_assignments: 0, next_exam: null, total_exams: 0 },
      { id: 5, title: 'Algorithms', image_url: null, user_id: 1, credits: 3, source_type: 'kb_folder', kb_source_id: 3, kb_folder_path: 'Algorithms', kb_document_count: 7, status: 'In progress', current_assignment: 0, total_assignments: 7, next_exam: null, total_exams: 0, description: 'Graphs, sorting and complexity.', color: '#22c55e' },
    ]);
    renderPage();
    await waitFor(() => expect(screen.getByText('Operating Systems')).toBeInTheDocument());
    // Each source gets its own clearly-labelled group (as section headings).
    expect(screen.getByRole('heading', { name: /Second Brain/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Google Classroom/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Manual/ })).toBeInTheDocument();
    // Second Brain subjects (tag- AND folder-derived) show their real note counts.
    expect(screen.getByText(/12 notes/)).toBeInTheDocument();
    expect(screen.getByText(/7 notes/)).toBeInTheDocument();
    expect(screen.getByText('Algorithms')).toBeInTheDocument();
    // Folder-level metadata surfaces on the card (description + accent dot).
    expect(screen.getByText('Graphs, sorting and complexity.')).toBeInTheDocument();
    expect(screen.getByText('Networks')).toBeInTheDocument();
    expect(screen.getByText('Biology 101')).toBeInTheDocument();
    expect(screen.getByText('Spanish')).toBeInTheDocument();
  });

  it('labels classroom sync as offline demo when Google is not connected', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('sync-status')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Sync Google Classroom/ }));
    await waitFor(() => expect(screen.getByText(/offline demo/)).toBeInTheDocument());
  });
});
