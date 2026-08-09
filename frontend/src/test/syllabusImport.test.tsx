import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SyllabusImport } from '../pages/SyllabusImport';

vi.mock('../services/api', () => {
  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({
        user: { id: 1, name: 'Alex', current_level: 5, total_xp: 2340, current_streak: 3, avatar: null, avatar_class: 'Wizard', created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
      }),
      courses: {
        list: vi.fn().mockResolvedValue([
          { id: 1, title: 'English 101', credits: 3, user_id: 1, image_url: null, current_assignment: 0, total_assignments: 0, next_exam: null, total_exams: 0, status: 'In progress' },
        ]),
      },
      assignments: {
        list: vi.fn().mockResolvedValue([]),
        create: vi.fn().mockResolvedValue({}),
      },
      ai: {
        syllabus: vi.fn().mockResolvedValue({
          assignments: [
            { title: 'Essay 1: Personal Narrative', due_date: '2026-02-14', course: 'English 101', priority: 'high' },
            { title: 'Midterm Exam', due_date: '2026-03-10', course: 'English 101', priority: 'high' },
          ],
          ai_used: false,
        }),
      },
      subjects: {
        import: vi.fn().mockResolvedValue({
          profile: {
            id: 7,
            user_id: 1,
            curriculum_subject_id: null,
            semester: 'Spring 2026',
            status: 'proposed',
            created_at: '2026-01-01T00:00:00',
            updated_at: '2026-01-01T00:00:00',
            parsed: {
              title: 'Data Structures',
              credits: 3,
              grading: '40% exams',
              units: [
                {
                  title: 'Arrays',
                  description: null,
                  topics: [{ name: 'Dynamic arrays', outcomes: ['can analyse amortized cost'] }],
                  deadlines: [],
                },
              ],
            },
            topics_count: 0,
            units_count: 0,
          },
          fallback: false,
        }),
        importFile: vi.fn().mockRejectedValue(new Error('not used')),
        proposals: vi.fn(),
        list: vi.fn(),
        get: vi.fn(),
        confirm: vi.fn().mockResolvedValue({
          profile: {
            id: 7,
            user_id: 1,
            curriculum_subject_id: 3,
            semester: 'Spring 2026',
            status: 'confirmed',
            created_at: '2026-01-01T00:00:00',
            updated_at: '2026-01-01T00:00:00',
            parsed: {
              title: 'Data Structures',
              credits: 3,
              grading: '40% exams',
              units: [],
            },
            topics_count: 0,
            units_count: 0,
          },
        }),
        reject: vi.fn().mockResolvedValue({
          ok: true,
          profile: {
            id: 7,
            user_id: 1,
            curriculum_subject_id: null,
            semester: 'Spring 2026',
            status: 'rejected',
            created_at: '2026-01-01T00:00:00',
            updated_at: '2026-01-01T00:00:00',
            parsed: { title: 'Data Structures', credits: 3, grading: null, units: [] },
            topics_count: 0,
            units_count: 0,
          },
        }),
        topics: {
          generate: vi.fn(),
          list: vi.fn(),
          confirm: vi.fn(),
          reject: vi.fn(),
          merge: vi.fn(),
          patch: vi.fn(),
          recompute: vi.fn(),
        },
        matchUnits: { list: vi.fn(), confirm: vi.fn() },
        dependencies: { get: vi.fn(), generate: vi.fn(), add: vi.fn(), remove: vi.fn() },
        roadmap: { generate: vi.fn(), get: vi.fn() },
        timeBudget: vi.fn(),
        pacing: vi.fn(),
        outcomes: { get: vi.fn(), add: vi.fn(), expand: vi.fn(), complete: vi.fn() },
      },
    },
  };
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <SyllabusImport />
    </MemoryRouter>,
  );

describe('SyllabusImport page — Phase 5 subject flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('parses pasted syllabus text into a proposal with a parsed preview', async () => {
    renderPage();
    const textarea = screen.getByPlaceholderText('Paste your syllabus text here...');
    fireEvent.change(textarea, { target: { value: 'Data Structures syllabus with an arrays unit.' } });
    fireEvent.click(screen.getByText('✨ Parse Syllabus into a Subject'));

    await waitFor(() => expect(screen.getByText('Data Structures')).toBeInTheDocument());
    expect(screen.getByText('proposed')).toBeInTheDocument();
    expect(screen.getByText(/Spring 2026/)).toBeInTheDocument();
    // parsed-syllabus preview (units + topics)
    expect(screen.getByText('Arrays')).toBeInTheDocument();
    expect(screen.getByText('Dynamic arrays')).toBeInTheDocument();
    // review step — edit name before any DB write
    const nameInput = screen.getByLabelText('Name');
    fireEvent.change(nameInput, { target: { value: 'Data Structures II' } });
  });

  it('confirms a proposal and exposes the workspace link', async () => {
    renderPage();
    const textarea = screen.getByPlaceholderText('Paste your syllabus text here...');
    fireEvent.change(textarea, { target: { value: 'Data Structures syllabus.' } });
    fireEvent.click(screen.getByText('✨ Parse Syllabus into a Subject'));

    await waitFor(() => expect(screen.getByText('proposed')).toBeInTheDocument());
    fireEvent.click(screen.getByText('✅ Confirm & Create Subject'));

    await waitFor(() => expect(screen.getByText('Open Subject Workspace →')).toBeInTheDocument());
    expect(screen.getByText('confirmed')).toBeInTheDocument();
  });

  it('rejects a proposal without writing curriculum rows', async () => {
    renderPage();
    const textarea = screen.getByPlaceholderText('Paste your syllabus text here...');
    fireEvent.change(textarea, { target: { value: 'Data Structures syllabus.' } });
    fireEvent.click(screen.getByText('✨ Parse Syllabus into a Subject'));

    await waitFor(() => expect(screen.getByText('proposed')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Reject'));

    await waitFor(() => expect(screen.getByText('rejected')).toBeInTheDocument());
    expect(screen.getByText('↻ Try a different syllabus')).toBeInTheDocument();
  });
});

describe('SyllabusImport page — legacy assignments flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('extracts assignments from pasted text via the legacy mode', async () => {
    renderPage();
    fireEvent.click(screen.getByText('📝 Extract Assignments (legacy)'));
    const textarea = screen.getByPlaceholderText('Paste your syllabus text here...');
    fireEvent.change(textarea, { target: { value: 'English 101 syllabus with an essay due in February.' } });
    fireEvent.click(screen.getByText('✨ Extract Assignments'));

    await waitFor(() => expect(screen.getByText('Found 2 assignments')).toBeInTheDocument());
    expect(screen.getByText('Essay 1: Personal Narrative')).toBeInTheDocument();
    expect(screen.getByText('Midterm Exam')).toBeInTheDocument();
  });

  it('imports all extracted assignments', async () => {
    renderPage();
    fireEvent.click(screen.getByText('📝 Extract Assignments (legacy)'));
    const textarea = screen.getByPlaceholderText('Paste your syllabus text here...');
    fireEvent.change(textarea, { target: { value: 'Some syllabus text.' } });
    fireEvent.click(screen.getByText('✨ Extract Assignments'));

    await waitFor(() => expect(screen.getByText('Found 2 assignments')).toBeInTheDocument());
    fireEvent.click(screen.getByText('＋ Add All to Assignments'));
    await waitFor(() => expect(screen.getByText('✅ Imported!')).toBeInTheDocument());
  });
});
