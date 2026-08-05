import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { useSubject } from '../hooks/useSubject';
import { useToast } from '../hooks/useToast';
import { endpoints } from '../services/api';
import type { SummaryGenerateResponse } from '../services/api';
import { Summary } from '../components/summary/Summary';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';

export const Subject = () => {
  const { id } = useParams<{ id: string }>();
  const subjectId = Number(id);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { subject, units, loading, error } = useSubject(subjectId);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [generating, setGenerating] = useState(false);
  const [summary, setSummary] = useState<SummaryGenerateResponse | null>(null);

  const toggle = (unitId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(unitId)) next.delete(unitId);
      else next.add(unitId);
      return next;
    });
  };

  const generateSummary = async () => {
    const ids = [...selected].sort((a, b) => a - b);
    if (ids.length === 0) return;
    setGenerating(true);
    setSummary(null);
    try {
      const res = await endpoints.summaries.generate(ids);
      setSummary(res);
      toast(res.cached ? 'Loaded from cache' : 'Summary generated', res.cached ? 'info' : 'success');
    } catch {
      toast('Could not generate summary', 'error');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="fade-in">
        <Header title="Subject" />
        <SkeletonCard />
      </div>
    );
  }

  if (error || !subject) {
    return (
      <div className="fade-in">
        <Header title="Subject" />
        <EmptyState icon="📘" title="Subject not found" message={error || 'This subject may have been removed.'}
          action={<Link className="btn btn-primary" to="/browse">Back to browse</Link>} />
      </div>
    );
  }

  return (
    <div className="fade-in">
      <Header title={subject.name} />

      <nav aria-label="Breadcrumb" style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem', display: 'flex', gap: '0.35rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <Link to="/browse" style={{ color: 'var(--accent)', textDecoration: 'none' }}>Browse</Link>
        <span>/</span>
        <span>{subject.code}</span>
      </nav>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{subject.name}</div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
              <span className="badge" style={{ color: 'var(--info)' }}>{subject.code}</span>
              {subject.semester != null && <span>Semester {subject.semester}</span>}
              <span>{subject.credits} credits</span>
              <span>{subject.unit_count} units</span>
            </div>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate('/browse')}>← Back</button>
        </div>
        {subject.description && (
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.75rem', lineHeight: 1.5 }}>{subject.description}</p>
        )}
      </div>

      {/* Units */}
      <div className="page-section">
        <h2>Units</h2>
        {!units || units.length === 0 ? (
          <EmptyState icon="📚" title="No units yet" message="This subject has no units — check back soon." />
        ) : (
          <div className="card-grid">
            {units.map((u) => {
              const checked = selected.has(u.id);
              return (
                <div key={u.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
                    <span className="badge" style={{ background: 'var(--bg-hover)' }}>Unit {u.unit_number}</span>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.72rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        aria-label={`Select unit ${u.unit_number} for summary`}
                        checked={checked}
                        onChange={() => toggle(u.id)}
                      />
                      Summarize
                    </label>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{u.name}</div>
                  {u.description && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {u.description}
                    </div>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'auto' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{u.material_count} materials</span>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate(`/units/${u.id}`)}>
                      Open →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Multi-unit summary */}
      <div className="page-section">
        <h2>Generate Summary</h2>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {selected.size === 0 ? 'Tick units above to combine into one summary.' : `${selected.size} unit${selected.size > 1 ? 's' : ''} selected`}
          </span>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => void generateSummary()}
            disabled={selected.size === 0 || generating}
          >
            {generating ? 'Generating…' : '✨ Generate Summary'}
          </button>
          {selected.size > 0 && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSelected(new Set())}>Clear</button>
          )}
        </div>
        {summary && (
          <Summary
            title={selected.size > 1 ? `Summary of ${selected.size} units` : `Unit ${[...selected][0]}`}
            content={summary.summary.content}
            keyPoints={summary.summary.key_points}
            cached={summary.cached}
          />
        )}
      </div>
    </div>
  );
};

export default Subject;
