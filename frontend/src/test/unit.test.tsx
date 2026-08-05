import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Unit } from '../pages/Unit';

vi.mock('../services/api', () => ({
  endpoints: {
    login: vi.fn().mockResolvedValue({
      user: { id: 1, name: 'Alex', current_level: 1, total_xp: 0, current_streak: 0, avatar: null, avatar_class: null, created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
    }),
    curriculum: {
      subject: vi.fn().mockResolvedValue({
        id: 1, program_id: 10, name: 'Data Structures', code: 'CS201', semester: 2, credits: 4, description: null, is_active: true, unit_count: 1, created_at: null,
      }),
      units: vi.fn().mockResolvedValue([
        { id: 7, subject_id: 1, unit_number: 1, name: 'Arrays', description: 'Memory layout and indexing', is_active: true, created_at: null },
      ]),
      unit: vi.fn().mockResolvedValue({ id: 7, subject_id: 1, unit_number: 1, name: 'Arrays', description: 'Memory layout and indexing', is_active: true, created_at: null }),
    },
    courses: {
      list: vi.fn().mockResolvedValue([
        { id: 1, title: 'Data Structures', image_url: null, current_assignment: 0, total_assignments: 0, next_exam: null, total_exams: 0, status: 'In progress', user_id: 1, credits: 3, curriculum_subject_id: null },
      ]),
      update: vi.fn().mockResolvedValue({ id: 1 }),
    },
    materials: {
      list: vi.fn().mockResolvedValue({
        items: [
          { id: 50, unit_id: 7, title: 'lecture-1.pdf', description: null, file_type: 'pdf', file_url: '/uploads/x.pdf', file_size: 2048, original_file_name: 'lecture-1.pdf', view_count: 3, download_count: 1, is_active: true, extracted_text: null, created_at: '2026-01-01' },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      }),
      upload: vi.fn().mockResolvedValue({ id: 51 }),
      downloadUrl: vi.fn((id: number) => `/api/materials/${id}/download`),
    },
    quizzes: {
      generate: vi.fn().mockResolvedValue({
        id: 9,
        unit_id: 7,
        difficulty: 'medium',
        questions: [
          { question: 'What is 2+2?', options: ['3', '4', '5', '6'], correct_index: 1, explanation: 'Basic addition.' },
          { question: 'Capital of France?', options: ['Berlin', 'Madrid', 'Paris', 'Rome'], correct_index: 2, explanation: 'Geography.' },
        ],
        created_at: null,
      }),
      attempt: vi.fn().mockResolvedValue({
        score: 2,
        total: 2,
        percentage: 100,
        results: [
          { question_index: 0, selected: 1, correct: true, correct_index: 1, explanation: 'Basic addition.' },
          { question_index: 1, selected: 2, correct: true, correct_index: 2, explanation: 'Geography.' },
        ],
        xp_awarded: 25,
      }),
      history: vi.fn().mockResolvedValue([]),
    },
    summaries: {
      generate: vi.fn().mockResolvedValue({ summary: { content: 'Unit summary.', key_points: ['KP'] }, cached: true }),
    },
  },
}));

const renderUnit = () =>
  render(
    <MemoryRouter initialEntries={['/units/7']}>
      <Routes>
        <Route path="/units/:id" element={<Unit />} />
      </Routes>
    </MemoryRouter>,
  );

describe('Unit page (SyllabusAI G9/G10)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders unit info and the material library', async () => {
    renderUnit();
    expect(await screen.findByText('Unit 1 — Arrays')).toBeInTheDocument();
    expect(screen.getByText('lecture-1.pdf')).toBeInTheDocument();
    expect(screen.getByText('PDF')).toBeInTheDocument();
    expect(screen.getByText(/1 downloads/)).toBeInTheDocument();
  });

  it('runs the full quiz flow to a scored result', async () => {
    renderUnit();
    fireEvent.click(await screen.findByText('🧠 Generate Quiz'));

    await waitFor(() => expect(screen.getByText('What is 2+2?')).toBeInTheDocument());

    fireEvent.click(screen.getByText('4'));
    fireEvent.click(screen.getByText('Next →'));
    fireEvent.click(screen.getByText('Paris'));
    fireEvent.click(screen.getByText('Submit Quiz'));

    await waitFor(() => expect(screen.getByText('You scored 2 / 2')).toBeInTheDocument());
    expect(screen.getByText('Excellent!')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
    // G13 (Phase 85): passing quiz shows the XP award banner.
    expect(screen.getByText('⚡ +25 XP earned for passing!')).toBeInTheDocument();
  });

  it('generates a single-unit summary with the cached notice', async () => {
    renderUnit();
    fireEvent.click(await screen.findByText('✨ Generate Summary'));

    await waitFor(() => expect(screen.getByText('Unit summary.')).toBeInTheDocument());
    expect(screen.getByText('cached')).toBeInTheDocument();
  });
});
