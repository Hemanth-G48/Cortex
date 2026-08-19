import { useCallback, useEffect, useState } from 'react';
import { endpoints, type KbAgentRun, type KbForecast, type KbMemoryTimeline, type KbObservabilityPayload, type KbRecommendationItem, type KbReflection } from '../../services/api';

type Tab = 'agents' | 'recommend' | 'memory' | 'reflect' | 'forecast' | 'observe';

const DOMAIN_META: Record<string, { icon: string; color: string }> = {
  study: { icon: '📚', color: '#2563eb' },
  revisit: { icon: '🔁', color: '#7c3aed' },
  read: { icon: '📄', color: '#0d9488' },
  practice: { icon: '✏️', color: '#d97706' },
};

const TABS: { id: Tab; label: string }[] = [
  { id: 'agents', label: '🤖 Agents' },
  { id: 'recommend', label: '✨ Recommend' },
  { id: 'memory', label: '🧠 Memory' },
  { id: 'reflect', label: '🪞 Reflect' },
  { id: 'forecast', label: '📈 Forecast' },
  { id: 'observe', label: '📊 Observability' },
];

const fmt = (n: number | null | undefined, digits = 1) =>
  n == null ? '—' : n.toLocaleString(undefined, { maximumFractionDigits: digits });

export const Phase10Panel = ({ onFlash }: { onFlash?: (msg: string) => void }) => {
  const [tab, setTab] = useState<Tab>('recommend');

  return (
    <div className="card" style={{ padding: '1rem', marginTop: '1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <h3 style={{ fontSize: '0.95rem', margin: 0 }}>🚀 Phase 10 — Advanced AI & Analytics</h3>
        <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>
          Orchestrated agents · long-term memory · RAG hardening · forecasting · observability
        </span>
      </div>
      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '0.85rem' }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`btn btn-sm ${tab === t.id ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'agents' && <AgentsTab onFlash={onFlash} />}
      {tab === 'recommend' && <RecommendTab onFlash={onFlash} />}
      {tab === 'memory' && <MemoryTab />}
      {tab === 'reflect' && <ReflectTab onFlash={onFlash} />}
      {tab === 'forecast' && <ForecastTab />}
      {tab === 'observe' && <ObserveTab />}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Idea 91 — agents                                                    */
/* ------------------------------------------------------------------ */
function AgentsTab({ onFlash }: { onFlash?: (msg: string) => void }) {
  const [request, setRequest] = useState('');
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState<KbAgentRun | null>(null);
  const [history, setHistory] = useState<KbAgentRun[]>([]);

  const load = useCallback(async () => {
    try {
      const res = await endpoints.kb.agents.runs();
      setHistory(res.items ?? []);
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runAgents = async () => {
    if (!request.trim() || busy) return;
    setBusy(true);
    try {
      const res = await endpoints.kb.agents.run(request.trim());
      setRun(res);
      onFlash?.(`Agent run #${res.run_id ?? res.id} → ${res.status}`);
      await load();
    } catch (e) {
      onFlash?.(`Agent run failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const example = "prepare me for Thursday's exam using my weakest topics";

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.5rem' }}>
        <input
          className="form-input"
          style={{ flex: 1, fontSize: '0.78rem' }}
          placeholder={`e.g. ${example}`}
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void runAgents()}
        />
        <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={() => void runAgents()}>
          {busy ? 'Orchestrating…' : '▶ Run'}
        </button>
      </div>

      {run && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <Chip label={run.status ?? 'done'} color={run.status === 'failed' ? '#ef4444' : '#10b981'} />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
              {fmt(run.latency_ms, 0)} ms · ${fmt(run.cost_estimate, 5)}
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
            {(run.plan ?? []).map((p, i) => (
              <span key={i} style={{ fontSize: '0.68rem', background: '#2563eb1a', color: '#2563eb', padding: '0.15rem 0.5rem', borderRadius: 999 }}>
                {i + 1}. {p.agent}
              </span>
            ))}
          </div>
          {run.result && (
            <pre
              style={{
                whiteSpace: 'pre-wrap', fontSize: '0.74rem', lineHeight: 1.5,
                background: '#0f172a', color: '#e2e8f0', padding: '0.75rem', borderRadius: 8,
                maxHeight: 320, overflow: 'auto',
              }}
            >
              {run.result}
            </pre>
          )}
        </div>
      )}

      {history.length > 0 && (
        <div>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
            RECENT RUNS
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            {history.slice(0, 5).map((r) => (
              <button
                key={r.id ?? r.run_id}
                type="button"
                className="btn btn-sm btn-ghost"
                style={{ justifyContent: 'flex-start', textAlign: 'left' }}
                onClick={() => setRun(r)}
              >
                #{r.id ?? r.run_id} · {r.request} — {r.status}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Idea 97 — recommendations                                           */
/* ------------------------------------------------------------------ */
function RecommendTab({ onFlash }: { onFlash?: (msg: string) => void }) {
  const [items, setItems] = useState<KbRecommendationItem[]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const res = await endpoints.kb.recommendations.list(10);
      setItems(res.items ?? []);
    } catch {
      setItems([]);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const feedback = async (item: KbRecommendationItem, action: 'accept' | 'skip') => {
    try {
      await endpoints.kb.recommendations.feedback(item.id, action);
      onFlash?.(`${action === 'accept' ? 'Accepted' : 'Skipped'} “${item.title}” ✓`);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    } catch (e) {
      onFlash?.(`Feedback failed: ${(e as Error).message}`);
    }
  };

  if (busy && items.length === 0) return <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Loading recommendations…</p>;
  if (items.length === 0)
    return (
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
        No recommendations yet — add topics (Phase 5) and study activity to unlock a cross-domain feed.
      </p>
    );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
      {items.map((item) => {
        const meta = DOMAIN_META[item.domain] ?? { icon: '✨', color: '#6b7280' };
        return (
          <div key={item.id} className="card" style={{ padding: '0.6rem 0.8rem', display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '1rem' }}>{meta.icon}</span>
            <div style={{ flex: 1, minWidth: 160 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600 }}>{item.title}</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>{item.reason}</div>
            </div>
            <span style={{ fontSize: '0.66rem', fontWeight: 700, color: meta.color, background: `${meta.color}1a`, padding: '0.1rem 0.45rem', borderRadius: 999, textTransform: 'uppercase' }}>
              {item.domain} · {fmt(item.score, 2)}
            </span>
            <div style={{ display: 'flex', gap: '0.3rem' }}>
              <button type="button" className="btn btn-sm btn-primary" onClick={() => void feedback(item, 'accept')}>✓ Accept</button>
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => void feedback(item, 'skip')}>✕</button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Idea 92 — memory timeline                                           */
/* ------------------------------------------------------------------ */
function MemoryTab() {
  const [timeline, setTimeline] = useState<KbMemoryTimeline | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setTimeline(await endpoints.kb.memory.timeline(50));
    } catch {
      setTimeline(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const consolidate = async () => {
    setBusy(true);
    try {
      const res = await endpoints.kb.memory.consolidate();
      alert(`Consolidated ${res.episodes} episode(s) → ${res.facts} durable fact(s).`);
      await load();
    } catch (e) {
      alert(`Consolidation failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
          {timeline ? `${timeline.durable_facts.length} durable fact(s) · ${timeline.total} episodes` : '…'}
        </span>
        <button type="button" className="btn btn-sm btn-ghost" disabled={busy} onClick={() => void consolidate()}>
          {busy ? 'Consolidating…' : '🧹 Run weekly consolidation'}
        </button>
      </div>
      {timeline?.durable_facts && timeline.durable_facts.length > 0 && (
        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
          {timeline.durable_facts.map((f) => (
            <span key={f.concept} style={{ fontSize: '0.68rem', background: '#10b98122', color: '#047857', padding: '0.15rem 0.5rem', borderRadius: 999 }}>
              {f.concept} · {fmt(f.strength)}
            </span>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', maxHeight: 300, overflowY: 'auto' }}>
        {(timeline?.episodes ?? []).map((e) => (
          <div key={e.id} style={{ fontSize: '0.72rem', borderLeft: '3px solid #7c3aed', paddingLeft: '0.6rem' }}>
            <span style={{ fontWeight: 700 }}>{e.event_type}</span>
            <span style={{ color: 'var(--text-secondary)' }}> — {e.summary}</span>
          </div>
        ))}
        {timeline && timeline.episodes.length === 0 && (
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>No episodes yet — study activity journals itself here.</p>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Idea 98 — reflection + goals                                        */
/* ------------------------------------------------------------------ */
function ReflectTab({ onFlash }: { onFlash?: (msg: string) => void }) {
  const [reflection, setReflection] = useState<KbReflection | null>(null);
  const [goals, setGoals] = useState<{ id: number; title: string; progress_percentage: number; subject_id: number | null }[]>([]);
  const [derived, setDerived] = useState<{ subject_id: number; title: string; quarter: string; year: number; target_date: string }[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [r, g, d] = await Promise.all([
        endpoints.kb.reflections.list().catch(() => ({ items: [] as KbReflection[] })),
        endpoints.kb.reflections.goals().catch(() => ({ items: [] })),
        endpoints.kb.reflections.derivedGoals().catch(() => ({ items: [] })),
      ]);
      setReflection(r.items[0] ?? null);
      setGoals(g.items ?? []);
      setDerived(d.items ?? []);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const generate = async () => {
    setBusy('reflect');
    try {
      const r = await endpoints.kb.reflections.generate();
      setReflection(r);
      onFlash?.(r.pushed ? 'Weekly reflection generated + notified ✓' : 'Reflection ready (already notified)');
    } catch (e) {
      onFlash?.(`Reflection failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const adjust = async () => {
    setBusy('adjust');
    try {
      const res = await endpoints.kb.reflections.adjust();
      onFlash?.(`Plan adjustments applied: ${res.count}`);
    } catch (e) {
      onFlash?.(`Adjust failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const confirmGoal = async (d: typeof derived[number]) => {
    setBusy(`goal-${d.subject_id}`);
    try {
      await endpoints.kb.reflections.confirmGoal(d);
      onFlash?.(`Goal “${d.title}” created ✓`);
      await load();
    } catch (e) {
      onFlash?.(`Goal failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-sm btn-primary" disabled={busy != null} onClick={() => void generate()}>
          {busy === 'reflect' ? 'Generating…' : '🪞 Generate weekly reflection'}
        </button>
        <button type="button" className="btn btn-sm btn-ghost" disabled={busy != null} onClick={() => void adjust()}>
          {busy === 'adjust' ? 'Adapting…' : '🔄 Apply plan adjustments'}
        </button>
      </div>

      {reflection && (
        <pre
          style={{
            whiteSpace: 'pre-wrap', fontSize: '0.74rem', lineHeight: 1.5,
            background: '#0f172a', color: '#e2e8f0', padding: '0.75rem', borderRadius: 8,
            maxHeight: 240, overflow: 'auto',
          }}
        >
          {reflection.content}
        </pre>
      )}

      {derived.length > 0 && (
        <div>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
            PROPOSED GOALS (REVIEW)
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            {derived.map((d) => (
              <div key={d.subject_id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
                <span style={{ flex: 1 }}>🎯 {d.title} ({d.quarter} {d.year})</span>
                <button type="button" className="btn btn-sm btn-primary" disabled={busy != null} onClick={() => void confirmGoal(d)}>
                  {busy === `goal-${d.subject_id}` ? '…' : 'Confirm'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {goals.length > 0 && (
        <div>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>GOALS</div>
          {goals.map((g) => (
            <div key={g.id} style={{ fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ flex: 1 }}>{g.title}</span>
              <div style={{ width: 120, height: 6, borderRadius: 3, background: 'var(--muted, #e5e7eb)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${g.progress_percentage}%`, background: '#2563eb' }} />
              </div>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>{fmt(g.progress_percentage, 0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Idea 99 — forecast                                                  */
/* ------------------------------------------------------------------ */
function ForecastTab() {
  const [subjects, setSubjects] = useState<{ id: number; name: string }[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [forecast, setForecast] = useState<KbForecast | null>(null);
  const [scanning, setScanning] = useState(false);

  const loadSubjects = useCallback(async () => {
    try {
      const res = await endpoints.subjects.list();
      const items = (res.items ?? []).filter((p) => p.curriculum_subject_id);
      setSubjects(items.map((p) => ({ id: p.curriculum_subject_id as number, name: p.parsed?.title ?? `Subject ${p.curriculum_subject_id}` })));
      if (items[0]) setSelected(items[0].curriculum_subject_id as number);
    } catch {
      setSubjects([]);
    }
  }, []);

  useEffect(() => {
    void loadSubjects();
  }, [loadSubjects]);

  useEffect(() => {
    if (selected == null) return;
    endpoints.kb.forecast
      .get(selected)
      .then(setForecast)
      .catch(() => setForecast(null));
  }, [selected]);

  const scan = async () => {
    setScanning(true);
    try {
      const res = await endpoints.kb.forecast.scan();
      alert(`Forecast scan — ${res.processed} subject(s), ${res.at_risk} at risk, ${res.alerted} alert(s) fired.`);
    } catch (e) {
      alert(`Scan failed: ${(e as Error).message}`);
    } finally {
      setScanning(false);
    }
  };

  const maxVal = Math.max(0.1, ...(forecast?.points ?? []).map((p) => p.value), forecast?.forecast ?? 0);

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap' }}>
        <select className="form-input" style={{ maxWidth: 240, fontSize: '0.75rem' }} value={selected ?? ''} onChange={(e) => setSelected(Number(e.target.value))}>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <button type="button" className="btn btn-sm btn-ghost" disabled={scanning} onClick={() => void scan()}>
          {scanning ? 'Scanning…' : '🚨 Run at-risk scan'}
        </button>
      </div>

      {forecast && (
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '0.6rem' }}>
          <span style={{ fontSize: '0.78rem' }}>
            Readiness <strong>{fmt(forecast.readiness * 100, 0)}%</strong> · forecast {fmt(forecast.forecast, 2)}
          </span>
          {forecast.exam_days_until != null && (
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>exam in {forecast.exam_days_until} day(s)</span>
          )}
          <Chip
            label={forecast.at_risk ? 'AT RISK' : 'on track'}
            color={forecast.at_risk ? '#ef4444' : '#10b981'}
          />
        </div>
      )}

      {forecast && forecast.points.length > 0 ? (
        <svg viewBox="0 0 320 90" style={{ width: '100%', maxWidth: 420, height: 90, background: '#0f172a', borderRadius: 8 }}>
          {forecast.points.map((p, i) => {
            const x = 16 + (i / Math.max(1, forecast.points.length - 1)) * 288;
            const y = 78 - (p.value / maxVal) * 62;
            return <circle key={p.date} cx={x} cy={y} r={2.5} fill="#38bdf8" />;
          })}
          {forecast.points.length > 1 &&
            forecast.points.slice(1).map((p, i) => {
              const prev = forecast.points[i];
              const x1 = 16 + (i / Math.max(1, forecast.points.length - 1)) * 288;
              const y1 = 78 - (prev.value / maxVal) * 62;
              const x2 = 16 + ((i + 1) / Math.max(1, forecast.points.length - 1)) * 288;
              const y2 = 78 - (p.value / maxVal) * 62;
              return <line key={`l-${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#38bdf8" strokeWidth={1.5} />;
            })}
          <line x1={16} y1={78 - (forecast.forecast / maxVal) * 62} x2={304} y2={78 - (forecast.forecast / maxVal) * 62} stroke={forecast.at_risk ? '#ef4444' : '#10b981'} strokeWidth={1.5} strokeDasharray="4 3" />
          <text x={16} y={86} fill="#94a3b8" fontSize={8}>forecast</text>
        </svg>
      ) : (
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          No trajectory yet — log study sessions and quiz attempts to build one.
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Idea 100 — observability                                            */
/* ------------------------------------------------------------------ */
function ObserveTab() {
  const [payload, setPayload] = useState<KbObservabilityPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    endpoints.kb.observability
      .dashboard()
      .then(setPayload)
      .catch((e) => setError((e as Error).message));
  }, []);

  if (error) return <p style={{ fontSize: '0.75rem', color: '#ef4444' }}>Could not load observability — {error}</p>;
  if (!payload) return <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Loading dashboard…</p>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))' }}>
        <Stat label="Interactions" value={String(payload.total)} />
        <Stat label="Est. cost" value={`$${fmt(payload.cost_estimate, 5)}`} />
        <Stat label="p95 latency" value={`${fmt(payload.p95_latency_ms, 0)} ms`} />
        <Stat label="Thumbs ↑↓" value={`${payload.feedback.positive} / ${payload.feedback.negative}`} />
        <Stat label="Faithfulness" value={payload.avg_faithfulness == null ? '—' : `${fmt(payload.avg_faithfulness * 100, 0)}%`} />
        <Stat label="Tokens" value={String(payload.tokens)} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        {Object.entries(payload.by_feature ?? {}).map(([feature, f]) => (
          <div key={feature} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.72rem' }}>
            <span style={{ width: 90 }}>{feature}</span>
            <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--muted, #e5e7eb)', overflow: 'hidden' }}>
              <div style={{ width: `${Math.min(100, (f.count / payload.total) * 100)}%`, height: '100%', background: '#2563eb' }} />
            </div>
            <span style={{ color: 'var(--text-secondary)' }}>{f.count} · {fmt(f.avg_latency_ms, 0)}ms · fb {fmt(f.feedback)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card" style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
      <div style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>{label}</div>
      <div style={{ fontSize: '1rem', fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function Chip({ label, color }: { label: string; color: string }) {
  return (
    <span
      style={{
        fontSize: '0.66rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em',
        color, background: `${color}1a`, padding: '0.12rem 0.5rem', borderRadius: 999, whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}
