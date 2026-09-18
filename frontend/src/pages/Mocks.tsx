import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import {
  endpoints,
  type SubjectProfile,
  type MockTestItem,
  type MockAttemptItem,
  type MockSubmitResponse,
  type MockQuestionItem,
} from '../services/api';

interface RunningState {
  mock: MockTestItem;
  attemptId: number;
  answers: Record<number, string>;
  remainingSecs: number;
}

export const Mocks = () => {
  const [subjects, setSubjects] = useState<SubjectProfile[]>([]);
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [title, setTitle] = useState('');
  const [count, setCount] = useState(10);
  const [duration, setDuration] = useState(45);
  const [mocks, setMocks] = useState<MockTestItem[]>([]);
  const [running, setRunning] = useState<RunningState | null>(null);
  const [result, setResult] = useState<MockSubmitResponse | null>(null);
  const [attemptsByMock, setAttemptsByMock] = useState<Record<number, MockAttemptItem[]>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Defect #75: paper status filter is a server query, and the ready-to-practice
  // bank size is hydrated from the practice question bank.
  const [statusFilter, setStatusFilter] = useState('');
  const [bankReady, setBankReady] = useState<number | null>(null);

  const loadSubjects = useCallback(async () => {
    try {
      const res = await endpoints.subjects.list();
      const confirmed = (res.items ?? []).filter((s) => s.status === 'confirmed');
      setSubjects(confirmed);
      if (confirmed.length) setSubjectId(confirmed[0].curriculum_subject_id ?? confirmed[0].id);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const loadMocks = useCallback(async () => {
    try {
      const res = await endpoints.kb.mocks.list(statusFilter || undefined);
      setMocks(res.items ?? []);
    } catch (e) {
      setError((e as Error).message);
    }
    // Hydrate the practice bank readiness (approved questions = practice-ready).
    try {
      const bank = await endpoints.kb.practice.questions({ status: 'approved' });
      setBankReady(bank.items?.length ?? 0);
    } catch {
      setBankReady(null);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadSubjects();
    void loadMocks();
  }, [loadSubjects, loadMocks]);

  // Countdown while a paper is running
  const attemptId = running?.attemptId;
  useEffect(() => {
    if (attemptId == null) return;
    const iv = window.setInterval(() => {
      setRunning((r) => {
        if (!r) return r;
        const next = r.remainingSecs - 1;
        return next <= 0 ? { ...r, remainingSecs: 0 } : { ...r, remainingSecs: next };
      });
    }, 1000);
    return () => window.clearInterval(iv);
  }, [attemptId]);

  const build = async () => {
    if (subjectId == null) return;
    setBusy(true);
    setError(null);
    try {
      const res = await endpoints.kb.mocks.build({
        subject_id: subjectId,
        title: title.trim() || undefined,
        question_count: count,
        duration_mins: duration,
      });
      setMocks((m) => [res.mock, ...m]);
      setTitle('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const start = async (mock: MockTestItem) => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await endpoints.kb.mocks.start(mock.id);
      setRunning({
        mock,
        attemptId: res.attempt.id,
        answers: {},
        remainingSecs: (mock.duration_mins ?? 45) * 60,
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!running) return;
    setBusy(true);
    setError(null);
    try {
      const res = await endpoints.kb.mocks.submit(running.attemptId, running.answers);
      setResult(res);
      setRunning(null);
      await loadMocks();
      await loadAttempts(res.mock_test_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const loadAttempts = async (mockId: number) => {
    try {
      const res = await endpoints.kb.mocks.attempts(mockId);
      setAttemptsByMock((a) => ({ ...a, [mockId]: res.items ?? [] }));
    } catch {
      /* non-critical */
    }
  };

  const fmtClock = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  // ── Exam runner view ──
  if (running) {
    const { mock, answers, remainingSecs } = running;
    const questions = mock.questions ?? [];
    const answered = Object.keys(answers).length;
    const over = remainingSecs <= 0;
    return (
      <div className="page-section">
        <Header title={mock.title} />
        <div
          className="card"
          style={{
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            flexWrap: 'wrap',
          }}
        >
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{questions.length} questions</span>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>⏱ {fmtClock(remainingSecs)}</span>
          <span style={{ fontSize: '0.72rem', color: over ? '#ef4444' : 'var(--text-secondary)' }}>
            {over ? '⛔ time is up — submit!' : `${answered}/${questions.length} answered`}
          </span>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={busy} style={{ marginLeft: 'auto' }}>
            {busy ? 'Submitting…' : 'Submit paper'}
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
          {questions.map((q, qi) => (
            <QuestionCard key={q.id} q={q} index={qi} selected={answers[q.id]} onSelect={(v) => setRunning((r) => r && { ...r, answers: { ...r.answers, [q.id]: v } })} />
          ))}
        </div>
        <div style={{ marginTop: '1rem' }}>
          <button type="button" className="btn btn-primary" onClick={() => void submit()} disabled={busy}>
            {busy ? 'Submitting…' : 'Submit paper'}
          </button>
        </div>
      </div>
    );
  }

  // ── Result view ──
  if (result) {
    return (
      <div className="page-section">
        <Header title="Result" />
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
            {Math.round(result.percentage)}<span style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>%</span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.3rem' }}>
            {result.score} / {result.total} correct{result.late_submission ? ' · ⚠ late submission' : ''}
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setResult(null)} style={{ marginTop: '0.75rem' }}>
            ← Back to papers
          </button>
        </div>
        <h3 style={{ fontSize: '0.85rem', margin: '0 0 0.5rem' }}>Per-topic breakdown</h3>
        <div className="card" style={{ padding: '0.85rem 1rem' }}>
          {Object.entries(result.per_topic).length === 0 ? (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No topic data recorded.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {Object.entries(result.per_topic).map(([tid, b]) => (
                <div key={tid} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', minWidth: 80 }}>Topic #{tid}</span>
                  <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--bg-hover)', overflow: 'hidden' }}>
                    <div style={{ width: `${(b.correct / Math.max(1, b.total)) * 100}%`, height: '100%', background: b.correct === b.total ? '#10b981' : '#f59e0b' }} />
                  </div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{b.correct}/{b.total}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="page-section">
      <Header title="Mock Exams" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Build timed exam papers from your approved question bank, run them under the clock, and get per-topic scores.
      </p>

      {error && (
        <div style={{ padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '0.75rem', background: '#ef444422', color: '#ef4444', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Build form */}
      <div className="card" style={{ padding: '1rem', marginBottom: '1rem' }}>
        <h3 style={{ fontSize: '0.85rem', margin: '0 0 0.6rem' }}>Build a paper</h3>
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Subject
            <select value={subjectId ?? ''} onChange={(e) => setSubjectId(Number(e.target.value) || null)} style={{ display: 'block', marginTop: '0.25rem', minWidth: 200 }}>
              {subjects.map((s) => (
                <option key={s.id} value={s.curriculum_subject_id ?? s.id}>
                  {s.parsed?.title ?? `Subject #${s.id}`}
                </option>
              ))}
            </select>
          </label>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Midterm Mock" style={{ display: 'block', marginTop: '0.25rem', width: 160 }} />
          </label>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Questions
            <input type="number" min={3} max={50} value={count} onChange={(e) => setCount(Number(e.target.value))} style={{ display: 'block', marginTop: '0.25rem', width: 90 }} />
          </label>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Minutes
            <input type="number" min={5} max={240} value={duration} onChange={(e) => setDuration(Number(e.target.value))} style={{ display: 'block', marginTop: '0.25rem', width: 90 }} />
          </label>
          <button type="button" className="btn btn-primary" onClick={() => void build()} disabled={busy || subjectId == null}>
            {busy ? 'Building…' : '＋ Build paper'}
          </button>
          {/* Defect #75: which papers to list is decided by the server. */}
          <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Show
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ display: 'block', marginTop: '0.25rem', width: 140 }}
            >
              <option value="">All papers</option>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
            </select>
          </label>
          {bankReady !== null && (
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              {bankReady} approved practice question{bankReady === 1 ? '' : 's'} in the bank
            </span>
          )}
        </div>
      </div>

      {/* Paper list */}
      {mocks.length === 0 ? (
        <EmptyState icon="📝" title="No mock papers yet" message="Build your first timed paper from a confirmed subject’s question bank." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {mocks.map((mock) => {
            const attempts = attemptsByMock[mock.id] ?? [];
            return (
              <div key={mock.id} className="card" style={{ padding: '0.85rem 1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: '0.85rem', flex: 1 }}>{mock.title}</strong>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    {mock.question_count} Qs · {mock.duration_mins} min
                    {mock.attempt_count ? ` · ${mock.attempt_count} attempt${mock.attempt_count === 1 ? '' : 's'}` : ''}
                  </span>
                  <button type="button" className="btn btn-primary btn-sm" onClick={() => void start(mock)} disabled={busy}>
                    ▶ Start
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => attempts.length === 0 ? void loadAttempts(mock.id) : setAttemptsByMock((a) => ({ ...a, [mock.id]: [] }))}
                  >
                    {attempts.length ? 'Hide' : 'Attempts'}
                  </button>
                </div>
                {attempts.length > 0 && (
                  <div style={{ marginTop: '0.6rem', borderTop: '1px solid var(--border)', paddingTop: '0.6rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {attempts.map((a) => (
                        <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          <span>#{a.id}</span>
                          <span>{a.started_at ? new Date(a.started_at).toLocaleString() : '—'}</span>
                          <strong style={{ marginLeft: 'auto', color: a.total && a.score / a.total >= 0.6 ? '#10b981' : '#f59e0b' }}>
                            {a.score}/{a.total}
                          </strong>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const QuestionCard = ({ q, index, selected, onSelect }: { q: MockQuestionItem; index: number; selected?: string; onSelect: (v: string) => void }) => (
  <div className="card" style={{ padding: '0.85rem 1rem' }}>
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.4rem' }}>
      <span style={{ fontSize: '0.66rem', fontWeight: 700, color: 'var(--accent)', background: 'var(--accent-muted)', borderRadius: 999, padding: '0.1rem 0.5rem' }}>
        Q{index + 1}
      </span>
      <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>{q.difficulty}</span>
    </div>
    <div style={{ fontSize: '0.83rem', lineHeight: 1.45, marginBottom: '0.6rem' }}>{q.question}</div>
    {q.options.length > 0 && (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        {q.options.map((o, i) => {
          const val = String.fromCharCode(65 + i);
          const active = selected === o;
          return (
            <button
              key={i}
              type="button"
              // Submit the option *text* — the backend scores `answer === option text`.
              onClick={() => onSelect(o)}
              style={{
                textAlign: 'left',
                fontSize: '0.78rem',
                padding: '0.45rem 0.7rem',
                borderRadius: 8,
                border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
                background: active ? 'var(--accent-muted)' : 'var(--bg-hover)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
              }}
            >
              {val}. {o}
            </button>
          );
        })}
      </div>
    )}
    {q.options.length === 0 && (
      <input
        value={selected ?? ''}
        onChange={(e) => onSelect(e.target.value)}
        placeholder="Type your answer…"
        style={{ width: '100%', fontSize: '0.8rem' }}
      />
    )}
  </div>
);

export default Mocks;
