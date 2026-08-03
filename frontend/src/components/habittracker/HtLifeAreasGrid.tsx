import type { HabitTrackerLifeArea } from '../../services/api';

interface Props {
  areas: HabitTrackerLifeArea[];
}

const AREA_ICONS: Record<string, string> = {
  Health: '💚',
  Fitness: '🏋️',
  'Self Development': '📚',
  'Self Improvement': '📚',
  Work: '💼',
  Academics: '🎓',
  Social: '🫂',
};

/** Row-1 life-area cards (Phase 65-67): 3D thumb, "All Time XP" + status badge. */
export const HtLifeAreasGrid = ({ areas }: Props) => {
  if (areas.length === 0) {
    return (
      <div className="ht-card">
        <div className="ht-card-title">Life Areas</div>
        <div className="ht-cal-empty">No life areas yet.</div>
      </div>
    );
  }

  return (
    <div className="ht-card">
      <div className="ht-card-title">Life Areas</div>
      <div className="ht-life-grid">
        {areas.map((a) => (
          <div key={a.id} className="ht-life-area-card">
            <div className="ht-la-backdrop" aria-hidden="true" />
            <div className="ht-la-content">
              <span className="ht-la-icon" aria-hidden="true">{AREA_ICONS[a.name] ?? '🎯'}</span>
              <span className="ht-la-name">{a.name}</span>
              <span className="ht-la-xp">All Time XP: {a.total_xp_earned}</span>
              <span className="ht-la-status-badge">{a.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
