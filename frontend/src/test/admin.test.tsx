import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Admin } from '../pages/Admin';

vi.mock('../services/api', () => ({
  endpoints: {
    login: vi.fn().mockResolvedValue({
      user: { id: 1, name: 'Alex', current_level: 1, total_xp: 0, current_streak: 0, avatar: null, avatar_class: null, created_at: '2026-01-01', current_weight: null, initial_weight: null, target_weight: null, membership_status: null, next_payment_date: null },
    }),
    admin: {
      allInstitutions: vi.fn().mockResolvedValue([
        { id: 1, name: 'National University', short_name: 'NU', description: null, is_active: true, created_at: null },
        { id: 2, name: 'City College', short_name: 'CC', description: null, is_active: false, created_at: null },
      ]),
      createInstitution: vi.fn().mockResolvedValue({ id: 3, name: 'New College', short_name: 'NC', description: null, is_active: false, created_at: null }),
      toggleInstitution: vi.fn().mockResolvedValue({ ok: true, is_active: false }),
      createProgram: vi.fn().mockResolvedValue({ id: 99 }),
      createSubject: vi.fn().mockResolvedValue({ id: 99 }),
      createUnit: vi.fn().mockResolvedValue({ id: 99 }),
    },
    curriculum: {
      programs: vi.fn().mockResolvedValue([]),
      subjects: vi.fn().mockResolvedValue([]),
      units: vi.fn().mockResolvedValue([]),
    },
  },
}));

describe('Admin page (SyllabusAI G11)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('lists all institutions with status badges', async () => {
    render(<Admin />);
    expect((await screen.findAllByText('National University')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('City College')).length).toBeGreaterThan(0);
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('toggles institution status on approve', async () => {
    render(<Admin />);
    const { endpoints } = await import('../services/api');
    fireEvent.click(await screen.findByText('Approve'));
    await waitFor(() => expect(endpoints.admin.toggleInstitution).toHaveBeenCalledWith(2));
  });

  it('creates an institution through the form', async () => {
    render(<Admin />);
    const { endpoints } = await import('../services/api');
    await screen.findAllByText('National University');

    fireEvent.change(screen.getByLabelText('Institution name'), { target: { value: 'New College' } });
    fireEvent.change(screen.getByLabelText('Short name'), { target: { value: 'NC' } });
    fireEvent.click(screen.getByText('＋ Create'));

    await waitFor(() =>
      expect(endpoints.admin.createInstitution).toHaveBeenCalledWith({
        name: 'New College',
        short_name: 'NC',
        description: null,
      }),
    );
  });
});
