import type { PersonalRecord } from '../../services/api';
import type { VaultNote } from '../../hooks/useFitnessHubData';

interface Props {
  records: PersonalRecord[];
  /** Vault notes mentioning PRs/lifts (defect #86). */
  vaultNotes?: VaultNote[];
}

/**
 * Extraction for PR auto-suggestions: pull a weight + optional reps out of a
 * note snippet, e.g. "bench 82.5 kg x 5" → { weight: 82.5, unit: 'kg', reps: 5 }.
 */
const PR_PATTERN = /(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)\b(?:\s*(?:x|×|\*)\s*(\d+))?/i;

export interface PrSuggestion {
  document_id: number;
  title: string;
  snippet: string;
  weight: number;
  unit: string;
  reps: number | null;
}

const extractPrSuggestion = (note: VaultNote): PrSuggestion | null => {
  const text = `${note.title} ${note.snippet}`;
  const m = PR_PATTERN.exec(text);
  if (!m) return null;
  return {
    document_id: note.document_id,
    title: note.title,
    snippet: note.snippet,
    weight: Number(m[1]),
    unit: m[2].toLowerCase(),
    reps: m[3] ? Number(m[3]) : null,
  };
};

/** Sidebar PR-Tracker widget (Phase 67): current/target bench + OHP progress. */
export const FhPRTracker = ({ records, vaultNotes = [] }: Props) => {
  // Defect #86: cross-check the vault for PR mentions we don't have on file yet.
  const knownWeights = new Set(records.map((r) => r.current_weight));
  const suggestions = vaultNotes
    .map(extractPrSuggestion)
    .filter((s): s is PrSuggestion => s !== null)
    .filter((s) => !knownWeights.has(s.weight))
    .slice(0, 3);
  if (records.length === 0 && suggestions.length === 0) {
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
        {suggestions.length > 0 && (
          <div className="fh-pr-row" style={{ fontSize: '0.7rem', color: 'var(--fh-text-muted, #999)' }}>
            <div className="fh-pr-head">
              <span className="fh-pr-name" title={suggestions[0].snippet}>
                📚 Suggested: {suggestions[0].weight} {suggestions[0].unit}
                {suggestions[0].reps ? ` × ${suggestions[0].reps}` : ''}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
