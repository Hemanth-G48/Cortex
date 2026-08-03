import { Link } from 'react-router-dom';
import type { PriorityWindow as PriorityWindowData } from '../../services/api';

interface Props {
  priority: PriorityWindowData | null;
}

const FOLDERS: { key: keyof PriorityWindowData; label: string }[] = [
  { key: 'High', label: 'High' },
  { key: 'Medium', label: 'Medium' },
  { key: 'Low', label: 'Low' },
];

/**
 * Priority-Window: High / Medium / Low "folder" cards, each item showing its
 * estimated duration and linking to the task or quest detail route.
 */
export const PriorityWindow = ({ priority }: Props) => {
  return (
    <div className="qc-card">
      <div className="qc-card-title">Priority Window</div>
      <div className="qc-priority-grid">
        {FOLDERS.map(({ key, label }) => {
          const items = priority?.[key] ?? [];
          return (
            <div key={key} className="qc-priority-card">
              <div className={`qc-priority-header ${key.toLowerCase()}`}>
                <span>{label}</span>
                <span className="qc-priority-count">{items.length}</span>
              </div>
              <div className="qc-priority-list">
                {items.length === 0 && (
                  <div className="qc-empty-note">Nothing {key.toLowerCase()}.</div>
                )}
                {items.map((it) => (
                  <div key={`${it.kind}-${it.id}`} className="qc-priority-item">
                    <Link
                      to={it.kind === 'quest' ? `/quests` : `/tasks`}
                      title={it.title}
                    >
                      {it.title}
                    </Link>
                    <span className="qc-kind-chip">{it.kind}</span>
                    {it.time_estimate != null && (
                      <span className="qc-priority-meta">~{it.time_estimate}m</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
