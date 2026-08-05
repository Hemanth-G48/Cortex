import type { Subject } from '../../services/api';

interface SubjectCardProps {
  subject: Subject;
  onClick?: () => void;
  footer?: React.ReactNode;
}

/** Catalog card for a subject, clickable into the subject detail page. */
export const SubjectCard = ({ subject, onClick, footer }: SubjectCardProps) => (
  <button
    type="button"
    className="card curriculum-card"
    onClick={onClick}
    style={{ textAlign: 'left', cursor: onClick ? 'pointer' : 'default' }}
  >
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
      <div style={{ fontSize: '1.5rem', lineHeight: 1 }}>📘</div>
      <span className="badge" style={{ color: 'var(--info)' }}>{subject.code}</span>
    </div>
    <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{subject.name}</div>
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
      {subject.semester != null && <span>Semester {subject.semester}</span>}
      <span>{subject.credits} credits</span>
      <span>{subject.unit_count} units</span>
    </div>
    {subject.description && (
      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{subject.description}</div>
    )}
    {footer}
  </button>
);
