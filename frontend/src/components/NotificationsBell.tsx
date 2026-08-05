import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useNotifications } from '../hooks/useNotifications';

export const NotificationsBell = () => {
  const { user } = useAuth();
  const { notifications, unread, markRead, markAllRead, remove } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!user) return null;

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        className="btn btn-ghost"
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        style={{ position: 'relative' }}
      >
        🔔
        {unread > 0 && (
          <span
            style={{
              position: 'absolute',
              top: -4,
              right: -4,
              background: 'var(--danger)',
              color: '#fff',
              borderRadius: '50%',
              width: 18,
              height: 18,
              fontSize: '0.65rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              lineHeight: 1,
            }}
          >
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="card"
          style={{
            position: 'absolute',
            right: 0,
            top: '100%',
            marginTop: '0.5rem',
            width: 320,
            maxHeight: 400,
            overflowY: 'auto',
            zIndex: 100,
            padding: 0,
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '0.75rem 1rem',
              borderBottom: '1px solid var(--border)',
            }}
          >
            <strong style={{ fontSize: '0.85rem' }}>Notifications</strong>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {unread > 0 && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void markAllRead()}>
                  Mark all read
                </button>
              )}
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setOpen(false)}>✕</button>
            </div>
          </div>

          {notifications.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              No notifications
            </div>
          ) : (
            notifications
              .slice()
              .reverse()
              .map((n) => (
                <div
                  key={n.id}
                  style={{
                    padding: '0.6rem 1rem',
                    borderBottom: '1px solid var(--border)',
                    display: 'flex',
                    gap: '0.5rem',
                    alignItems: 'flex-start',
                    background: n.read ? undefined : 'var(--bg-hover)',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{n.title}</div>
                    {n.body && <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 2 }}>{n.body}</div>}
                  </div>
                  <div style={{ display: 'flex', gap: '0.25rem', flexShrink: 0 }}>
                    {!n.read && (
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void markRead(n.id)} title="Mark read">
                        ✓
                      </button>
                    )}
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => void remove(n.id)} title="Delete" style={{ color: 'var(--danger)' }}>
                      ✕
                    </button>
                  </div>
                </div>
              ))
          )}
        </div>
      )}
    </div>
  );
};
