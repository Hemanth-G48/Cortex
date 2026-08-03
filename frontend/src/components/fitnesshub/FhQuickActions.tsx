import { useNavigate } from 'react-router-dom';

export type FhQuickActionKind =
  | 'exercise'
  | 'expense'
  | 'muscle-group'
  | 'habit'
  | 'weight-goal';

interface Props {
  onCreate: (kind: FhQuickActionKind) => void;
}

type Action =
  | { label: string; icon: string; kind: FhQuickActionKind }
  | { label: string; icon: string; route: string };

const ACTIONS: Action[] = [
  { label: 'Add Exercise', icon: '🏋️', kind: 'exercise' },
  { label: 'Add Expense', icon: '💸', kind: 'expense' },
  { label: 'Muscle Group', icon: '💪', kind: 'muscle-group' },
  { label: 'New Habit', icon: '🌱', kind: 'habit' },
  { label: 'Habit Grid Design', icon: '▦', route: '/grid-design' },
  { label: 'Weight Goal', icon: '⚖️', kind: 'weight-goal' },
  { label: 'Membership', icon: '🏟️', route: '/fitness-hub' },
];

/** Sidebar Quick-Action widget (Phase 64): 7 spec links with + icons. */
export const FhQuickActions = ({ onCreate }: Props) => {
  const navigate = useNavigate();

  return (
    <div className="fh-card">
      <div className="fh-card-title">Quick-Action</div>
      <div className="fh-qa-grid">
        {ACTIONS.map((a) => (
          <button
            key={a.label}
            type="button"
            className="fh-qa-btn"
            onClick={() => ('route' in a ? navigate(a.route) : onCreate(a.kind))}
            aria-label={a.label}
          >
            <span className="fh-qa-icon" aria-hidden="true">+</span>
            <span className="fh-qa-label">{a.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
