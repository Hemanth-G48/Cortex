import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { authApi, type UserRole } from '../services/api';

export const Login = () => {
  const navigate = useNavigate();
  const { login: authLogin } = useAuth();
  const [role, setRole] = useState<UserRole>('student');
  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [teacherSecret, setTeacherSecret] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'signup' | 'login'>('signup');

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await authApi.signup({ name, username: username || undefined, email: email || undefined, password, role, teacher_secret: role === 'teacher' ? teacherSecret : undefined });
      navigate('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login' && identifier) {
        await authLogin({ identifier, password });
      } else {
        await authLogin({});
      }
      navigate('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="card" style={{ maxWidth: '420px', margin: '2rem auto', padding: '2rem' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>🎓 Student Life OS</h2>

        <div className="field-row" style={{ justifyContent: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <button className={`btn ${mode === 'signup' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => { setMode('signup'); setError(''); }}>Sign Up</button>
          <button className={`btn ${mode === 'login' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => { setMode('login'); setError(''); }}>Log In</button>
        </div>

        {error && <div className="toast toast-error" style={{ marginBottom: '1rem' }}>{error}</div>}

        {mode === 'signup' ? (
          <form onSubmit={handleSignup}>
            <div className="field-row">
              <label htmlFor="signup-name">Name</label>
              <input id="signup-name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field-row">
              <label htmlFor="signup-username">Username</label>
              <input id="signup-username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div className="field-row">
              <label htmlFor="signup-email">Email</label>
              <input id="signup-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="field-row">
              <label htmlFor="signup-password">Password</label>
              <input id="signup-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <div className="field-row">
              <label htmlFor="signup-role">Role</label>
              <select id="signup-role" value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
                <option value="student">Student</option>
                <option value="teacher">Teacher</option>
              </select>
            </div>
            {role === 'teacher' && (
              <div className="field-row">
                <label htmlFor="signup-secret">Teacher Secret</label>
                <input id="signup-secret" type="password" value={teacherSecret} onChange={(e) => setTeacherSecret(e.target.value)} required />
              </div>
            )}
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }} disabled={loading}>
              {loading ? 'Signing up…' : 'Sign Up'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin}>
            <div className="field-row">
              <label htmlFor="login-identifier">Identifier (email or username)</label>
              <input id="login-identifier" type="text" value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
            </div>
            <div className="field-row">
              <label htmlFor="login-password">Password</label>
              <input id="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }} disabled={loading}>
              {loading ? 'Logging in…' : 'Log In'}
            </button>
            <p style={{ textAlign: 'center', marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Leave identifier empty for legacy login (first user)
            </p>
          </form>
        )}
      </div>
    </div>
  );
};