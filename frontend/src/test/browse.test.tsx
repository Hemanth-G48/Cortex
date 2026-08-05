import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Browse } from '../pages/Browse';

vi.mock('../services/api', () => ({
  endpoints: {
    login: vi.fn().mockResolvedValue({
      user: { id: 1, name: 'Alex', current_level: 1, total_xp: 0, current_streak: 0, avatar: null, avatar_class: null, created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
    }),
    curriculum: {
      institutions: vi.fn().mockResolvedValue([
        { id: 1, name: 'National University of Science', short_name: 'NUS', description: 'Public research university', is_active: true, created_at: null },
        { id: 2, name: 'City College', short_name: 'CC', description: null, is_active: false, created_at: null },
      ]),
      programs: vi.fn().mockImplementation((institutionId: number) =>
        Promise.resolve(institutionId === 1 ? [
          { id: 10, institution_id: 1, name: 'B.Sc. Computer Science', code: 'CS', description: null, duration: 8, is_active: true, created_at: null },
          { id: 11, institution_id: 1, name: 'B.Sc. Mathematics', code: 'MA', description: null, duration: 8, is_active: true, created_at: null },
        ] : []),
      ),
      subjects: vi.fn().mockResolvedValue([
        { id: 100, program_id: 10, name: 'Data Structures', code: 'CS201', semester: 2, credits: 4, description: null, is_active: true, unit_count: 3, created_at: null },
        { id: 101, program_id: 10, name: 'Calculus', code: 'MATH101', semester: 1, credits: 3, description: null, is_active: true, unit_count: 2, created_at: null },
      ]),
    },
  },
}));

const renderBrowse = () =>
  render(
    <MemoryRouter>
      <Browse />
    </MemoryRouter>,
  );

describe('Browse page (SyllabusAI G8)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the institution list with status badges', async () => {
    renderBrowse();
    expect(await screen.findByText('National University of Science')).toBeInTheDocument();
    expect(screen.getByText('City College')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('cascades: selecting an institution loads its programs', async () => {
    renderBrowse();
    fireEvent.click(await screen.findByText('National University of Science'));

    await waitFor(() => expect(screen.getByText('B.Sc. Computer Science')).toBeInTheDocument());
    expect(screen.getByText('B.Sc. Mathematics')).toBeInTheDocument();
  });

  it('selecting a program shows semester-grouped subjects', async () => {
    renderBrowse();
    fireEvent.click(await screen.findByText('National University of Science'));
    fireEvent.click(await screen.findByText('B.Sc. Computer Science'));

    await waitFor(() => expect(screen.getByText('Data Structures')).toBeInTheDocument());
    // 'Semester N' appears both as the group heading and inside subject cards
    expect(screen.getAllByText('Semester 2').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Semester 1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Calculus')).toBeInTheDocument();
  });
});
