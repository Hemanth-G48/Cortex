import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { AIQuizQuestion, Note } from '../services/api';

const QUIZ_HISTORY_KEY = 'student-os-quiz-history';

interface QuizHistoryEntry {
  date: number;
  score: number;
  total: number;
  title: string;
}

const loadHistory = (): QuizHistoryEntry[] => {
  try {
    return JSON.parse(localStorage.getItem(QUIZ_HISTORY_KEY) || '[]');
  } catch {
    return [];
  }
};

const saveHistory = (h: QuizHistoryEntry[]) => {
  try {
    localStorage.setItem(QUIZ_HISTORY_KEY, JSON.stringify(h.slice(0, 12)));
  } catch {
    /* ignore */
  }
};

export const Quiz = () => {
  const [phase, setPhase] = useState<'setup' | 'quiz' | 'results'>('setup');
  const [questions, setQuestions] = useState<AIQuizQuestion[]>([]);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [answers, setAnswers] = useState<boolean[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedNote, setSelectedNote] = useState('');
  const [notes, setNotes] = useState<Note[]>([]);
  const [history, setHistory] = useState<QuizHistoryEntry[]>(loadHistory);
  const [aiMode, setAiMode] = useState('Offline');

  useEffect(() => {
    endpoints.notes.list().then(setNotes).catch(() => {});
    endpoints.ai
      .health()
      .then((h) => setAiMode(h.available && h.model ? `AI · ${h.model}` : 'Offline'))
      .catch(() => setAiMode('Offline'));
  }, []);

  const startQuiz = async () => {
    setLoading(true);
    try {
      const note = notes.find((n) => String(n.id) === String(selectedNote));
      const content = note?.content || 'General knowledge about studying and learning.';
      const res = await endpoints.ai.quiz(content);
      const qs = Array.isArray(res.questions) && res.questions.length > 0 ? res.questions : [];
      setQuestions(qs);
    } catch {
      setQuestions([]);
    }
    setLoading(false);
    setPhase('quiz');
    setCurrent(0);
    setAnswers([]);
    setSelected(null);
  };

  const handleAnswer = (idx: number) => {
    if (selected !== null) return;
    setSelected(idx);
    window.setTimeout(() => {
      const correct = idx === questions[current]?.ans;
      setAnswers((a) => [...a, correct]);
      if (current + 1 < questions.length) {
        setCurrent((c) => c + 1);
        setSelected(null);
      } else {
        const score = answers.filter(Boolean).length + (correct ? 1 : 0);
        const entry: QuizHistoryEntry = {
          date: Date.now(),
          score,
          total: questions.length,
          title: notes.find((n) => String(n.id) === String(selectedNote))?.title || 'Quiz',
        };
        const next = [entry, ...history];
        setHistory(next);
        saveHistory(next);
        setPhase('results');
      }
    }, 700);
  };

  const score = answers.filter(Boolean).length;

  const quit = () => {
    setPhase('setup');
    setCurrent(0);
    setAnswers([]);
    setSelected(null);
  };

  // ── Results ──
  if (phase === 'results') {
    const perfect = score === questions.length;
    const good = score >= Math.ceil(questions.length / 2);
    const emoji = perfect ? '🏆' : good ? '👍' : '📖';
    const color = perfect ? 'var(--warning)' : good ? 'var(--success)' : 'var(--info)';
    return (
      <div className="fade-in" style={{ maxWidth: 560, margin: '0 auto', textAlign: 'center' }}>
        <Header title="Quiz" />
        <div className="card" style={{ padding: '2.75rem' }}>
          <div
            style={{
              width: 76,
              height: 76,
              borderRadius: 22,
              margin: '0 auto 1.15rem',
              background: `${color}1f`,
              border: `1px solid ${color}55`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '2rem',
              boxShadow: `0 0 40px ${color}33`,
            }}
          >
            {emoji}
          </div>
          <h2 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.5rem' }}>{score} / {questions.length}</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            {perfect ? 'Perfect score!' : good ? 'Good job!' : 'Keep studying!'}
          </p>
          <p style={{ fontSize: '0.8rem', color: 'var(--success)', fontWeight: 700, marginBottom: '1.75rem' }}>+{score * 10} XP earned</p>
          <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'center' }}>
            <button type="button" className="btn btn-ghost" onClick={quit}>New Quiz</button>
            <button type="button" className="btn btn-primary" onClick={() => void startQuiz()}>Retry</button>
          </div>
        </div>
      </div>
    );
  }

  // ── Quiz phase ──
  if (phase === 'quiz') {
    const q = questions[current];
    if (!q) {
      return (
        <div className="fade-in" style={{ maxWidth: 560, margin: '0 auto' }}>
          <Header title="Quiz" />
          <div className="card empty-state">
            <div className="empty-icon">❓</div>
            <div className="empty-title">No questions generated</div>
            <div className="empty-message">The AI returned no questions — try again or pick a note.</div>
            <div className="empty-action">
              <button type="button" className="btn btn-primary" onClick={quit}>Back</button>
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="fade-in" style={{ maxWidth: 560, margin: '0 auto' }}>
        <Header title="Quiz" />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
            Question {current + 1} of {questions.length}
          </span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={quit}>✕ Quit</button>
        </div>
        <div style={{ height: 5, background: 'var(--bg-hover)', borderRadius: 3, overflow: 'hidden', marginBottom: '1.5rem' }}>
          <div
            style={{
              height: '100%',
              width: `${((current + 1) / questions.length) * 100}%`,
              background: 'var(--info)',
              borderRadius: 3,
              transition: 'width 0.3s',
            }}
          />
        </div>
        <div className="card" style={{ marginBottom: '1rem' }}>
          <p style={{ fontSize: '1rem', fontWeight: 600, lineHeight: 1.6 }}>{q.q}</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {q.opts.map((opt, i) => {
            let bg = 'var(--bg-card)';
            let border = 'var(--border)';
            let color = 'var(--text-primary)';
            if (selected !== null) {
              if (i === q.ans) {
                bg = 'var(--success-muted)';
                border = 'var(--success)';
                color = 'var(--success)';
              } else if (i === selected && selected !== q.ans) {
                bg = 'var(--danger-muted)';
                border = 'var(--danger)';
                color = 'var(--danger)';
              }
            }
            return (
              <button
                key={i}
                type="button"
                onClick={() => handleAnswer(i)}
                style={{
                  padding: '0.9rem 1.15rem',
                  borderRadius: 12,
                  border: `1px solid ${border}`,
                  background: bg,
                  color,
                  cursor: selected !== null ? 'default' : 'pointer',
                  textAlign: 'left',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  transition: 'all 0.2s',
                }}
              >
                {opt}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // ── Setup phase ──
  return (
    <div className="fade-in" style={{ maxWidth: 560, margin: '0 auto' }}>
      <Header title="Quiz" />
      <div className="card" style={{ padding: '1.75rem' }}>
        <h2 className="widget-title" style={{ marginBottom: '0.5rem' }}>🧠 Quiz Generator</h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Test yourself with AI-generated questions from your notes.
        </p>
        {aiMode === 'Offline' && (
          <div
            style={{
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'flex-start',
              background: 'var(--warning-muted)',
              border: '1px solid var(--warning)',
              borderRadius: 12,
              padding: '0.75rem 1rem',
              marginBottom: '1.25rem',
              fontSize: '0.75rem',
              color: 'var(--warning)',
              lineHeight: 1.5,
            }}
          >
            <span>⚠️</span> AI is offline — a sample quiz will be shown.
          </div>
        )}
        {notes.length > 0 && (
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', fontWeight: 700 }}>
              Generate from note (optional)
            </label>
            <select value={selectedNote} onChange={(e) => setSelectedNote(e.target.value)} style={{ width: '100%' }}>
              <option value="">— General knowledge —</option>
              {notes.map((n) => (
                <option key={n.id} value={n.id}>{n.title || 'Untitled'}</option>
              ))}
            </select>
          </div>
        )}
        <button type="button" className="btn btn-primary" onClick={() => void startQuiz()} disabled={loading} style={{ width: '100%', padding: '0.8rem' }}>
          {loading ? 'Generating…' : '✨ Start Quiz'}
        </button>
      </div>

      {history.length > 0 && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <h2 className="widget-title" style={{ marginBottom: '0.5rem' }}>📜 Quiz History</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {history.slice(0, 5).map((h, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.4rem 0', borderBottom: '1px solid var(--border)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>
                  {h.title} · {new Date(h.date).toLocaleDateString()}
                </span>
                <span style={{ fontWeight: 700 }}>{h.score}/{h.total}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
