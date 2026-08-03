import { useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import type { Goal } from '../../services/api';

/** Quarterly goal tracker for the sidebar */
export const GoalTracker = () => {
  const [goals, setGoals] = useState<Goal[]>([]);

  useEffect(() => {
    endpoints.goals.list().then(setGoals).catch(() => {});
  }, []);

  const now = new Date();
  const q = Math.floor(now.getMonth() / 3) + 1;
  const quarterGoals = goals.filter((g) => g.quarter === `Q${q}`);

  if (!quarterGoals.length) return null;

  return (
    <div className="sidebar-widget goal-tracker">
      <div className="widget-title">Q{q} Goals</div>
      {quarterGoals.slice(0, 4).map((g) => (
        <div key={g.id} className="gt-row">
          <span className="gt-label">{g.title}</span>
          <div className="xp-bar"><div className="xp-fill" style={{ width: `${g.progress_percentage}%` }} /></div>
          <span className="gt-value">{g.progress_percentage}%</span>
        </div>
      ))}
    </div>
  );
};
