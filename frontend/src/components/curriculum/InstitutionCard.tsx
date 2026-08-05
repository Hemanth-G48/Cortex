import type { Institution } from '../../services/api';

interface InstitutionCardProps {
  institution: Institution;
  selected?: boolean;
  onClick?: () => void;
}

/** Catalog card for an institution in the Browse drill-down. */
export const InstitutionCard = ({ institution, selected, onClick }: InstitutionCardProps) => (
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
      <div style={{ fontSize: '1.5rem', lineHeight: 1 }}>🏛️</div>
      {institution.is_active ? (
        <span className="badge badge-success">Active</span>
      ) : (
        <span className="badge" style={{ color: 'var(--warning)', background: 'var(--warning-muted)' }}>Pending</span>
      )}
    </div>
    <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{institution.name}</div>
    <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <span className="badge" style={{ color: 'var(--info)' }}>{institution.short_name}</span>
    </div>
    {institution.description && (
      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
        {institution.description}
      </div>
    )}
  </button>
);
