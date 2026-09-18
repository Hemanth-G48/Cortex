import type { DietPlan } from '../../services/api';
import type { VaultNote } from '../../hooks/useFitnessHubData';

interface Props {
  plans: DietPlan[];
  /** Vault notes about diet/nutrition (defect #85). */
  vaultNotes?: VaultNote[];
}

/** Sidebar Diet-Plan widget (Phase 69): phases with active highlight + pulse. */
export const FhDietPlan = ({ plans, vaultNotes = [] }: Props) => {
  if (plans.length === 0) {
    return (
      <div className="fh-card">
        <div className="fh-card-title">Diet-Plan</div>
        <div className="fh-empty" style={{ padding: '0.75rem' }}>
          <span className="fh-empty-icon" aria-hidden="true">🍽️</span>
          <span>No diet plans yet.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="fh-card">
      <div className="fh-card-title">Diet-Plan</div>
      <div className="fh-diet-list">
        {plans.map((p) => (
          <div key={p.id} className={`fh-diet-item${p.is_active ? ' active' : ''}`}>
            <span>{p.title}</span>
            <span className="fh-diet-dot" aria-label={p.is_active ? 'Active plan' : undefined} />
          </div>
        ))}
        {vaultNotes.length > 0 && (
          <div className="fh-diet-item" style={{ fontSize: '0.7rem', color: 'var(--fh-text-muted, #999)' }}>
            <span title={vaultNotes[0].snippet}>📚 {vaultNotes[0].title}</span>
          </div>
        )}
      </div>
    </div>
  );
};
