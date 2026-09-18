import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints, kbRelatedApi, moodApi } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import { EmptyState } from '../components/shared/EmptyState';
import { SkeletonCard } from '../components/shared/Skeleton';
import type { JournalEntry } from '../services/api';

// Mood chips are ordered/weighted by the user's actual mood distribution
// from the backend (defect #41 fix). Fall back to a sensible default when
// the mood subsystem is offline or empty.
const DEFAULT_MOODS = ['happy', 'neutral', 'sad', 'anxious', 'excited'] as const;

const moodEmoji: Record<string, string> = {
  happy: '😊', neutral: '😐', sad: '😔', anxious: '😰', excited: '🎉',
  focused: '🎯', relaxed: '😌', stressed: '😰',
};

export const Journal = () => {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [entryLinks, setEntryLinks] = useState<Record<number, { id: number; title: string; relation: string | null }[]>>({});
  const [showForm, setShowForm] = useState(false);
  const [content, setContent] = useState('');
  const [mood, setMood] = useState('happy');
  const [tags, setTags] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  // Defect #20 fix: editing support.
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState('');

  const [moods, setMoods] = useState<readonly string[]>(DEFAULT_MOODS);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    endpoints.journal.list()
      .then((entries) => {
        setEntries(entries);
        // Defect #42 fix: cross-link each journal entry to KB notes that mention it.
        const links: Record<number, { id: number; title: string; relation: string | null }[]> = {};
        Promise.all(
          entries.map((e) =>
            kbRelatedApi.forDocument(e.id)
              .then((r) => { links[e.id] = r.related; })
              .catch(() => {})
          )
        ).then(() => setEntryLinks(links));
      })
      // Defect #19 fix: surface load failures.
      .catch(() => setError('Could not load journal entries — is the backend running?'))
      .finally(() => setLoading(false));
    // Fetch the user's real mood distribution to order/weight the chips.
    moodApi.analytics()
      .then((res) => {
        if (res.distribution && res.distribution.length) {
          // Sort by count descending — most common moods float to the left.
          const ranked = res.distribution
            .filter((d) => d.count > 0)
            .sort((x, y) => y.count - x.count)
            .map((d) => d.mood);
          if (ranked.length) setMoods(ranked);
        }
      })
      .catch(() => setMoods(DEFAULT_MOODS));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Defect #19 fix: report save failures to the user.
  const handleSubmit = async () => {
    if (!content.trim()) return;
    setSaveError(null);
    try {
      await endpoints.journal.create({
        date: new Date().toISOString().split('T')[0],
        content, mood, tags,
        user_id: 1,
      });
      setContent(''); setMood('happy'); setTags('');
      setShowForm(false);
      load();
    } catch {
      setSaveError('Could not save the entry — try again.');
    }
  };

  const handleEdit = async () => {
    if (editingId === null || !editContent.trim()) return;
    setSaveError(null);
    try {
      await endpoints.journal.update(editingId, { content: editContent });
      setEditingId(null);
      load();
    } catch {
      setSaveError('Could not save the entry — try again.');
    }
  };

  // Defect #84 fix: delete with confirmation.
  const handleDelete = (id: number) => {
    if (!confirmDelete('this journal entry')) return;
    endpoints.journal.delete(id).then(load).catch(() => setError('Could not delete the entry'));
  };

  return (
    <div>
      <Header title="Journal & Reflection" />
      <button
        className="badge badge-info"
        style={{ cursor: 'pointer', border: 'none', padding: '0.5rem 1rem', marginBottom: '1rem', fontSize: '0.9rem' }}
        onClick={() => setShowForm(!showForm)}
      >
        {showForm ? '− Cancel' : '+ New Entry'}
      </button>
      {showForm && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <textarea
            placeholder="What's on your mind?"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            style={{ width: '100%', minHeight: '100px', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text-primary)', padding: '0.75rem', marginBottom: '0.75rem', resize: 'vertical' }}
          />
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Mood:</span>
            {moods.map((m) => (
              <button
                key={m}
                onClick={() => setMood(m)}
                style={{ background: mood === m ? 'var(--accent-muted)' : 'transparent', border: mood === m ? '1px solid var(--accent)' : '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '0.25rem 0.5rem', cursor: 'pointer', fontSize: '1rem' }}
              >{moodEmoji[m]}</button>
            ))}
          </div>
          <input
            placeholder="Tags (comma-separated)"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            style={{ width: '100%', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text-primary)', padding: '0.5rem 0.75rem', marginBottom: '0.75rem' }}
          />
          <button className="badge badge-success" style={{ cursor: 'pointer', border: 'none', padding: '0.5rem 1rem' }} onClick={() => void handleSubmit()}>Save Entry</button>
          {saveError && <div style={{ color: 'var(--danger)', fontSize: '0.8rem', marginTop: '0.5rem' }}>⚠ {saveError}</div>}
        </div>
      )}
      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}
      <div className="card-grid">
        {loading ? (
          // Defect #21 fix: skeletons while entries load.
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : entries.length === 0 ? (
          <EmptyState
            icon="📓"
            title="No journal entries yet"
            message="Write your first reflection to start tracking your moods and thoughts."
            action={<button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>+ New Entry</button>}
          />
        ) : entries.map((e) => (
          <div className="card" key={e.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{e.date}</span>
              <span style={{ fontSize: '1.2rem' }}>{moodEmoji[e.mood ?? ''] ?? '😐'}</span>
            </div>
            {editingId === e.id ? (
              <div>
                <textarea
                  value={editContent}
                  onChange={(ev) => setEditContent(ev.target.value)}
                  style={{ width: '100%', minHeight: '80px', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text-primary)', padding: '0.5rem', marginBottom: '0.5rem', resize: 'vertical' }}
                />
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button className="badge badge-success" style={{ cursor: 'pointer', border: 'none', padding: '0.35rem 0.75rem' }} onClick={() => void handleEdit()}>Save</button>
                  <button className="badge badge-info" style={{ cursor: 'pointer', border: 'none', padding: '0.35rem 0.75rem' }} onClick={() => setEditingId(null)}>Cancel</button>
                </div>
              </div>
            ) : (
              <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', lineClamp: 5, WebkitLineClamp: 5, display: '-webkit-box', WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{e.content}</p>
            )}
            {e.tags && (
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                {e.tags.split(',').map((t, i) => (
                  <span key={i} className="badge badge-info" style={{ fontSize: '0.7rem' }}>{t.trim()}</span>
                ))}
              </div>
            )}
            {/* Defect #42 fix: related KB notes linked to this journal entry. */}
            {entryLinks[e.id]?.length && (
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                {entryLinks[e.id].map((l) => (
                  <span key={l.id} className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                    {l.title}
                  </span>
                ))}
              </div>
            )}
            {/* Defects #20/#84 fix: edit + delete actions. */}
            {editingId !== e.id && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                <button
                  onClick={() => { setEditingId(e.id); setEditContent(e.content); }}
                  style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.75rem' }}
                >Edit</button>
                <button
                  onClick={() => handleDelete(e.id)}
                  style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.75rem' }}
                >Delete</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
