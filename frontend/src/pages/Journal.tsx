import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { JournalEntry } from '../services/api';

const MOODS = ['happy', 'neutral', 'sad', 'anxious', 'excited'] as const;

const moodEmoji: Record<string, string> = {
  happy: '😊', neutral: '😐', sad: '😔', anxious: '😰', excited: '🎉',
};

export const Journal = () => {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [content, setContent] = useState('');
  const [mood, setMood] = useState('happy');
  const [tags, setTags] = useState('');

  const load = () => endpoints.journal.list().then(setEntries).catch(() => {});

  useEffect(() => { load(); }, []);

  const handleSubmit = () => {
    if (!content.trim()) return;
    endpoints.journal.create({
      date: new Date().toISOString().split('T')[0],
      content, mood, tags,
      user_id: 1,
    }).then(() => {
      setContent(''); setMood('happy'); setTags('');
      setShowForm(false);
      load();
    });
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
            {MOODS.map((m) => (
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
          <button className="badge badge-success" style={{ cursor: 'pointer', border: 'none', padding: '0.5rem 1rem' }} onClick={handleSubmit}>Save Entry</button>
        </div>
      )}
      <div className="card-grid">
        {entries.map((e) => (
          <div className="card" key={e.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{e.date}</span>
              <span style={{ fontSize: '1.2rem' }}>{moodEmoji[e.mood ?? ''] ?? '😐'}</span>
            </div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', lineClamp: 5, WebkitLineClamp: 5, display: '-webkit-box', WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{e.content}</p>
            {e.tags && (
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                {e.tags.split(',').map((t, i) => (
                  <span key={i} className="badge badge-info" style={{ fontSize: '0.7rem' }}>{t.trim()}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
