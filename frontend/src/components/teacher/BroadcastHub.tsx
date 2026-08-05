import { useState } from 'react';
import { BroadcastModal } from './BroadcastModal';

interface BroadcastHubProps {
  selected: number[];
  onDone: () => void;
}

export type BroadcastKind = 'course' | 'assignment' | 'todo' | 'book' | 'schedule';

const KIND_LABELS: Record<BroadcastKind, string> = {
  course: '📚 Course',
  assignment: '📝 Assignment',
  todo: '✅ Todo',
  book: '📖 Book',
  schedule: '📅 Schedule',
};

export const BroadcastHub = ({ selected, onDone }: BroadcastHubProps) => {
  const [openKind, setOpenKind] = useState<BroadcastKind | null>(null);

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div className="card-header">
        <h2 className="widget-title">Broadcast</h2>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {(Object.keys(KIND_LABELS) as BroadcastKind[]).map((kind) => (
          <button
            key={kind}
            type="button"
            className="btn btn-primary"
            onClick={() => setOpenKind(kind)}
          >
            {KIND_LABELS[kind]}
          </button>
        ))}
      </div>

      {openKind && (
        <BroadcastModal
          kind={openKind}
          selected={selected}
          onClose={() => setOpenKind(null)}
          onDone={onDone}
        />
      )}
    </div>
  );
};
