import { NotificationsBell } from '../NotificationsBell';
import { useAuth } from '../../hooks/useAuth';

export const Header = ({ title }: { title: string }) => {
  // Use the authenticated user (AuthContext) rather than the legacy
  // no-body ``/auth/login`` (first-user) call — the latter would silently
  // overwrite the stored token with the first user's on every page load,
  // breaking multi-user sessions.
  const { user } = useAuth();

  return (
    <header className="header">
      <h1>{title}</h1>
      <NotificationsBell />
      {user && (
        <div className="user-badge">
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{user.name}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Lv.{user.current_level} · {user.total_xp} XP
            </div>
          </div>
          <div>
            <div className="xp-bar">
              <div className="xp-fill" style={{ width: `${(user.total_xp % 1000) / 10}%` }} />
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
