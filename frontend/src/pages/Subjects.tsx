import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { SkeletonCard } from '../components/shared/Skeleton';
import { endpoints } from '../services/api';
import type { SubjectProfile, SubjectProfileStatus } from '../services/api';

const statusColor: Record<string, string> = {
  proposed: 'var(--warning)',
  confirmed: 'var(--success)',
  rejected: 'var(--danger)',
};

const statusIcon: Record<string, string> = {
  proposed: '⏳',
  confirmed: '✅',
  rejected: '🚫',
};

const STATUSES: (SubjectProfileStatus | '')[] = ['', 'proposed', 'confirmed', 'rejected'];

/** Phase 5 subject list (Idea 43, phrase 26–28): semester facet + status. */
export const Subjects = () => {
  // ``all`` is the unfiltered master list — facets (semesters, status counts)
  // are derived from it so they never collapse while a filter is active.
  const [all, setAll] = useState<SubjectProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [semester, setSemester] = useState('');
  const [status, setStatus] = useState<SubjectProfileStatus | ''>('');

  const load = useCallback(() => {
    setLoading(true);
    endpoints.subjects
      .list()
      .then((r) => setAll(r.items))
      .catch(() => setAll([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Client-side filtering so the facet chips stay stable under any filter.
  const items = useMemo(
    () =>
      all.filter(
        (i) =>
          (!semester || i.semester === semester) &&
          (!status || i.status === status),
      ),
    [all, semester, status],
  );

  const semesters = useMemo(() => {
    const seen = new Set<string>();
    for (const i of all) {
      if (i.semester && !seen.has(i.semester)) seen.add(i.semester);
    }
    return Array.from(seen).sort((a, b) => a.localeCompare(b));
  }, [all]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { proposed: 0, confirmed: 0, rejected: 0 };
    for (const i of all) c[i.status] = (c[i.status] ?? 0) + 1;
    return c;
  }, [all]);

  return (
    <div className="fade-in" style={{ maxWidth: 900 }}>
      <Header title="Subjects" />

      {/* Actions */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
        <Link to="/import" className="btn btn-primary btn-sm">📥 Import Syllabus</Link>
      </div>

      {/* Semester + status facets */}
      <div className="card" style={{ padding: '0.9rem 1rem', marginBottom: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Semester
        </span>
        <button
          type="button"
          className="badge"
          style={{ cursor: 'pointer', border: 'none', background: semester === '' ? 'var(--accent)' : 'var(--bg-hover)', color: semester === '' ? '#0b0e14' : 'var(--text-secondary)', padding: '0.35rem 0.7rem' }}
          onClick={() => setSemester('')}
        >
          All
        </button>
        {semesters.map((s) => (
          <button
            key={s}
            type="button"
            className="badge"
            style={{ cursor: 'pointer', border: 'none', background: semester === s ? 'var(--accent)' : 'var(--bg-hover)', color: semester === s ? '#0b0e14' : 'var(--text-secondary)', padding: '0.35rem 0.7rem' }}
            onClick={() => setSemester(s)}
          >
            🗓 {s}
          </button>
        ))}
        <span style={{ width: 1, height: 22, background: 'var(--border)', margin: '0 0.4rem' }} />
        {STATUSES.map((st) => (
          <button
            key={st || 'all'}
            type="button"
            className="badge"
            style={{ cursor: 'pointer', border: 'none', background: status === st ? (st ? statusColor[st] : 'var(--accent)') : 'var(--bg-hover)', color: status === st ? '#0b0e14' : 'var(--text-secondary)', padding: '0.35rem 0.7rem', textTransform: 'capitalize' }}
            onClick={() => setStatus(st)}
          >
            {st ? `${statusIcon[st]} ${st} (${counts[st] ?? 0})` : 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <SkeletonCard />
      ) : items.length === 0 ? (
        <EmptyState
          icon="📘"
          title="No subjects yet"
          message="Import a syllabus to auto-create your first subject profile — you review it before anything is written."
          action={<Link className="btn btn-primary" to="/import">Import a syllabus</Link>}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {items.map((p) => (
            <div key={p.id} className="card" style={{ padding: '1rem 1.15rem', display: 'flex', alignItems: 'center', gap: '1rem', transition: 'transform 0.15s ease, box-shadow 0.15s ease' }}
              onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = 'var(--shadow-md, 0 6px 24px rgba(0,0,0,0.12))'; }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
            >
              <div style={{ fontSize: '1.4rem' }}>{statusIcon[p.status]}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{p.parsed?.title ?? 'Untitled Subject'}</span>
                  <span className="badge" style={{ color: statusColor[p.status], background: `${statusColor[p.status]}22`, textTransform: 'capitalize' }}>{p.status}</span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.3rem' }}>
                  {p.semester && <span className="badge" style={{ color: 'var(--info)' }}>🗓 {p.semester}</span>}
                  {p.parsed?.credits != null && <span>{p.parsed.credits} credits</span>}
                  <span>{p.parsed?.units.length ?? 0} units</span>
                  {p.curriculum_subject_id && <span>· {p.topics_count} topics</span>}
                </div>
              </div>
              {p.status === 'proposed' ? (
                <Link className="btn btn-sm" to={`/subjects/profiles/${p.id}`}>Review →</Link>
              ) : (
                <Link className="btn btn-sm" to={`/subjects/profiles/${p.id}`}>Open →</Link>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Subjects;
