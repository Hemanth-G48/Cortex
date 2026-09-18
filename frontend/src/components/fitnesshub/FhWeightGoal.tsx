import type { WeightGoal } from '../../services/api';
import type { VaultNote } from '../../hooks/useFitnessHubData';

interface Props {
  weightGoal: WeightGoal | null;
  onEdit?: () => void;
  /** Vault notes about weight goals (defect #85). */
  vaultNotes?: VaultNote[];
}

/** Sidebar Weight Goal widget (Phase 66): initial → current → target + bar. */
export const FhWeightGoal = ({ weightGoal, onEdit, vaultNotes = [] }: Props) => {
  if (!weightGoal || weightGoal.current === null) {
    return (
      <div className="fh-card">
        <div className="fh-card-title">Weight Goal</div>
        <div className="fh-empty" style={{ padding: '0.75rem' }}>
          <span className="fh-empty-icon" aria-hidden="true">⚖️</span>
          <span>No weight goal set yet.</span>
          {onEdit && (
            <button type="button" className="fh-mark-btn" onClick={onEdit}>Set goal</button>
          )}
        </div>
      </div>
    );
  }

  const { initial, current, target, percent } = weightGoal;
  return (
    <div className="fh-card" id="weight">
      <div className="fh-card-title">Weight Goal</div>
      <div className="fh-weight-row">
        <span>Initial</span>
        <b>{initial} kg</b>
      </div>
      <div className="fh-weight-row">
        <span>Current</span>
        <b>{current} kg</b>
      </div>
      <div className="fh-weight-row">
        <span>Target</span>
        <b>{target} kg</b>
      </div>
      <div className="fh-weight-bar" role="progressbar" aria-label="Weight goal progress" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
        <div className="fh-weight-fill" style={{ width: `${percent}%` }} />
      </div>
      <div className="fh-percent">{percent}% to goal</div>
      {vaultNotes.length > 0 && (
        <div className="fh-weight-row" style={{ fontSize: '0.7rem', color: 'var(--fh-text-muted, #999)' }}>
          <span>📚 Vault</span>
          <b title={vaultNotes[0].snippet}>{vaultNotes[0].title}</b>
        </div>
      )}
      {onEdit && (
        <button type="button" className="fh-mark-btn" style={{ width: '100%' }} onClick={onEdit}>
          Update
        </button>
      )}
    </div>
  );
};
