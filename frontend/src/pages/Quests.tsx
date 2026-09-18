import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';
import type { Quest, QuestCentreBoard } from '../services/api';

export const Quests = () => {
  // Defect #23 fix: filter persisted in the URL so it survives navigation.
  const [searchParams, setSearchParams] = useSearchParams();
  const filter = searchParams.get('category') ?? '';
  const setFilter = useCallback((cat: string) => {
    if (cat) setSearchParams({ category: cat }, { replace: true });
    else setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  const [quests, setQuests] = useState<Quest[]>([]);
  const [board, setBoard] = useState<QuestCentreBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', xp_reward: 50, due_date: '' });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    endpoints.quests.list(filter || undefined)
      .then(setQuests)
      .catch(() => setError('Could not load quests — is the backend running?'))
      .finally(() => setLoading(false));
    // Defect #88 fix: authoritative status counts + shared XP wallet.
    endpoints.questCentre.board().then(setBoard).catch(() => {});
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  // Defect #22 fix: quest create/delete on this page.
  const handleCreate = async () => {
    if (!form.title.trim()) return;
    try {
      await endpoints.quests.create({
        title: form.title.trim(),
        description: form.description || null,
        xp_reward: Number(form.xp_reward) || 50,
        due_date: form.due_date || null,
      });
      setForm({ title: '', description: '', xp_reward: 50, due_date: '' });
      setShowCreate(false);
      load();
    } catch {
      setError('Could not create quest');
    }
  };

  const handleDelete = (id: number) => {
    if (!confirmDelete('this quest')) return;
    endpoints.quests.delete(id).then(load).catch(() => setError('Could not delete quest'));
  };

  const handleComplete = (q: Quest) => {
    endpoints.quests.complete(q.id).then(load).catch(() => setError('Could not complete quest'));
  };

  const totalXp = quests.filter((q) => q.status === 'Completed').reduce((s, q) => s + q.xp_reward, 0);
  const boardQuests = board?.quests;
  const activeCount = boardQuests ? boardQuests.open : quests.filter((q) => q.status !== 'Completed').length;
  const completedCount = boardQuests ? boardQuests.completed : quests.filter((q) => q.status === 'Completed').length;
  const earnedXp = board ? Math.max(board.characters.total_xp, totalXp) : totalXp;

  return (
    <div>
      <Header title="Quest Center" />
      <div style={{ marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? '− Cancel' : '+ New Quest'}
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <input placeholder="Quest title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input placeholder="Description (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input type="number" placeholder="XP reward" value={form.xp_reward} onChange={(e) => setForm({ ...form, xp_reward: Number(e.target.value) })} style={{ width: 120 }} />
            <input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} style={{ width: 180 }} />
            <button type="button" className="btn btn-primary" onClick={() => void handleCreate()} disabled={!form.title.trim()}>Create</button>
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-2 flex-wrap">
        <button className={`btn btn-sm ${filter === '' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFilter('')}>All</button>
        {(['Work', 'Fitness', 'Personal', 'Learning', 'Social', 'Health'] as const).map((cat) => (
          <button key={cat} className={`btn btn-sm ${filter === cat ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFilter(cat)}>
            {cat}
          </button>
        ))}
      </div>
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Active Quests</div><div className="value">{activeCount}</div></div>
        <div className="stat-tile"><div className="label">Completed</div><div className="value">{completedCount}</div></div>
        <div className="stat-tile"><div className="label">Total XP Earned</div><div className="value">{earnedXp}</div></div>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}

      <div className="card-grid">
        {loading ? (
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : quests.length === 0 ? (
          <EmptyState
            icon="⚔️"
            title="No quests found"
            message={filter ? `No quests in the ${filter} category.` : 'Create your first quest to start earning XP.'}
            action={<button type="button" className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Quest</button>}
          />
        ) : quests.map((q) => (
          <div className="card" key={q.id} style={{ borderLeft: `3px solid ${q.status === 'Completed' ? 'var(--success)' : q.status === 'In progress' ? 'var(--warning)' : 'var(--border)'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <h3>{q.title}</h3>
              <span className="badge badge-warning">+{q.xp_reward} XP</span>
            </div>
            {q.description && <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>{q.description}</p>}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span className={`badge badge-${q.status === 'Completed' ? 'success' : q.status === 'In progress' ? 'warning' : 'info'}`}>{q.status}</span>
              {q.due_date && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Due: {q.due_date}</span>}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
              {q.status !== 'Completed' && (
                <button className="badge badge-success" style={{ cursor: 'pointer', border: 'none' }} onClick={() => handleComplete(q)}>✓ Complete</button>
              )}
              <button onClick={() => handleDelete(q.id)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.75rem' }}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
