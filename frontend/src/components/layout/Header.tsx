import { NotificationsBell } from '../NotificationsBell';
import { useProfile } from '../../hooks/useProfile';

export const Header = ({ title }: { title: string }) => {
  // Single-owner app: the owner profile (no login) drives the badge.
  const { profile: user } = useProfile();

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
