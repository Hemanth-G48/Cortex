import { useNavigate } from 'react-router-dom';

const ACTIONS: { label: string; icon: string; route: string }[] = [
  { label: 'Add New Quest', icon: '⚔️', route: '/quests' },
  { label: 'Add New Mission', icon: '🎯', route: '/missions' },
  { label: 'Add New Life Area', icon: '🌱', route: '/life-areas' },
  { label: 'Add New Reward', icon: '🏆', route: '/rewards' },
];

/**
 * Quick-action grid: each button navigates to the page hosting the matching
 * create modal (the create forms live there already).
 */
export const QuickActionsQC = () => {
  const navigate = useNavigate();

  return (
    <div className="qc-card">
      <div className="qc-card-title">Quick Actions</div>
      <div className="qc-qa-grid">
        {ACTIONS.map((a) => (
          <button
            key={a.route}
            type="button"
            className="qc-qa-btn"
            onClick={() => navigate(a.route)}
            aria-label={a.label}
          >
            <span className="qc-qa-icon" aria-hidden="true">{a.icon}</span>
            <span className="qc-qa-label">{a.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
