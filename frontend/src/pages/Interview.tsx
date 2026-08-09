import { useState } from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import {
  endpoints,
  type InterviewSession,
  type InterviewAnswerResponse,
  type InterviewFinishResponse,
} from '../services/api';

const SKILL_SUGGESTIONS = [
  'Programming & Software Development',
  'Data Structures & Algorithms',
  'Machine Learning Foundations',
  'Deep Learning & Neural Networks',
  'Linear Algebra & Calculus',
  'Probability & Statistics',
  'Data Analysis & Visualization',
  'Natural Language Processing',
  'Computer Vision',
  'Databases & SQL',
  'Computer Networks & Security',
  'Software Engineering & Architecture',
  'Discrete Mathematics',
  'Economics & Finance',
  'Business & Management',
  'Sciences (Physics, Chemistry, Biology)',
  'Humanities & Social Sciences',
  'Writing & Communication',
];

const LEVELS = ['beginner', 'intermediate', 'advanced'] as const;

const scoreColor = (s: number) => (s >= 8 ? '#10b981' : s >= 6 ? '#f59e0b' : '#ef4444');

export const Interview = () => {
  const [skill, setSkill] = useState('');
  const [level, setLevel] = useState<string>('intermediate');
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [graded, setGraded] = useState<Record<number, InterviewAnswerResponse>>({});
  const [current, setCurrent] = useState(0);
  const [summary, setSummary] = useState<InterviewFinishResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = async () => {
    if (!skill.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await endpoints.kb.interview.start({ skill: skill.trim(), level });
      setSession(res.session);
      setAnswers({});
      setGraded({});
      setCurrent(0);
      setSummary(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const submitAnswer = async (index: number, text: string) => {
    if (!session || !text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await endpoints.kb.interview.answer(session.id, index, text);
      setGraded((g) => ({ ...g, [index]: res }));
      setSession((s) => {
        if (!s) return s;
        const total = Object.values({ ...graded, [index]: res }).reduce((acc, r) => acc + r.score, 0);
        return { ...s, total_score: total };
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const res = await endpoints.kb.interview.finish(session.id);
      setSummary(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setSession(null);
    setSummary(null);
    setGraded({});
    setAnswers({});
  };

  // ── Summary view ──
  if (summary && session) {
    return (
      <div className="page-section">
        <Header title="Interview complete" />
        <div
          className="card"
          style={{
            padding: '1.25rem',
            marginBottom: '1rem',
            textAlign: 'center',
            background: 'linear-gradient(135deg, var(--bg-card), var(--bg-hover))',
          }}
        >
          <div style={{ fontSize: '2.8rem', fontWeight: 900, lineHeight: 1 }}>
            {summary.total_score}
            <span style={{ fontSize: '1.1rem', color: 'var(--text-muted)' }}> / {session.questions.length * 10}</span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.3rem' }}>
            {summary.skill} · {summary.level} · {summary.answered} of {session.questions.length} answered
          </div>
          <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => setSkill('')} disabled>
              ✓ Scored
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={reset}>← New interview</button>
          </div>
        </div>

        <h3 style={{ fontSize: '0.85rem', margin: '0 0 0.5rem' }}>Question review</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {session.questions.map((q, i) => {
            const g = graded[i];
            return (
              <div key={i} className="card" style={{ padding: '0.85rem 1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                  <span style={{ fontSize: '0.66rem', fontWeight: 700, color: g ? scoreColor(g.score) : 'var(--text-muted)', background: g ? `${scoreColor(g.score)}1f` : 'var(--bg-hover)', borderRadius: 999, padding: '0.1rem 0.5rem' }}>
                    {g ? `${g.score}/10` : 'unanswered'}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Q{i + 1}</span>
                </div>
                <div style={{ fontSize: '0.82rem', lineHeight: 1.45, marginBottom: '0.4rem' }}>{q.question}</div>
                {g && (
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <div><strong style={{ color: '#10b981' }}>Strengths: </strong>{g.strengths.join(' · ') || '—'}</div>
                    <div><strong style={{ color: '#ef4444' }}>Misconceptions: </strong>{g.misconceptions.join(' · ') || 'none'}</div>
                    <div><strong style={{ color: '#f59e0b' }}>Next: </strong>{g.action_items.join(' · ')}</div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // ── In-progress view ──
  if (session) {
    const q = session.questions[current];
    const text = answers[current] ?? '';
    const done = Object.keys(graded).length;
    const allDone = done >= session.questions.length;

    if (!q && allDone) {
      return (
        <div className="page-section">
          <Header title="Interview" />
          <EmptyState icon="🏁" title="All questions answered" message="Finish the interview to lock in your score." />
          <button type="button" className="btn btn-primary" onClick={() => void finish()} disabled={busy} style={{ marginTop: '0.75rem' }}>
            {busy ? 'Scoring…' : '🏁 Finish interview'}
          </button>
        </div>
      );
    }

    return (
      <div className="page-section">
        <Header title={`${session.skill} interview`} />
        <div className="card" style={{ padding: '0.75rem 1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--accent)', background: 'var(--accent-muted)', borderRadius: 999, padding: '0.12rem 0.55rem' }}>{session.level}</span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            Question {current + 1} of {session.questions.length}
          </span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>answered {done}</span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.3rem' }}>
            {session.questions.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setCurrent(i)}
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 6,
                  fontSize: '0.62rem',
                  cursor: 'pointer',
                  background: graded[i] ? 'var(--accent)' : current === i ? 'var(--bg-hover)' : 'transparent',
                  color: graded[i] ? '#fff' : 'var(--text-secondary)',
                  border: '1px solid var(--border)',
                }}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div style={{ padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '0.75rem', background: '#ef444422', color: '#ef4444', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}

        <div className="card" style={{ padding: '1.1rem' }}>
          <div style={{ fontSize: '0.95rem', lineHeight: 1.55, marginBottom: '0.9rem' }}>{q.question}</div>
          <textarea
            value={text}
            onChange={(e) => setAnswers((a) => ({ ...a, [current]: e.target.value }))}
            rows={6}
            placeholder="Answer as you would in the real interview…"
            style={{ width: '100%', fontSize: '0.83rem', resize: 'vertical', marginBottom: '0.75rem' }}
          />
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void submitAnswer(current, text)}
              disabled={busy || !text.trim() || !!graded[current]}
            >
              {graded[current] ? '✓ Answered' : busy ? 'Grading…' : 'Submit answer'}
            </button>
            {graded[current] && current < session.questions.length - 1 && (
              <button type="button" className="btn btn-ghost" onClick={() => setCurrent((c) => c + 1)}>
                Next question →
              </button>
            )}
            {graded[current] && current === session.questions.length - 1 && (
              <button type="button" className="btn btn-ghost" onClick={() => void finish()} disabled={busy}>
                {busy ? 'Scoring…' : '🏁 Finish interview'}
              </button>
            )}
            <button type="button" className="btn btn-ghost btn-sm" onClick={reset} style={{ marginLeft: 'auto' }}>
              ✕ Quit
            </button>
          </div>
        </div>

        {graded[current] && (
          <div className="card" style={{ padding: '0.9rem 1rem', marginTop: '0.75rem', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '1.4rem', fontWeight: 900, color: scoreColor(graded[current].score) }}>{graded[current].score}/10</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {graded[current].ai_used ? '✨ AI grader' : '⚙️ offline grader'}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
              <div><strong style={{ color: '#10b981' }}>Strengths: </strong>{graded[current].strengths.join(' · ') || '—'}</div>
              <div><strong style={{ color: '#ef4444' }}>Misconceptions: </strong>{graded[current].misconceptions.join(' · ') || 'none'}</div>
              <div><strong style={{ color: '#f59e0b' }}>Action items: </strong>{graded[current].action_items.join(' · ')}</div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── Start view ──
  return (
    <div className="page-section">
      <Header title="Interview Prep" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Simulate a real skill interview — answer questions grounded in your vault, get a grade with strengths,
        misconceptions, and concrete next steps, then finish to grow your skill profile.
      </p>

      {error && (
        <div style={{ padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '0.75rem', background: '#ef444422', color: '#ef4444', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      <div className="card" style={{ padding: '1.1rem', maxWidth: 480 }}>
        <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
          Skill to be interviewed on
        </label>
        <input
          value={skill}
          onChange={(e) => setSkill(e.target.value)}
          list="interview-skills"
          placeholder="e.g. Machine Learning Foundations"
          style={{ width: '100%', fontSize: '0.85rem', marginBottom: '0.75rem' }}
        />
        <datalist id="interview-skills">
          {SKILL_SUGGESTIONS.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>

        <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
          Difficulty level
        </label>
        <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '1rem' }}>
          {LEVELS.map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => setLevel(l)}
              style={{
                flex: 1,
                padding: '0.45rem',
                fontSize: '0.78rem',
                borderRadius: 8,
                border: `1px solid ${level === l ? 'var(--accent)' : 'var(--border)'}`,
                background: level === l ? 'var(--accent-muted)' : 'var(--bg-hover)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {l}
            </button>
          ))}
        </div>

        <button type="button" className="btn btn-primary" onClick={() => void start()} disabled={busy || !skill.trim()} style={{ width: '100%' }}>
          {busy ? 'Preparing questions…' : '▶ Start interview'}
        </button>
      </div>
    </div>
  );
};

export default Interview;
