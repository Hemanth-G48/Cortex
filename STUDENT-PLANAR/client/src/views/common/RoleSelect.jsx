import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function RoleSelect() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [secretKey, setSecretKey] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!name || !password) {
      setError('Username and password are required');
      return;
    }
    if (!isLogin && !fullName) {
      setError('Full Name is required for signup');
      return;
    }

    try {
      const endpoint = isLogin ? '/api/login' : '/api/signup';
      const payload = isLogin ? { name, password, role } : { name, fullName, password, role, secretKey };
      const res = await axios.post(`http://localhost:5000${endpoint}`, payload);
      
      // Save identity locally
      localStorage.setItem('user', JSON.stringify(res.data));
      
      // Navigate to correct dashboard
      if (res.data.role === 'student') navigate('/student/dashboard');
      else navigate('/teacher/dashboard');
    } catch (err) {
      console.error('Auth Failed', err);
      if (err.response && err.response.data && err.response.data.error) {
        setError(err.response.data.error);
      } else {
        setError('Could not connect to backend. Is MongoDB running natively?');
      }
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: 'var(--bg-color)', color: 'var(--text-primary)' }}>
      <div style={{ padding: '2rem 3rem', backgroundColor: 'var(--bg-color-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)', width: '100%', maxWidth: '400px', boxShadow: '0 8px 24px rgba(0,0,0,0.2)' }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--accent-green)', textAlign: 'center' }}>Student Planner</h1>
        <p style={{ marginBottom: '2rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
          {isLogin ? 'Welcome back! Log in to continue.' : 'Create a new account.'}
        </p>

        {error && <div style={{ backgroundColor: 'rgba(217, 102, 102, 0.1)', color: 'var(--accent-red)', padding: '0.75rem', borderRadius: '4px', marginBottom: '1.5rem', border: '1px solid var(--accent-red)', fontSize: '0.9rem', textAlign: 'center' }}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {!isLogin && (
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Full Name</label>
              <input 
                type="text" 
                value={fullName} 
                onChange={e => setFullName(e.target.value)}
                style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-primary)' }}
                placeholder="Enter your real full name"
              />
            </div>
          )}
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Username</label>
            <input 
              type="text" 
              value={name} 
              onChange={e => setName(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-primary)' }}
              placeholder="Enter unique username"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-primary)' }}
              placeholder="Enter password"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>I am a...</label>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="radio" name="role" value="student" checked={role === 'student'} onChange={() => setRole('student')} />
                Student
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="radio" name="role" value="teacher" checked={role === 'teacher'} onChange={() => setRole('teacher')} />
                Teacher
              </label>
            </div>
          </div>

          {!isLogin && role === 'teacher' && (
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Teacher Secret Key</label>
              <input 
                type="password" 
                value={secretKey} 
                onChange={e => setSecretKey(e.target.value)}
                style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--accent-red)', backgroundColor: 'var(--bg-color)', color: 'var(--text-primary)' }}
                placeholder="Required for Teacher accounts"
              />
            </div>
          )}

          <button 
            type="submit"
            style={{ marginTop: '1rem', padding: '1rem', fontSize: '1.1rem', backgroundColor: 'var(--accent-blue)', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '600', transition: 'opacity 0.2s' }}
            onMouseOver={e => e.currentTarget.style.opacity = '0.9'}
            onMouseOut={e => e.currentTarget.style.opacity = '1'}
          >
            {isLogin ? 'Log In' : 'Sign Up'}
          </button>
        </form>

        <p style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <span 
            onClick={() => setIsLogin(!isLogin)} 
            style={{ color: 'var(--accent-blue)', cursor: 'pointer', textDecoration: 'underline' }}
          >
            {isLogin ? 'Sign up' : 'Log in'}
          </span>
        </p>
      </div>
    </div>
  );
}
