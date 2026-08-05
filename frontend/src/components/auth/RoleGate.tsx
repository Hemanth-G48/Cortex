import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';

interface RoleGateProps {
  role: 'teacher' | 'student' | 'admin';
  children: React.ReactNode;
}

export const RoleGate = ({ role, children }: RoleGateProps) => {
  const { user, role: userRole, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  // `admin` is the user's `is_admin` flag (SyllabusAI G1), not a role value.
  const allowed = role === 'admin' ? (user?.is_admin ?? false) : userRole === role;

  useEffect(() => {
    if (!loading && isAuthenticated && !allowed) {
      navigate('/');
    }
  }, [loading, isAuthenticated, allowed, navigate]);

  if (loading) return <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>Loading…</div>;
  if (!isAuthenticated || !allowed) return null;
  return <>{children}</>;
};