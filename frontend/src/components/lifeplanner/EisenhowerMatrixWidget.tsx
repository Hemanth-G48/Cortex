import type { EisenhowerMatrix, EisenhowerTask } from '../../services/api';

interface EisenhowerMatrixWidgetProps {
  matrix: EisenhowerMatrix;
  onComplete: (task: EisenhowerTask) => void;
}

const QUADRANTS: {
  key: keyof EisenhowerMatrix;
  title: string;
  action: string;
  actionClass: string;
  klass: string;
}[] = [
  { key: 'urgent_important', title: 'Urgent & Important', action: 'Do first', actionClass: 'do-first', klass: 'q-urgent-important' },
  { key: 'important_not_urgent', title: 'Important, Not Urgent', action: 'Schedule', actionClass: 'schedule', klass: 'q-important' },
  { key: 'urgent_not_important', title: 'Urgent, Not Important', action: 'Delegate', actionClass: 'delegate', klass: 'q-neutral' },
  { key: 'not_important', title: 'Not Important, Not Urgent', action: 'Delete / Postpone', actionClass: 'delete', klass: 'q-neutral' },
];

/** Bottom-row 2×2 Eisenhower matrix with tinted borders and mark-as-done. */
export const EisenhowerMatrixWidget = ({ matrix, onComplete }: EisenhowerMatrixWidgetProps) => (
  <div>
    <div className="lp-section-title">Eisenhower Matrix</div>
    <div className="eisenhower-matrix">
      {QUADRANTS.map((q) => (
        <div key={q.key} className={`eq-quadrant ${q.klass}`}>
          <div className="eq-header">
            <span className="eq-title">{q.title}</span>
            <span className={`eq-action ${q.actionClass}`}>{q.action}</span>
          </div>
          {matrix[q.key].length === 0 && <div className="eq-empty">Nothing here — great job!</div>}
          {matrix[q.key].map((t) => (
            <div key={t.id} className="eq-task">
              <span title={t.subject_tag ?? undefined}>▸</span>
              <span style={{ flex: 1 }}>{t.title}</span>
              <button type="button" className="eq-done" onClick={() => onComplete(t)} aria-label={`Mark done: ${t.title}`}>
                ✓ Done
              </button>
            </div>
          ))}
        </div>
      ))}
    </div>
  </div>
);
