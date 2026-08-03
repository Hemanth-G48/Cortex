import type { ProgressReport } from '../../services/api';

interface Props {
  progress: ProgressReport | null;
}

const BARS: { key: keyof ProgressReport; label: string }[] = [
  { key: 'year', label: 'Year' },
  { key: 'month', label: 'Month' },
  { key: 'week', label: 'Week' },
  { key: 'day', label: 'Day' },
];

/**
 * Macroscopic progress bars (Year / Month / Week / Day) fed by the
 * /quest-centre/progress endpoint.
 */
export const ProgressBarsQC = ({ progress }: Props) => {
  return (
    <div className="qc-card qc-progress-bars">
      <div className="qc-card-title">Progress</div>
      {BARS.map(({ key, label }) => {
        const value = progress ? progress[key] : 0;
        return (
          <div key={key} className="qc-pb-row">
            <span className="qc-pb-label">{label}</span>
            <div className="qc-xp-bar" role="progressbar" aria-label={`${label} progress`} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
              <div className="qc-xp-fill" style={{ width: `${value}%` }} />
            </div>
            <span className="qc-pb-value">{value}%</span>
          </div>
        );
      })}
    </div>
  );
};
