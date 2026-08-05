import { useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import type { User } from '../../services/api';
import { NotificationsBell } from '../NotificationsBell';

export const Header = ({ title }: { title: string }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    endpoints.login().then((r) => setUser(r.user)).catch(() => {});
  }, []);

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
