import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Subject } from '../pages/Subject';

vi.mock('../services/api', () => ({
  endpoints: {
    login: vi.fn().mockResolvedValue({
      user: { id: 1, name: 'Alex', current_level: 1, total_xp: 0, current_streak: 0, avatar: null, avatar_class: null, created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
    }),
    curriculum: {
      subject: vi.fn().mockResolvedValue({
        id: 1, program_id: 10, name: 'Data Structures', code: 'CS201', semester: 2, credits: 4, description: 'Intro to DS', is_active: true, unit_count: 2, created_at: null,
      }),
      units: vi.fn().mockResolvedValue([
        { id: 5, subject_id: 1, unit_number: 1, name: 'Arrays', description: null, is_active: true, created_at: null },
        { id: 6, subject_id: 1, unit_number: 2, name: 'Linked Lists', description: null, is_active: true, created_at: null },
      ]),
    },
    materials: {
      list: vi.fn().mockResolvedValue({ items: [], total: 3, page: 1, page_size: 20 }),
    },
    summaries: {
      generate: vi.fn().mockResolvedValue({
        summary: { content: 'Arrays are contiguous blocks of memory.', key_points: ['Covers memory layout', 'Covers complexity analysis'] },
        cached: false,
      }),
    },
  },
}));

const renderSubject = () =>
  render(
    <MemoryRouter initialEntries={['/subjects/1']}>
      <Routes>
        <Route path="/subjects/:id" element={<Subject />} />
      </Routes>
    </MemoryRouter>,
  );

describe('Subject page (SyllabusAI G9)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders subject info and its units with material counts', async () => {
    renderSubject();
    expect((await screen.findAllByText('Data Structures')).length).toBeGreaterThan(0);
    expect(screen.getByText('Arrays')).toBeInTheDocument();
    expect(screen.getByText('Linked Lists')).toBeInTheDocument();
    // useSubject annotates each unit with material_count = 3
    await waitFor(() => expect(screen.getAllByText('3 materials').length).toBe(2));
  });

  it('generates a multi-unit summary from selected units', async () => {
    renderSubject();
    await screen.findAllByText('Data Structures');

    fireEvent.click(screen.getByLabelText('Select unit 1 for summary'));
    fireEvent.click(screen.getByLabelText('Select unit 2 for summary'));
    fireEvent.click(screen.getByText('✨ Generate Summary'));

    await waitFor(() => expect(screen.getByText('Covers memory layout')).toBeInTheDocument());
    expect(screen.getByText(/Arrays are contiguous/)).toBeInTheDocument();
  });
});
