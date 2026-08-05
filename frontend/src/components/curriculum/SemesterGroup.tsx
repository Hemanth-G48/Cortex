import type { ReactNode } from 'react';
import type { Subject } from '../../services/api';
import { SubjectCard } from './SubjectCard';

interface SemesterGroupProps {
  label: string;
  subjects: Subject[];
  onOpenSubject?: (id: number) => void;
  renderSubject?: (subject: Subject) => ReactNode;
}

/** A semester heading + grid of subject cards (plan Phase 53). */
export const SemesterGroup = ({ label, subjects, onOpenSubject, renderSubject }: SemesterGroupProps) => (
  <section aria-label={label} style={{ marginBottom: '1.5rem' }}>
    <h3 style={{ fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
      {label}
    </h3>
    <div className="card-grid">
      {subjects.map((s) =>
        renderSubject ? (
          <div key={s.id}>{renderSubject(s)}</div>
        ) : (
          <SubjectCard key={s.id} subject={s} onClick={() => onOpenSubject?.(s.id)} />
        ),
      )}
    </div>
  </section>
);
