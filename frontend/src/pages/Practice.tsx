import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import {
  endpoints,
  type SubjectProfile,
  type TopicItem,
  type PracticeQuestionItem,
  type AdaptiveSession,
  type PracticeAnswerResponse,
  type MistakeAnalysisResponse,
} from '../services/api';

type Tab = 'bank' | 'adaptive' | 'mistakes';

const difficultyColor = (d: string) =>
  d === 'E' ? '#10b981' : d === 'H' ? '#ef4444' : '#f59e0b';

export const Practice = () => {
  const [subjects, setSubjects] = useState<SubjectProfile[]>([]);
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [topicId, setTopicId] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>('bank');

  // Bank state
  const [bank, setBank] = useState<PracticeQuestionItem[]>([]);
  const [generating, setGenerating] = useState(false);

  // Adaptive state
  const [session, setSession] = useState<AdaptiveSession | null>(null);
  const [currentQ, setCurrentQ] = useState<PracticeQuestionItem | null>(null);
  const [lastResult, setLastResult] = useState<PracticeAnswerResponse | null>(null);
  const [selected, setSelected] = useState<string>('');

  // Mistakes state
  const [mistakeQ, setMistakeQ] = useState<PracticeQuestionItem | null>(null);
  const [studentAnswer, setStudentAnswer] = useState('');
  const [analysis, setAnalysis] = useState<MistakeAnalysisResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSubjects = useCallback(async () => {
    try {
      const res = await endpoints.subjects.list();
      const confirmed = (res.items ?? []).filter((s) => s.status === 'confirmed');
      setSubjects(confirmed);
      if (confirmed.length && subjectId == null) setSubjectId(confirmed[0].id);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [subjectId]);

  useEffect(() => {
    void loadSubjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadTopics = useCallback(async (sid: number) => {
    try {
      const res = await endpoints.subjects.topics.list(sid);
      const confirmed = (res.items ?? []).filter((t) => t.status === 'confirmed');
      setTopics(confirmed);
      // Keep a deep-linked (or user-chosen) topic when it's still available;
      // otherwise fall back to the first confirmed topic.
      setTopicId((prev) => {
        if (prev != null && confirmed.some((t) => t.id === prev)) return prev;
        return confirmed.length ? confirmed[0].id : null;
      });
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    if (subjectId != null) void loadTopics(subjectId);
  }, [subjectId, loadTopics]);

  // Phase 8 (Idea 75): deep link from the Dashboard "Next up" card —
  // /practice?topic=<id> preselects the topic and opens the adaptive tab.
  useEffect(() => {
    const param = new URLSearchParams(window.location.search).get('topic');
    const tid = Number(param);
    if (param && Number.isInteger(tid) && tid > 0) {
      setTopicId(tid);
      setTab('adaptive');
    }
  }, []);

  const loadBank = useCallback(async (tid: number) => {
    try {
      const res = await endpoints.kb.practice.questions({ topic_id: tid });
      setBank(res.items ?? []);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    if (topicId != null && tab === 'bank') void loadBank(topicId);
  }, [topicId, tab, loadBank]);

  const generate = async () => {
    if (topicId == null) return;
    setGenerating(true);
    setError(null);
    try {
      await endpoints.kb.practice.generate({ topic_id: topicId, count: 5 });
      await loadBank(topicId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  const review = async (id: number, action: 'approve' | 'reject') => {
    try {
      if (action === 'approve') await endpoints.kb.practice.approve(id);
      else await endpoints.kb.practice.reject(id);
      if (topicId != null) await loadBank(topicId);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const startAdaptive = async () => {
    if (topicId == null) return;
    setBusy(true);
    setError(null);
    setLastResult(null);
    setSelected('');
    try {
      const res = await endpoints.kb.practice.session(topicId);
      setSession(res.session);
      setCurrentQ(res.question);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const checkAnswer = async (correct: boolean) => {
    if (topicId == null || session == null || currentQ == null) return;
    setBusy(true);
    setError(null);
    try {
      const res = await endpoints.kb.practice.answer({
        topic_id: topicId,
        tier: session.tier,
        correct,
      });
      setLastResult(res);
      setSession((s) => (s ? { ...s, tier: res.tier, streak: res.streak } : s));
      setCurrentQ(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const runMistakeAnalysis = async () => {
    if (!mistakeQ || !studentAnswer.trim()) return;
    setAnalyzing(true);
    setError(null);
    setAnalysis(null);
    try {
      const res = await endpoints.kb.practice.mistakeAnalysis({
        question_id: mistakeQ.id,
        student_answer: studentAnswer,
      });
      setAnalysis(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  const pending = bank.filter((q) => q.status !== 'approved');
  const approved = bank.filter((q) => q.status === 'approved');

  return (
    <div className="page-section">
      <Header title="Practice" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Generate a question bank from your topics, drill adaptively, and learn from every mistake.
      </p>

      {error && (
        <div style={{ padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '0.75rem', background: '#ef444422', color: '#ef4444', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Subject + topic pickers */}
      <div className="card" style={{ padding: '0.9rem', marginBottom: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
          Subject
          <select value={subjectId ?? ''} onChange={(e) => setSubjectId(Number(e.target.value) || null)} style={{ display: 'block', marginTop: '0.25rem', minWidth: 220 }}>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.parsed?.title ?? `Subject #${s.id}`}
              </option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
          Topic
          <select value={topicId ?? ''} onChange={(e) => setTopicId(Number(e.target.value) || null)} style={{ display: 'block', marginTop: '0.25rem', minWidth: 240 }}>
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Tabs */}
      <div style={{ display: 'inline-flex', borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border)', marginBottom: '1rem' }}>
        {(
          [
            ['bank', '🗂️ Question Bank'],
            ['adaptive', '🎯 Adaptive'],
            ['mistakes', '🩺 Mistakes'],
          ] as [Tab, string][]
        ).map(([t, label]) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            style={{
              padding: '0.45rem 1rem',
              fontSize: '0.8rem',
              border: 'none',
              cursor: 'pointer',
              background: tab === t ? 'var(--accent)' : 'transparent',
              color: tab === t ? '#fff' : 'var(--text-secondary)',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Question Bank ── */}
      {tab === 'bank' && (
        <>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => void generate()} disabled={generating || topicId == null}>
              {generating ? 'Generating…' : '＋ Generate 5 questions'}
            </button>
            {pending.length > 0 && <button type="button" className="btn btn-ghost btn-sm" onClick={() => topicId != null && void loadBank(topicId)}>↻ Refresh</button>}
          </div>

          {bank.length === 0 ? (
            <EmptyState icon="🗂️" title="No questions yet" message="Pick a topic and generate your first question set — each is grounded in the topic’s notes." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {bank.map((q) => (
                <div key={q.id} className="card" style={{ padding: '0.85rem 1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.62rem', fontWeight: 700, color: difficultyColor(q.difficulty), background: `${difficultyColor(q.difficulty)}1f`, borderRadius: 999, padding: '0.1rem 0.5rem' }}>
                      {q.difficulty}
                    </span>
                    <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{q.bloom_level}</span>
                    <span style={{ fontSize: '0.62rem', color: q.status === 'approved' ? '#10b981' : '#f59e0b', marginLeft: 'auto' }}>
                      {q.status === 'approved' ? '✓ approved' : '⏳ pending review'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.83rem', lineHeight: 1.45 }}>{q.question}</div>
                  {q.options.length > 0 && (
                    <div style={{ marginTop: '0.35rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                      {q.options.map((o, i) => (
                        <div key={i} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {String.fromCharCode(65 + i)}. {o}
                        </div>
                      ))}
                    </div>
                  )}
                  {q.status !== 'approved' && (
                    <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.5rem' }}>
                      <button type="button" className="btn btn-primary btn-sm" onClick={() => void review(q.id, 'approve')}>✓ Approve</button>
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void review(q.id, 'reject')}>✕ Reject</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Adaptive ── */}
      {tab === 'adaptive' && (
        <div className="card" style={{ padding: '1rem' }}>
          {session == null ? (
            <>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Adaptive practice picks the difficulty from your mastery and adjusts the tier as you answer — up on streaks, down on slips.
              </p>
              <button type="button" className="btn btn-primary" onClick={() => void startAdaptive()} disabled={busy || topicId == null}>
                {busy ? 'Starting…' : '▶ Start adaptive session'}
              </button>
            </>
          ) : currentQ ? (
            <div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.66rem', fontWeight: 700, color: difficultyColor(currentQ.difficulty), background: `${difficultyColor(currentQ.difficulty)}1f`, borderRadius: 999, padding: '0.12rem 0.55rem' }}>
                  Tier {session.tier}
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>🔥 streak {session.streak}</span>
                <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>{session.reason}</span>
              </div>
              <div style={{ fontSize: '0.88rem', lineHeight: 1.5, marginBottom: '0.75rem' }}>{currentQ.question}</div>
              {currentQ.options.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '0.75rem' }}>
                  {currentQ.options.map((o, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setSelected(o)}
                      style={{
                        textAlign: 'left',
                        fontSize: '0.8rem',
                        padding: '0.5rem 0.75rem',
                        borderRadius: 8,
                        border: `1px solid ${selected === o ? 'var(--accent)' : 'var(--border)'}`,
                        background: selected === o ? 'var(--accent-muted)' : 'var(--bg-hover)',
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                      }}
                    >
                      {String.fromCharCode(65 + i)}. {o}
                    </button>
                  ))}
                </div>
              )}
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button type="button" className="btn btn-primary" onClick={() => void checkAnswer(true)} disabled={busy}>
                  ✓ I got it right
                </button>
                <button type="button" className="btn btn-ghost" onClick={() => void checkAnswer(false)} disabled={busy}>
                  ✗ I got it wrong
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void startAdaptive()} disabled={busy} style={{ marginLeft: 'auto' }}>
                  ↻ New question
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Current tier</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 800, color: difficultyColor(session.tier) }}>{session.tier}</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>🔥 streak {session.streak}</span>
              </div>
              {lastResult && (
                <div
                  style={{
                    fontSize: '0.82rem',
                    marginBottom: '0.75rem',
                    padding: '0.6rem 0.85rem',
                    borderRadius: 8,
                    background: lastResult.tier_moved ? 'rgba(16,185,129,0.1)' : 'var(--bg-hover)',
                    border: `1px solid ${lastResult.tier_moved ? 'rgba(16,185,129,0.3)' : 'var(--border)'}`,
                  }}
                >
                  {lastResult.tier_moved
                    ? `🎉 Tier moved up! Accuracy at this tier: ${Math.round(lastResult.accuracy_at_tier * 100)}%`
                    : `Recorded — accuracy at this tier: ${Math.round(lastResult.accuracy_at_tier * 100)}%`}
                </div>
              )}
              <button type="button" className="btn btn-primary" onClick={() => void startAdaptive()} disabled={busy}>
                ▶ Next question
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Mistakes ── */}
      {tab === 'mistakes' && (
        <div className="card" style={{ padding: '1rem' }}>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
            Explain my mistake — paste your actual answer to a bank question and get a precise divergence analysis with revision tasks.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginBottom: '0.75rem' }}>
            <select
              value={mistakeQ?.id ?? ''}
              onChange={(e) => {
                const q = approved.find((x) => x.id === Number(e.target.value)) ?? null;
                setMistakeQ(q);
                setAnalysis(null);
              }}
              style={{ minWidth: 280 }}
            >
              <option value="">— choose an approved question —</option>
              {approved.map((q) => (
                <option key={q.id} value={q.id}>{q.question.slice(0, 80)}</option>
              ))}
            </select>
            <textarea
              value={studentAnswer}
              onChange={(e) => setStudentAnswer(e.target.value)}
              placeholder="Your answer to this question (as you wrote it)…"
              rows={3}
              style={{ fontSize: '0.82rem', resize: 'vertical' }}
            />
            <div>
              <button type="button" className="btn btn-primary" onClick={() => void runMistakeAnalysis()} disabled={analyzing || !mistakeQ || !studentAnswer.trim()}>
                {analyzing ? 'Analyzing…' : '🔍 Analyze my mistake'}
              </button>
            </div>
          </div>

          {analysis && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}>
              <div style={{ fontSize: '0.78rem', lineHeight: 1.5 }}>
                <strong style={{ color: 'var(--accent)' }}>Divergence: </strong>
                {analysis.divergence}
              </div>
              {analysis.missed_points.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Missed points</div>
                  <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                    {analysis.missed_points.map((m, i) => <li key={i}>{m}</li>)}
                  </ul>
                </div>
              )}
              {analysis.concept_definition && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', background: 'var(--bg-hover)', borderRadius: 8, padding: '0.5rem 0.7rem' }}>
                  <strong>Concept: </strong>
                  {analysis.concept_definition}
                </div>
              )}
              <div style={{ fontSize: '0.78rem', lineHeight: 1.45, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 8, padding: '0.55rem 0.7rem' }}>
                <strong style={{ color: '#f59e0b' }}>Recommendation: </strong>
                {analysis.recommendation}
              </div>
              {analysis.revision_task_created && (
                <div style={{ fontSize: '0.72rem', color: '#10b981' }}>✓ A revision task was added to your tasks.</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Practice;
