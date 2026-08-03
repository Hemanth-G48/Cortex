import type { PersonalRecord } from '../../services/api';

interface Props {
  records: PersonalRecord[];
}

/** Sidebar PR-Tracker widget (Phase 67): current/target bench + OHP progress. */
export const FhPRTracker = ({ records }: Props) => {
  if (records.length === 0) {
    return (
      <div className="fh-card" id="pr">
        <div className="fh-card-title">PR-Tracker</div>
        <div className="fh-empty" style={{ padding: '0.75rem' }}>
          <span className="fh-empty-icon" aria-hidden="true">🏆</span>
          <span>No personal records yet.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="fh-card" id="pr">
      <div className="fh-card-title">PR-Tracker</div>
      <div className="fh-pr-list">
        {records.map((r) => (
          <div key={r.id} className="fh-pr-row">
            <div className="fh-pr-head">
              <span className="fh-pr-name">{r.exercise_name}</span>
              <span className="fh-pr-val">
                {r.current_weight}/{r.target_weight} {r.unit}
              </span>
            </div>
            <div className="fh-pr-bar" role="progressbar" aria-label={`${r.exercise_name} progress`} aria-valuenow={r.percent ?? 0} aria-valuemin={0} aria-valuemax={100}>
              <div className="fh-pr-fill" style={{ width: `${r.percent ?? 0}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
