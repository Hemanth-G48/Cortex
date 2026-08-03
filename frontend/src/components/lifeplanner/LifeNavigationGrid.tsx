import { Link } from 'react-router-dom';

interface NavCard {
  to: string;
  title: string;
  sub: string;
  icon: string;
}

const CARDS: NavCard[] = [
  { to: '/life-areas', title: 'Wheel of Life', sub: 'Balance your life dimensions', icon: '🎡' },
  { to: '/goals', title: 'Goal Tracker', sub: 'Quarterly goals & progress', icon: '🎯' },
  { to: '/life-planner', title: 'Eisenhower Matrix', sub: 'Prioritize urgent vs important', icon: '🗂️' },
  { to: '/habits', title: 'Habit Tracker', sub: 'Build daily routines', icon: '🔄' },
  { to: '/journal', title: 'Daily Journal', sub: 'Capture your thoughts', icon: '📔' },
  { to: '/notes', title: 'Reflection Diary', sub: 'Review and reflect', icon: '📓' },
];

/** 2×3 navigation grid of life planner sections. */
export const LifeNavigationGrid = () => (
  <div>
    <div className="lp-section-title">Life Navigation</div>
    <div className="life-nav-grid">
      {CARDS.map((c) => (
        <Link key={c.to} to={c.to} className="life-nav-card">
          <span className="lnc-icon">{c.icon}</span>
          <span className="lnc-title">{c.title}</span>
          <span className="lnc-sub">{c.sub}</span>
        </Link>
      ))}
    </div>
  </div>
);
