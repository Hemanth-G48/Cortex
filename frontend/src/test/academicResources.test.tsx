import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AcademicResourcesGrid } from '../components/resources/AcademicResourcesGrid';

vi.mock('../services/api', () => ({
  endpoints: {
    courses: {
      resources: vi.fn(),
    },
  },
}));

import { endpoints } from '../services/api';

const mockResources = endpoints.courses.resources as ReturnType<typeof vi.fn>;

describe('AcademicResourcesGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders fetched resources (KB folders + Classroom links)', async () => {
    mockResources.mockResolvedValue([
      { id: 'sb-1', title: 'OS Notes', type: 'folder', url: '/tmp/os', description: 'local_dir source' },
      { id: 'gc-abc', title: 'Biology', type: 'classroom', url: 'https://classroom.google.com/c/1', description: 'Google Classroom' },
    ]);

    render(<AcademicResourcesGrid />);

    await waitFor(() => {
      expect(screen.getByText('OS Notes')).toBeInTheDocument();
    });
    expect(screen.getByText('Biology')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /OS Notes/ })).toHaveAttribute('href', '/tmp/os');
  });

  it('falls back to static defaults when the API returns nothing', async () => {
    mockResources.mockResolvedValue([]);

    render(<AcademicResourcesGrid />);

    await waitFor(() => {
      expect(screen.getByText('Library Portal')).toBeInTheDocument();
    });
  });

  it('keeps defaults when the API fails', async () => {
    mockResources.mockRejectedValue(new Error('boom'));

    render(<AcademicResourcesGrid />);

    await waitFor(() => {
      expect(screen.getByText('Google Scholar')).toBeInTheDocument();
    });
  });
});
