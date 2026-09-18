import { useEffect, useMemo, useState } from 'react';
import { endpoints } from '../../services/api';
import type { Goal, KbMastery, LifeArea } from '../../services/api';

interface LifeAreasGoalsProps {
  areas: LifeArea[];
  goals: Goal[];
  onAchieve: (goal: Goal) => void;
}

const RING_SIZE = 44;
const RING_STROKE = 6;
const RADIUS = (RING_SIZE - RING_STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function ProgressRing({ value, achieved }: { value: number; achieved: boolean }) {
  const offset = CIRCUMFERENCE * (1 - Math.min(100, Math.max(0, value)) / 100);
  return (
    <svg width={RING_SIZE} height={RING_SIZE} className="g-ring" viewBox={`0 0 ${RING_SIZE} ${RING_SIZE}`}>
      <circle cx={RING_SIZE / 2} cy={RING_SIZE / 2} r={RADIUS} className="ring-bg" />
      <circle
        cx={RING_SIZE / 2} cy={RING_SIZE / 2} r={RADIUS}
        className="ring-fg"
        strokeDasharray={CIRCUMFERENCE}
        strokeDashoffset={offset}
      />
      <text
        x="50%" y="50%" dy="0.3em" textAnchor="middle"
        style={{ fontSize: 10, fontWeight: 700, fill: 'var(--text-primary)' }}
      >
        {Math.round(value)}{achieved ? '✓' : '%'}
      </text>
    </svg>
  );
}

/**
 * Vault mastery sparkline (defect #40): plots the subject's real daily mastery
 * score from its LearningEvent practice logs. Renders nothing until the trend
 * has at least two points, so the card layout is unchanged for new subjects.
 */
function MasterySparkline({ mastery }: { mastery: KbMastery }) {
  const points = mastery.trend.slice(-20);
  if (points.length < 2) return null;
  const w = 120;
  const h = 22;
  const scores = points.map((p) => p.score_pct);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const span = max - min || 1;
  const polyline = points
    .map((p, i) => `${(i / (points.length - 1)) * w},${h - ((p.score_pct - min) / span) * h}`)
    .join(' ');
  return (
    <div style={{ marginTop: 4 }}>
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-label="vault mastery trend">
        <polyline points={polyline} fill="none" stroke="var(--accent)" strokeWidth={1.5} />
      </svg>
      <div className="g-sub">vault mastery {Math.round(mastery.score_pct)}%</div>
    </div>
  );
}

/** 4-column goals grid with Areas / Quarterly tabs + circular progress + mark achieved. */
export const LifeAreasGoals = ({ areas, goals, onAchieve }: LifeAreasGoalsProps) => {
  const [tab, setTab] = useState<'areas' | 'quarterly'>('quarterly');
  // Defect #40: vault mastery per linked subject, keyed by curriculum subject id.
  const [masteryBySubject, setMasteryBySubject] = useState<Record<number, KbMastery>>({});

  const subjectIds = useMemo(
    () => [...new Set(goals.map((g) => g.subject_id).filter((id): id is number => typeof id === 'number'))],
    [goals],
  );

  useEffect(() => {
    if (subjectIds.length === 0) return;
    let stale = false;
    Promise.all(
      subjectIds.map((id) =>
        endpoints.kb
          .mastery({ subject: id })
          .then((m) => [id, m] as const)
          .catch(() => null),
      ),
    ).then((rows) => {
      if (stale) return;
      const next: Record<number, KbMastery> = {};
      for (const row of rows) {
        if (row) next[row[0]] = row[1];
      }
      setMasteryBySubject(next);
    });
    return () => {
      stale = true;
    };
  }, [subjectIds]);

  return (
    <div>
      <div className="lp-section-title">Life Areas & Goals</div>
      <div className="lp-tabs" role="tablist" aria-label="Life areas and goals">
        <button
          type="button" role="tab" aria-selected={tab === 'areas'}
          className={`lp-tab${tab === 'areas' ? ' active' : ''}`}
          onClick={() => setTab('areas')}
        >
          Areas
        </button>
        <button
          type="button" role="tab" aria-selected={tab === 'quarterly'}
          className={`lp-tab${tab === 'quarterly' ? ' active' : ''}`}
          onClick={() => setTab('quarterly')}
        >
          Quarterly
        </button>
      </div>

      {tab === 'areas' && (
        <div className="lp-goal-grid">
          {areas.map((a) => (
            <div key={a.id} className="lp-goal-card">
              <div className="g-ring-wrap">
                <ProgressRing value={a.progress_percent} achieved={false} />
                <div>
                  <div className="g-title">{a.name}</div>
                  <div className="g-sub">{a.goal ?? a.description ?? 'Life area'}</div>
                </div>
              </div>
            </div>
          ))}
          {areas.length === 0 && <div className="reminders-empty">No life areas yet</div>}
        </div>
      )}

      {tab === 'quarterly' && (
        <div className="lp-goal-grid">
          {goals.map((g) => (
            <div key={g.id} className={`lp-goal-card${g.is_completed ? ' achieved' : ''}`}>
              <div className="g-ring-wrap">
                <ProgressRing value={g.is_completed ? 100 : g.progress_percentage} achieved={g.is_completed} />
                <div>
                  <div className="g-title">{g.title}</div>
                  <div className="g-sub">
                    {g.quarter} {g.year} · {g.is_completed ? 'Completed' : `${Math.round(g.progress_percentage)}%`}
                  </div>
                  {g.subject_id != null && masteryBySubject[g.subject_id] && (
                    <MasterySparkline mastery={masteryBySubject[g.subject_id]} />
                  )}
                </div>
              </div>
              <button
                type="button"
                className={`btn btn-ghost btn-sm btn-achieve${g.is_completed ? ' achieved' : ''}`}
                onClick={() => onAchieve(g)}
              >
                {g.is_completed ? '✓ Achieved' : 'Mark as achieved'}
              </button>
            </div>
          ))}
          {goals.length === 0 && <div className="reminders-empty">No goals yet</div>}
        </div>
      )}
    </div>
  );
};
