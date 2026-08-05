import type { Program } from '../../services/api';

interface ProgramCardProps {
  program: Program;
  selected?: boolean;
  onClick?: () => void;
}

/** Catalog card for a program (degree course) under an institution. */
export const ProgramCard = ({ program, selected, onClick }: ProgramCardProps) => (
  <button
    type="button"
    className="card curriculum-card"
    aria-pressed={!!selected}
    onClick={onClick}
    style={{
      textAlign: 'left',
      cursor: onClick ? 'pointer' : 'default',
      borderColor: selected ? 'var(--accent)' : undefined,
      boxShadow: selected ? '0 0 0 2px var(--accent-muted, transparent)' : undefined,
    }}
  >
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
      <div style={{ fontSize: '1.5rem', lineHeight: 1 }}>🎓</div>
      <span className="badge" style={{ color: 'var(--text-secondary)' }}>{program.code}</span>
    </div>
    <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{program.name}</div>
    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
      {program.duration} semesters
    </div>
    {program.description && (
      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
        {program.description}
      </div>
    )}
  </button>
);
