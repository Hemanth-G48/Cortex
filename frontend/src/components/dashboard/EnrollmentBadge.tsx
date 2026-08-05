import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { endpoints } from '../../services/api';
import type { EnrollmentSummary } from '../../services/api';

/** Dashboard widget showing the student's enrolled institution + program. */
export const EnrollmentBadge = () => {
  const [summary, setSummary] = useState<EnrollmentSummary | null>(null);

  useEffect(() => {
    endpoints.enrollment
      .summary()
      .then(setSummary)
      .catch(() => undefined);
  }, []);

  if (!summary?.institution_name) {
    return (
      <div className="card" style={{ padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Not enrolled yet</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Pick your institution & program.</div>
        </div>
        <Link className="btn btn-primary btn-sm" to="/complete-profile">Enroll</Link>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>🎓 {summary.institution_name}</div>
        <span className="badge badge-info">{summary.program_name}</span>
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
        <span>{summary.subjects.length} subjects</span>
        <span>{summary.units.length} units</span>
        <span>{summary.material_count} materials</span>
      </div>
      <Link
        to="/browse"
        style={{ display: 'inline-block', marginTop: '0.6rem', fontSize: '0.75rem', color: 'var(--accent)', textDecoration: 'none' }}
      >
        Browse catalog →
      </Link>
    </div>
  );
};
