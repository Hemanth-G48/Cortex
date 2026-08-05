import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { authApi, type AuthUser, type UserRole } from '../services/api';

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  role: UserRole | null;
  loading: boolean;
}

interface AuthCtx {
  user: AuthUser | null;
  token: string | null;
  role: UserRole | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (d: { identifier?: string; password?: string }) => Promise<{ user: AuthUser; token: string }>;
  signup: (d: { name: string; username?: string; email?: string; password: string; role: UserRole; teacher_secret?: string }) => Promise<{ user: AuthUser; token: string }>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  token: null,
  role: null,
  loading: true,
  isAuthenticated: false,
  login: async () => ({ user: null as never, token: '' }),
  signup: async () => ({ user: null as never, token: '' }),
  logout: async () => {},
  refreshMe: async () => {},
});

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<AuthState>({ user: null, token: null, role: null, loading: true });

  const refreshMe = async () => {
    try {
      const r = await authApi.me();
      setState({ user: r.user, token: r.user.token, role: r.user.role, loading: false });
    } catch {
      setState({ user: null, token: null, role: null, loading: false });
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('student_os_token');
    if (token) {
      refreshMe().catch(() => setState({ user: null, token: null, role: null, loading: false }));
    } else {
      setState({ user: null, token: null, role: null, loading: false });
    }
  }, []);

  const login = async (d: { identifier?: string; password?: string }) => {
    const r = await authApi.login(d);
    setState({ user: r.user, token: r.token, role: r.user.role, loading: false });
    return r;
  };

  const signup = async (d: { name: string; username?: string; email?: string; password: string; role: UserRole; teacher_secret?: string }) => {
    const r = await authApi.signup(d);
    setState({ user: r.user, token: r.token, role: r.user.role, loading: false });
    return r;
  };

  const logout = async () => {
    try { await authApi.logout(); } catch { /* ignore */ }
    setState({ user: null, token: null, role: null, loading: false });
  };

  return (
    <AuthContext.Provider value={{ user: state.user, token: state.token, role: state.role, loading: state.loading, isAuthenticated: !!state.user, login, signup, logout, refreshMe }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
export default AuthContext;