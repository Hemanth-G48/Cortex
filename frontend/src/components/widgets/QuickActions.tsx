import { useNavigate } from 'react-router-dom';

const actions = [
  { label: 'New Task', icon: '➕', to: '/tasks' },
  { label: 'Log Habit', icon: '🔄', to: '/habits' },
  { label: 'Timer', icon: '⏱️', to: '/pomodoro' },
  { label: 'Journal', icon: '📔', to: '/journal' },
];

/** Quick‑action button grid in the sidebar */
export const QuickActions = () => {
  const navigate = useNavigate();

  return (
    <div className="sidebar-widget quick-actions">
      <div className="widget-title">Quick Actions</div>
      <div className="qa-grid">
        {actions.map((a) => (
          <button key={a.to} className="qa-btn" onClick={() => navigate(a.to)} title={a.label}>
            <span className="qa-icon">{a.icon}</span>
            <span className="qa-label">{a.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
