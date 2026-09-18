import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { endpoints } from '../../services/api';
import type { EnrollmentSummary, Subject } from '../../services/api';
import { SkeletonCard } from '../shared/Skeleton';
import { EmptyState } from '../shared/EmptyState';

/** Dashboard section: enrolled program, subjects by semester, quick links. */
export const CurriculumSection = () => {
  const [summary, setSummary] = useState<EnrollmentSummary | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    endpoints.enrollment
      .summary()
      .then((s) => {
        setSummary(s);
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, []);

  const semesterGroups = useMemo(() => {
    if (!summary?.subjects.length) return [];
    const groups = new Map<string, Subject[]>();
    for (const s of summary.subjects) {
      // Defect #9: the label is resolved by the backend — render it verbatim.
      const key = s.semester_label ?? 'Other';
      groups.set(key, [...(groups.get(key) ?? []), s]);
    }
    return [...groups.entries()];
  }, [summary]);

  if (!loaded) {
    return (
      <div className="page-section">
        <h2>My Curriculum</h2>
        <SkeletonCard />
      </div>
    );
  }

  if (!summary?.institution_name) {
    return (
      <div className="page-section">
        <h2>My Curriculum</h2>
        <EmptyState
          icon="🎓"
          title="Not enrolled in a program"
          message="Complete your profile to see your curriculum, materials and quiz progress here."
          action={<Link className="btn btn-primary" to="/complete-profile">Complete profile</Link>}
        />
      </div>
    );
  }

  const avgQuiz = summary.avg_quiz_percentage != null ? `${Math.round(summary.avg_quiz_percentage)}%` : '—';

  return (
    <div className="page-section">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <h2 style={{ marginBottom: 0 }}>My Curriculum</h2>
        <span className="badge badge-info">{summary.institution_name} · {summary.program_name}</span>
      </div>

      <div className="stat-grid" style={{ marginBottom: '1rem' }}>
        <div className="stat-tile"><div className="label">Subjects</div><div className="value">{summary.subjects.length}</div></div>
        <div className="stat-tile"><div className="label">Units</div><div className="value">{summary.units.length}</div></div>
        <div className="stat-tile"><div className="label">Materials</div><div className="value">{summary.material_count}</div></div>
        <div className="stat-tile"><div className="label">Quiz attempts</div><div className="value">{summary.quiz_attempts}</div></div>
        <div className="stat-tile"><div className="label">Avg quiz score</div><div className="value">{avgQuiz}</div></div>
      </div>

      {semesterGroups.map(([label, subjects]) => (
        <div key={label} style={{ marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>{label}</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {subjects.map((s) => (
              <Link
                key={s.id}
                to={`/subjects/${s.id}`}
                className="badge"
                style={{
                  padding: '0.45rem 0.7rem',
                  color: 'var(--text-primary)',
                  background: 'var(--bg-hover)',
                  textDecoration: 'none',
                  border: '1px solid var(--border)',
                }}
              >
                {s.code} · {s.name}
              </Link>
            ))}
          </div>
        </div>
      ))}

      <Link to="/browse" style={{ fontSize: '0.8rem', color: 'var(--accent)', textDecoration: 'none' }}>
        Browse full catalog →
      </Link>
    </div>
  );
};
