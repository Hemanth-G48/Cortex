import { NavLink } from 'react-router-dom';
import { useProfile } from '../../hooks/useProfile';

interface NavGroup {
  label: string;
  links: { to: string; label: string; icon: string }[];
}

const studentGroups: NavGroup[] = [
  {
    label: 'Workflows',
    links: [
      { to: '/today', label: 'Today', icon: '📅' },
      { to: '/weekly-review', label: 'Weekly Review', icon: '🗓️' },
      { to: '/learning-planner', label: 'Learning Path Planner', icon: '🗺️' },
      { to: '/workflows', label: 'Workflows', icon: '⚙️' },
    ],
  },
  {
    label: 'Academics',
    links: [
      { to: '/courses', label: 'Courses', icon: '📚' },
      { to: '/assignments', label: 'Assignments', icon: '📝' },
      { to: '/exams', label: 'Exams', icon: '📋' },
      { to: '/grades', label: 'Grades', icon: '📊' },
      { to: '/flashcards', label: 'Flashcards', icon: '🃏' },
      { to: '/study-plans', label: 'Study Plans', icon: '🗓️' },
      { to: '/quiz', label: 'Quiz', icon: '🧠' },
      { to: '/import', label: 'Import Syllabus', icon: '📥' },
      { to: '/subjects', label: 'Subjects', icon: '📘' },
      { to: '/analytics', label: 'Analytics', icon: '📈' },
      { to: '/reading', label: 'Reading', icon: '📖' },
      { to: '/book-gaps', label: 'Book Gaps', icon: '🔍' },
      { to: '/knowledge-base', label: 'Second Brain', icon: '🧠' },
      { to: '/knowledge-graph', label: 'Graph', icon: '🕸️' },
      { to: '/vault-search', label: 'Search', icon: '🔎' },
      { to: '/kb-insights', label: 'Insights', icon: '🩺' },
      { to: '/gap-analysis', label: 'Gap Analysis', icon: '🕳️' },
      { to: '/tutor', label: 'AI Tutor', icon: '🧑‍🏫' },
      { to: '/practice', label: 'Practice', icon: '🎯' },
      { to: '/mocks', label: 'Mock Exams', icon: '📝' },
      { to: '/interview', label: 'Interview Prep', icon: '🎤' },
      { to: '/skills', label: 'Skills', icon: '🛠️' },
      { to: '/quality', label: 'Note Quality', icon: '🏆' },
      { to: '/flashcard-review', label: 'Review Queue', icon: '📥' },
      { to: '/browse', label: 'Browse Curriculum', icon: '🗂️' },
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
      { to: '/leaderboard', label: 'Leaderboard', icon: '🏆' },
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
  {
    label: 'System',
    links: [
      { to: '/settings', label: 'Settings', icon: '⚙️' },
    ],
  },
];

const adminGroups: NavGroup[] = [
  {
    label: 'Admin',
    links: [
      { to: '/admin', label: 'Curriculum Admin', icon: '🛠️' },
    ],
  },
];

/** Categorised navigation links replacing the flat sidebar nav */
export const NavLinks = () => {
  // Single-owner app: no teacher role; admin is the owner's `is_admin` flag.
  const { profile: user } = useProfile();
  const base = studentGroups;
  const groups = user?.is_admin ? [...base, ...adminGroups] : base;

  return (
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
};
