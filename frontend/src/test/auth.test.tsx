import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Login } from '../pages/Login';
import { RoleGate } from '../components/auth/RoleGate';
import { authApi } from '../services/api';

vi.mock('../services/api', async () => {
  vi.importActual('../services/api');
  return {
    authApi: {
      signup: vi.fn(),
      login: vi.fn(),
      me: vi.fn(),
      logout: vi.fn(async () => {
        localStorage.removeItem('student_os_token');
        return { ok: true } as const;
      }),
    },
  };
});

vi.mock('../hooks/useAuth', async () => {
  vi.importActual('../hooks/useAuth');
  return {
    useAuth: vi.fn(() => ({
      user: null,
      token: null,
      role: null,
      loading: false,
      isAuthenticated: false,
      login: async (d?: { identifier?: string; password?: string }) => {
        const r = await authApi.login(d ?? {});
        localStorage.setItem('student_os_token', r.token);
        return r;
      },
      signup: async (d: { name: string; username?: string; email?: string; password: string; role: 'student' | 'teacher'; teacher_secret?: string }) => {
        const r = await authApi.signup(d);
        localStorage.setItem('student_os_token', r.token);
        return r;
      },
      logout: async () => {
        await authApi.logout();
      },
      refreshMe: async () => {},
    })),
  };
});

const mockLogin = vi.mocked(authApi.login);
const mockSignup = vi.mocked(authApi.signup);

function renderWithRouter(ui: React.ReactElement, initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      {ui}
    </MemoryRouter>
  );
}

// Both the mode tab and the submit button carry the same label ("Sign Up"/"Log In");
// the submit button is rendered after the tab, so index [1] targets the submit.
function submitForm(label: string) {
  fireEvent.click(screen.getAllByRole('button', { name: label })[1]);
}

describe('Login page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders signup form by default', () => {
    renderWithRouter(<Login />);
    expect(screen.getByLabelText(/^Name$/i)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Sign Up' }).length).toBeGreaterThan(0);
  });

  it('switches to login mode when Log In tab is clicked', () => {
    renderWithRouter(<Login />);
    fireEvent.click(screen.getByRole('button', { name: 'Log In' }));
    expect(screen.getByLabelText(/Identifier/i)).toBeInTheDocument();
  });

  it('shows teacher secret field when Teacher role is selected', () => {
    renderWithRouter(<Login />);
    fireEvent.change(screen.getByLabelText(/Role/i), { target: { value: 'teacher' } });
    expect(screen.getByLabelText(/Teacher Secret/i)).toBeInTheDocument();
  });

  it('hides teacher secret field when Student role is selected', () => {
    renderWithRouter(<Login />);
    fireEvent.change(screen.getByLabelText(/Role/i), { target: { value: 'student' } });
    expect(screen.queryByLabelText(/Teacher Secret/i)).not.toBeInTheDocument();
  });

  it('calls authApi.signup on signup form submit', async () => {
    mockSignup.mockResolvedValue({ user: { id: 1, name: 'Alex', role: 'student' } as never, token: 'tok' });

    renderWithRouter(<Login />);
    fireEvent.change(screen.getByLabelText(/^Name$/i), { target: { value: 'Alex' } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'pass123' } });
    submitForm('Sign Up');

    await waitFor(() => expect(mockSignup).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Alex', password: 'pass123', role: 'student' })
    ));
  });

  it('calls authApi.login with credentials on login form submit', async () => {
    mockLogin.mockResolvedValue({ user: { id: 1, name: 'Alex', role: 'student' } as never, token: 'tok' });

    renderWithRouter(<Login />);
    fireEvent.click(screen.getByRole('button', { name: 'Log In' }));
    fireEvent.change(screen.getByLabelText(/Identifier/i), { target: { value: 'alex@test.com' } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'pass' } });
    submitForm('Log In');

    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith(
      expect.objectContaining({ identifier: 'alex@test.com', password: 'pass' })
    ));
  });

  it('calls authApi.login with empty object for legacy login', async () => {
    mockLogin.mockResolvedValue({ user: { id: 1, name: 'Alex', role: 'student' } as never, token: 'tok' });

    renderWithRouter(<Login />);
    fireEvent.click(screen.getByRole('button', { name: 'Log In' }));
    submitForm('Log In');

    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith({}));
  });

  it('shows error on signup failure', async () => {
    mockSignup.mockRejectedValue(new Error('Email already exists'));

    renderWithRouter(<Login />);
    fireEvent.change(screen.getByLabelText(/^Name$/i), { target: { value: 'Alex' } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'pass' } });
    submitForm('Sign Up');

    await waitFor(() => expect(screen.getByText('Email already exists')).toBeInTheDocument());
  });

  it('stores token in localStorage after successful login', async () => {
    mockLogin.mockResolvedValue({ user: { id: 1, name: 'Alex', role: 'student' } as never, token: 'tok123' });

    renderWithRouter(<Login />);
    fireEvent.click(screen.getByRole('button', { name: 'Log In' }));
    fireEvent.change(screen.getByLabelText(/Identifier/i), { target: { value: 'a' } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'p' } });
    submitForm('Log In');

    await waitFor(() => expect(localStorage.getItem('student_os_token')).toBe('tok123'));
  });
});

describe('RoleGate', () => {
  it('renders children when role matches', async () => {
    const { useAuth } = await import('../hooks/useAuth');
    vi.mocked(useAuth).mockReturnValue({ user: { id: 1, name: 'T', role: 'teacher', token: 't' } as never, token: 't', role: 'teacher', loading: false, isAuthenticated: true, login: vi.fn(), signup: vi.fn(), logout: vi.fn(), refreshMe: vi.fn() });

    const { container } = render(
      <MemoryRouter>
        <RoleGate role="teacher"><div data-testid="gate-content">Teacher Only</div></RoleGate>
      </MemoryRouter>
    );
    expect(container.querySelector('[data-testid="gate-content"]')).toBeInTheDocument();
  });

  it('does not render children when role does not match', async () => {
    const { useAuth } = await import('../hooks/useAuth');
    vi.mocked(useAuth).mockReturnValue({ user: { id: 1, name: 'S', role: 'student', token: 't' } as never, token: 't', role: 'student', loading: false, isAuthenticated: true, login: vi.fn(), signup: vi.fn(), logout: vi.fn(), refreshMe: vi.fn() });

    const { container } = render(
      <MemoryRouter>
        <RoleGate role="teacher"><div data-testid="gate-content">Teacher Only</div></RoleGate>
      </MemoryRouter>
    );
    expect(container.querySelector('[data-testid="gate-content"]')).not.toBeInTheDocument();
  });

  it('redirects to / when role does not match', async () => {
    const { useAuth } = await import('../hooks/useAuth');
    vi.mocked(useAuth).mockReturnValue({ user: { id: 1, name: 'S', role: 'student', token: 't' } as never, token: 't', role: 'student', loading: false, isAuthenticated: true, login: vi.fn(), signup: vi.fn(), logout: vi.fn(), refreshMe: vi.fn() });

    render(
      <MemoryRouter initialEntries={['/teacher']}>
        <RoleGate role="teacher"><div>Teacher Only</div></RoleGate>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.queryByText('Teacher Only')).not.toBeInTheDocument();
    });
  });
});

describe('logout clears token', () => {
  it('removes token from localStorage on logout', async () => {
    localStorage.setItem('student_os_token', 'tok');

    await authApi.logout();
    expect(localStorage.getItem('student_os_token')).toBeNull();
  });
});
