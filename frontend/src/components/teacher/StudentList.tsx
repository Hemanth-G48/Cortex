import { StudentStats } from './StudentStats';
import type { TeacherStudent } from '../../services/api';

interface StudentListProps {
  students: TeacherStudent[];
  selected: Set<number>;
  onToggle: (id: number) => void;
  onToggleAll: () => void;
  onOpenDetail: (id: number) => void;
}

export const StudentList = ({ students, selected, onToggle, onToggleAll, onOpenDetail }: StudentListProps) => {
  const allSelected = students.length > 0 && students.every((s) => selected.has(s.id));
  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', alignItems: 'center' }}>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onToggleAll}>
          {allSelected ? 'Deselect all' : 'Select all'}
        </button>
        {selected.size > 0 && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => { /* cleared via toggle-all */ }}>
            Clear ({selected.size})
          </button>
        )}
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: 'auto' }}>
          {selected.size} selected
        </span>
      </div>

      {students.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-icon">👥</div>
          <div className="empty-title">No students</div>
          <div className="empty-message">No students are enrolled yet.</div>
        </div>
      ) : (
        <div className="card-grid">
          {students.map((student) => (
            <div key={student.id} className="card" style={{ cursor: 'pointer' }}>
              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={selected.has(student.id)}
                  onChange={() => onToggle(student.id)}
                  style={{ marginTop: 3 }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{student.name}</div>
                  <StudentStats stats={student.stats} />
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    style={{ marginTop: '0.5rem' }}
                    onClick={(e) => { e.stopPropagation(); onOpenDetail(student.id); }}
                  >
                    View details →
                  </button>
                </div>
              </label>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
