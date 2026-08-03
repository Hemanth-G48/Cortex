import { NavLink } from 'react-router-dom';

interface NavGroup {
  label: string;
  links: { to: string; label: string; icon: string }[];
}

const groups: NavGroup[] = [
  {
    label: 'Academics',
    links: [
      { to: '/courses', label: 'Courses', icon: '📚' },
      { to: '/assignments', label: 'Assignments', icon: '📝' },
      { to: '/exams', label: 'Exams', icon: '📋' },
    ],
  },
  {
    label: 'Productivity',
    links: [
      { to: '/tasks', label: 'Tasks', icon: '✅' },
      { to: '/schedule', label: 'Schedule', icon: '📅' },
      { to: '/habits', label: 'Habits', icon: '🔄' },
      { to: '/pomodoro', label: 'Pomodoro', icon: '⏱️' },
      { to: '/goals', label: 'Goals', icon: '🎯' },
    ],
  },
  {
    label: 'Wellness',
    links: [
      { to: '/fitness-hub', label: 'Fitness Hub', icon: '💪' },
      { to: '/fitness', label: 'Fitness', icon: '🏋️' },
      { to: '/journal', label: 'Journal', icon: '📔' },
      { to: '/life-areas', label: 'Life Areas', icon: '🎯' },
    ],
  },
  {
    label: 'Projects',
    links: [
      { to: '/quests', label: 'Quests', icon: '⚔️' },
      { to: '/projects', label: 'Projects', icon: '📁' },
      { to: '/notes', label: 'Notes', icon: '📓' },
    ],
  },
  {
    label: 'RPG',
    links: [
      { to: '/quest-centre', label: 'Quest Centre', icon: '🏆' },
      { to: '/habit-tracker', label: 'Habit Tracker', icon: '🔥' },
      { to: '/rpg-dashboard', label: 'RPG Dashboard', icon: '📊' },
      { to: '/character', label: 'Character', icon: '👤' },
      { to: '/rewards', label: 'Rewards', icon: '🎁' },
      { to: '/missions', label: 'Missions', icon: '🎯' },
    ],
  },
  {
    label: 'Vault',
    links: [
      { to: '/vault', label: 'Vault Dashboard', icon: '🗄️' },
      { to: '/habit-report', label: 'Habit Report', icon: '📈' },
      { to: '/archive-habits', label: 'Archive Habits', icon: '🗃️' },
      { to: '/goals-setting', label: 'Goals Setting', icon: '🎯' },
      { to: '/habit-logs', label: 'Habit Logs', icon: '📜' },
      { to: '/grid-design', label: 'Grid Design', icon: '▦' },
      { to: '/vault-database', label: 'Database', icon: '🗄️' },
    ],
  },
  {
    label: 'Life Planner',
    links: [
      { to: '/life-planner', label: 'Life Planner Dashboard', icon: '🌱' },
    ],
  },
];

/** Categorised navigation links replacing the flat sidebar nav */
export const NavLinks = () => (
  <nav className="sidebar-nav">
    <NavLink to="/" end className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
      <span>📊</span> Dashboard
    </NavLink>
    {groups.map((g) => (
      <div key={g.label} className="nav-group">
        <div className="nav-group-label">{g.label}</div>
        {g.links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
          >
            <span>{l.icon}</span>
            {l.label}
          </NavLink>
        ))}
      </div>
    ))}
  </nav>
);
