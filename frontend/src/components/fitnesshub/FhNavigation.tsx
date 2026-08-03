import { NavLink } from 'react-router-dom';

const LINKS: { to: string; label: string; icon: string }[] = [
  { to: '/fitness-hub', label: 'Membership', icon: '🏟️' },
  { to: '/fitness-hub#muscles', label: 'Muscle Groups', icon: '💪' },
  { to: '/fitness-hub#exercises', label: 'Exercises', icon: '🏋️' },
  { to: '/fitness-hub#split', label: 'Workout Plan', icon: '📅' },
  { to: '/grid-design', label: 'Habit Grid Design', icon: '▦' },
  { to: '/fitness-hub#weight', label: 'Weight Goals', icon: '⚖️' },
  { to: '/fitness-hub#pr', label: 'PR Tracker', icon: '🏆' },
  { to: '/fitness-hub#expenses', label: 'Resources', icon: '📚' },
  { to: '/archive-habits', label: 'Archive', icon: '🗃️' },
  { to: '/fitness-hub#weight', label: 'Physique Check In', icon: '📸' },
  { to: '/vault-database', label: 'Backend', icon: '⚙️' },
];

/** Sidebar Navigation widget (Phase 65): 11 spec links with active states. */
export const FhNavigation = () => (
  <div className="fh-card">
    <div className="fh-card-title">Navigation</div>
    <nav className="fh-nav-list" aria-label="Fitness Hub navigation">
      {LINKS.map((l) => (
        <NavLink
          key={l.label}
          to={l.to}
          className={({ isActive }) => `fh-nav-link${isActive ? ' active' : ''}`}
        >
          <span className="fh-nav-icon" aria-hidden="true">{l.icon}</span>
          {l.label}
        </NavLink>
      ))}
    </nav>
  </div>
);
