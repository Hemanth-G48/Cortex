import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';
import type { LifeArea } from '../services/api';

export const LifeAreas = () => {
  const [areas, setAreas] = useState<LifeArea[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', satisfaction_score: 5, goal: '' });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    endpoints.lifeAreas.list()
      .then(setAreas)
      // Defect #35 fix: surface load failures.
      .catch(() => setError('Could not load life areas — is the backend running?'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Defect #34 fix: create/delete from this page.
  const handleCreate = async () => {
    if (!form.name.trim()) return;
    try {
      await endpoints.lifeAreas.create({
        name: form.name.trim(),
        satisfaction_score: Number(form.satisfaction_score) || 1,
        goal: form.goal || null,
      });
      setForm({ name: '', satisfaction_score: 5, goal: '' });
      setShowCreate(false);
      load();
    } catch {
      setError('Could not create the life area');
    }
  };

  const handleDelete = (id: number) => {
    if (!confirmDelete('this life area')) return;
    endpoints.lifeAreas.delete(id).then(load).catch(() => setError('Could not delete the life area'));
  };

  // Inline satisfaction adjustment.
  const setScore = (a: LifeArea, score: number) => {
    endpoints.lifeAreas.update(a.id, { satisfaction_score: Math.max(1, Math.min(10, score)) })
      .then(load)
      .catch(() => setError('Could not update the life area'));
  };

  const avgScore = areas.length ? Math.round(areas.reduce((s, a) => s + a.satisfaction_score, 0) / areas.length * 10) / 10 : 0;

  const renderDots = (score: number) =>
    Array.from({ length: 10 }, (_, i) => (
      <span key={i} style={{ color: i < score ? 'var(--accent)' : 'var(--border)', fontSize: '1.25rem', lineHeight: 1 }}>●</span>
    ));

  return (
    <div>
      <Header title="Life Areas" />
      <div style={{ marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? '− Cancel' : '+ New Life Area'}
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <input placeholder="Area name (e.g. Health, Career, Relationships)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input type="number" min={1} max={10} placeholder="Satisfaction (1-10)" value={form.satisfaction_score} onChange={(e) => setForm({ ...form, satisfaction_score: Number(e.target.value) })} style={{ width: 170 }} />
            <input placeholder="Goal (optional)" value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} style={{ flex: 1, minWidth: 200 }} />
            <button type="button" className="btn btn-primary" onClick={() => void handleCreate()} disabled={!form.name.trim()}>Create</button>
          </div>
        </div>
      )}

      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Areas Tracked</div><div className="value">{areas.length}</div></div>
        <div className="stat-tile"><div className="label">Avg Satisfaction</div><div className="value">{avgScore}/10</div></div>
      </div>
      <div className="card-grid">
        {loading ? (
          // Defect #35/#88 fix: skeletons while loading.
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : areas.length === 0 ? (
          <EmptyState
            icon="🎯"
            title="No life areas yet"
            message="Track the areas of your life that matter most."
            action={<button type="button" className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Life Area</button>}
          />
        ) : areas.map((a) => (
          <div className="card" key={a.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
              <h3 style={{ marginBottom: '0.5rem' }}>{a.name}</h3>
              <button onClick={() => handleDelete(a.id)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>✕</button>
            </div>
            <div style={{ marginBottom: '0.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Satisfaction: {a.satisfaction_score}/10</div>
              <div>{renderDots(a.satisfaction_score)}</div>
              <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.25rem' }}>
                <button className="btn btn-ghost btn-sm" onClick={() => setScore(a, a.satisfaction_score - 1)} aria-label="Lower satisfaction">−</button>
                <button className="btn btn-ghost btn-sm" onClick={() => setScore(a, a.satisfaction_score + 1)} aria-label="Raise satisfaction">＋</button>
              </div>
            </div>
            {a.goal && (
              <div style={{ paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.15rem' }}>Goal</div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{a.goal}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
