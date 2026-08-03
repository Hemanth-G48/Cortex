import { useNavigate } from 'react-router-dom';

interface Props {
  onCreate: (kind: 'good' | 'bad') => void;
}

type Action =
  | { label: string; icon: string; kind: 'good' }
  | { label: string; icon: string; kind: 'bad' }
  | { label: string; icon: string; route: string };

const ACTIONS: Action[] = [
  { label: 'New Good Habit', icon: '🌱', kind: 'good' },
  { label: 'New Bad Habit', icon: '⚠️', kind: 'bad' },
  { label: 'Database', icon: '🗄️', route: '/vault-database' },
];

/** Row-1 quick actions (Phase 62): create good/bad habits or open the database. */
export const HtQuickActions = ({ onCreate }: Props) => {
  const navigate = useNavigate();

  return (
    <div className="ht-card">
      <div className="ht-card-title">Quick Actions</div>
      <div className="ht-qa-grid">
        {ACTIONS.map((a) => (
          <button
            key={a.label}
            type="button"
            className="ht-qa-btn"
            onClick={() => ('route' in a ? navigate(a.route) : onCreate(a.kind))}
            aria-label={a.label}
          >
            <span className="ht-qa-icon" aria-hidden="true">{a.icon}</span>
            <span className="ht-qa-label">{a.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
