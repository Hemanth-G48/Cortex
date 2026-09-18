import { useCallback, useEffect, useRef, useState } from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import {
  endpoints,
  kbSearchApi,
  type KbSearchResponse,
  type TutorChatResponse,
  type TutorSource,
  type TutorDoubtResponse,
} from '../services/api';

interface ChatTurn {
  kind: 'chat' | 'doubt';
  message: string;
  step?: string;
  response: TutorChatResponse | TutorDoubtResponse;
}

const SourceChips = ({ sources }: { sources: TutorSource[] }) => {
  if (!sources.length) return null;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.55rem' }}>
      <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', alignSelf: 'center' }}>
        Sources
      </span>
      {sources.map((s, i) => (
        <span
          key={`${s.chunk_id ?? 'doc'}-${i}`}
          title={s.snippet}
          style={{
            fontSize: '0.68rem',
            color: 'var(--text-secondary)',
            background: 'var(--bg-hover)',
            border: '1px solid var(--border)',
            borderRadius: 999,
            padding: '0.12rem 0.55rem',
            maxWidth: 220,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {s.title || s.source_path || `#${s.chunk_id ?? s.document_id ?? '?'}`}
        </span>
      ))}
    </div>
  );
};

const DoubtPanel = ({ response }: { response: TutorDoubtResponse }) => {
  const blocking = response.blocking_concepts ?? [];
  const followUps = response.follow_ups ?? [];
  return (
    <>
      {blocking.length > 0 && (
        <div style={{ marginTop: '0.7rem' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.35rem' }}>
            ⛔ Likely blocking concepts
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {blocking.map((b, i) => (
              <div
                key={i}
                style={{
                  fontSize: '0.78rem',
                  background: 'rgba(245,158,11,0.08)',
                  border: '1px solid rgba(245,158,11,0.25)',
                  borderRadius: 8,
                  padding: '0.45rem 0.65rem',
                }}
              >
                <strong style={{ color: '#f59e0b' }}>{b.concept}</strong>
                {b.topic_name && (
                  <span style={{ color: 'var(--text-muted)', marginLeft: '0.4rem' }}>· {b.topic_name}</span>
                )}
                {b.definition && (
                  <div style={{ color: 'var(--text-secondary)', marginTop: '0.2rem', fontSize: '0.72rem' }}>{b.definition}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {followUps.length > 0 && (
        <div style={{ marginTop: '0.7rem' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.35rem' }}>
            Suggested next steps
          </div>
          <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            {followUps.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
};

export const Tutor = () => {
  const [mode, setMode] = useState<'chat' | 'doubt'>('chat');
  const [message, setMessage] = useState('');
  const [step, setStep] = useState('');
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [sessionCount, setSessionCount] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Defect #64 fix: show the daily AI budget meter.
  const [budget, setBudget] = useState<{ today: number; limit: number; remaining: number } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  // Phase 8 (Idea 74, phrase 37): "you studied X" chips from user_memory.
  const [known, setKnown] = useState<{ concept: string; strength: number }[]>([]);

  const loadSessions = useCallback(async () => {
    try {
      const res = await endpoints.kb.tutor.sessions();
      setSessionCount(res.items?.length ?? 0);
    } catch {
      /* sidebar count is non-critical */
    }
  }, []);

  useEffect(() => {
    void loadSessions();
    endpoints.kb.memory
      .get(8)
      .then((r) => setKnown(r.items.filter((m) => m.strength > 0)))
      .catch(() => setKnown([]));
    // Defect #64 fix: daily AI budget meter.
    endpoints.ai.budget().then(setBudget).catch(() => setBudget(null));
  }, [loadSessions]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  const submit = async () => {
    const text = message.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === 'chat') {
        // Defect #89 fix: before sending to the tutor, retrieve the top KB
        // chunks for the user's query so the tutor can ground its answer in
        // the vault, not just the message text.
        let grounded = text;
        let sources: KbSearchResponse | null = null;
        try {
          sources = await kbSearchApi.query(text, 'hybrid', 1, 3);
          if (sources.items.length > 0) {
            const ctx = sources.items
              .map((i) => `[${i.title}](${i.source_path || ''})\n${i.snippet}`)
              .join('\n\n');
            grounded = `Context from your knowledge base:\n${ctx}\n\n---
User question: ${text}`;
          }
        } catch {
          /* KB search is non-critical — fall back to ungrounded chat */
        }
        const res = await endpoints.kb.tutor.chat({ message: grounded, session_id: sessionId });
        setSessionId(res.session_id);
        setTurns((t) => [...t, { kind: 'chat', message: text, response: res }]);
      } else {
        const res = await endpoints.kb.tutor.doubt({
          question: text,
          step_where_stuck: step.trim() || null,
        });
        setTurns((t) => [...t, { kind: 'doubt', message: text, step: step.trim(), response: res }]);
      }
      setMessage('');
      setStep('');
      void loadSessions();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page-section">
      <Header title="AI Tutor" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        RAG-grounded answers over your vault — every reply cites the notes it was built from.
        {sessionCount > 0 && ` ${sessionCount} past session${sessionCount === 1 ? '' : 's'}.`}
      </p>

      {/* Phase 8 (Idea 74): known-context chips — the tutor can reference
          these as prior knowledge (Rule A: nothing else is ever implied). */}
      {known.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', alignItems: 'center', marginBottom: '1rem' }}>
          <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            You've studied
          </span>
          {known.map((k) => (
            <span
              key={k.concept}
              title={`strength ${Math.round(k.strength * 100)}%`}
              style={{
                fontSize: '0.68rem',
                color: 'var(--success, #10b981)',
                background: 'rgba(16,185,129,0.1)',
                border: '1px solid rgba(16,185,129,0.25)',
                borderRadius: 999,
                padding: '0.12rem 0.55rem',
              }}
            >
              {k.concept}
            </span>
          ))}
        </div>
      )}

      {/* Mode toggle */}
      <div style={{ display: 'inline-flex', borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border)', marginBottom: '1rem' }}>
        {(['chat', 'doubt'] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            style={{
              padding: '0.45rem 1rem',
              fontSize: '0.8rem',
              border: 'none',
              cursor: 'pointer',
              background: mode === m ? 'var(--accent)' : 'transparent',
              color: mode === m ? '#fff' : 'var(--text-secondary)',
            }}
          >
            {m === 'chat' ? '💬 Ask anything' : '🧩 I’m stuck'}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '0.75rem', background: '#ef444422', color: '#ef4444', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Chat transcript */}
      <div className="card" style={{ padding: '1rem', marginBottom: '1rem', minHeight: 260, maxHeight: 520, overflowY: 'auto' }}>
        {turns.length === 0 ? (
          <EmptyState
            icon={mode === 'chat' ? '💬' : '🧩'}
            title={mode === 'chat' ? 'Ask your AI tutor' : 'Describe where you’re stuck'}
            message={
              mode === 'chat'
                ? 'Ask about any concept in your vault — answers cite the source notes.'
                : 'Tell us the question and the step where you got stuck — we’ll find the missing prerequisites.'
            }
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            {turns.map((t, i) => (
              <div key={i}>
                <div
                  style={{
                    alignSelf: 'flex-end',
                    background: 'var(--accent-muted)',
                    color: 'var(--text-primary)',
                    borderRadius: '14px 14px 4px 14px',
                    padding: '0.5rem 0.8rem',
                    fontSize: '0.82rem',
                    maxWidth: '85%',
                    marginLeft: 'auto',
                  }}
                >
                  {t.message}
                  {t.step && (
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                      stuck at: {t.step}
                    </div>
                  )}
                </div>
                <div
                  style={{
                    background: 'var(--bg-hover)',
                    border: '1px solid var(--border)',
                    borderRadius: '14px 14px 14px 4px',
                    padding: '0.6rem 0.85rem',
                    fontSize: '0.82rem',
                    lineHeight: 1.5,
                    color: 'var(--text-primary)',
                    marginTop: '0.4rem',
                  }}
                >
                  <div style={{ whiteSpace: 'pre-wrap' }}>{t.response.answer}</div>
                  {t.response.empty_retrieval && (
                    <div style={{ fontSize: '0.68rem', color: '#f59e0b', marginTop: '0.4rem' }}>
                      ⚠ No matching notes in your vault — this answer isn’t grounded. Add notes on this topic to improve it.
                    </div>
                  )}
                  {t.kind === 'doubt' && <DoubtPanel response={t.response as TutorDoubtResponse} />}
                  <SourceChips sources={t.response.sources} />
                  {t.response.ai_used ? (
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: '0.45rem' }}>✨ generated by AI</div>
                  ) : (
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: '0.45rem' }}>⚙️ offline deterministic mode</div>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="card" style={{ padding: '0.9rem' }}>
        {mode === 'doubt' && (
          <input
            value={step}
            onChange={(e) => setStep(e.target.value)}
            placeholder="Optional: the exact step where you got stuck…"
            style={{ width: '100%', marginBottom: '0.5rem' }}
          />
        )}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void submit();
              }
            }}
            placeholder={mode === 'chat' ? 'e.g. Explain linear regression and how gradient descent fits it…' : 'e.g. Why does maximum likelihood estimation fail on small samples?'}
            rows={2}
            style={{ flex: 1, resize: 'vertical', fontSize: '0.85rem' }}
          />
          <button type="button" className="btn btn-primary" onClick={() => void submit()} disabled={busy || !message.trim()} style={{ alignSelf: 'flex-end' }}>
            {busy ? 'Thinking…' : 'Send'}
          </button>
        </div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '0.4rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <span>Enter to send · Shift+Enter for a new line</span>
          {budget && (
            <span title="Provider-backed AI calls today (local fallback is free)">
              ⚡ Budget: {budget.remaining}/{budget.limit} left today
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default Tutor;
