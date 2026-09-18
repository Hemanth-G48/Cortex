import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { StudyPlan } from '../services/api';
import { exportStudyPlanToPDF } from '../utils/pdfExport';

export const StudyPlans = () => {
  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [form, setForm] = useState({ subject: '', examDate: '' });
  const [loading, setLoading] = useState(false);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [aiMode, setAiMode] = useState('Offline');
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const p = await endpoints.studyPlans.list();
      setPlans(p);
      setActiveId((cur) => cur ?? p[0]?.id ?? null);
    } catch {
      /* silent */
    }
    // Defect #72: prefer the plan the vault's focus board recommends. The board
    // reports readiness per curriculum subject, so the recommended subject's
    // name is resolved via the mastery read model and matched to a saved plan.
    try {
      const board = await endpoints.kb.focus.board();
      const top = board.recommendations[0];
      if (!top) return;
      const mastery = await endpoints.kb.mastery({ subject: top.subject_id });
      const name = mastery.subject_name?.trim().toLowerCase();
      if (!name) return;
      const recommended = (await endpoints.studyPlans.list()).find(
        (plan) =>
          plan.subject.trim().toLowerCase() === name ||
          plan.subject.trim().toLowerCase().includes(name),
      );
      if (recommended) setActiveId(recommended.id);
    } catch {
      /* the focus board is advisory — keep the user's selection */
    }
  }, []);

  useEffect(() => {
    void refresh();
    endpoints.ai
      .health()
      .then((h) => setAiMode(h.available && h.model ? `AI · ${h.model}` : 'Offline'))
      .catch(() => setAiMode('Offline'));
  }, [refresh]);

  const generate = async () => {
    if (!form.subject.trim() || loading) return;
    setLoading(true);
    setError('');
    try {
      const res = await endpoints.ai.studyPlan(form.subject.trim(), form.examDate || undefined);
      const plan = res.plan;
      const saved = await endpoints.studyPlans.create({
        subject: plan.subject,
        exam_date: plan.exam_date,
        weeks: plan.weeks,
      });
      await refresh();
      setActiveId(saved.id);
      setForm({ subject: '', examDate: '' });
    } catch {
      setError('Generation failed — please try again.');
    }
    setLoading(false);
  };

  const handleDelete = async (id: number) => {
    try {
      await endpoints.studyPlans.delete(id);
      await refresh();
    } catch {
      /* silent */
    }
  };

  const active = plans.find((p) => p.id === activeId) ?? plans[0] ?? null;
  const canGenerate = !loading && form.subject.trim().length > 0;

  return (
    <div className="fade-in" style={{ maxWidth: 820 }}>
      <Header title="Study Plans" />

      {/* Generator */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h2 className="widget-title" style={{ marginBottom: '0.75rem' }}>✨ Generate AI Study Plan</h2>
        {aiMode === 'Offline' && (
          <div
            style={{
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'flex-start',
              background: 'var(--warning-muted)',
              border: '1px solid var(--warning)',
              borderRadius: 10,
              padding: '0.6rem 0.85rem',
              fontSize: '0.75rem',
              color: 'var(--warning)',
              marginBottom: '0.85rem',
            }}
          >
            <span>⚠️</span> AI is offline — a sample plan will be generated.
          </div>
        )}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <input
            value={form.subject}
            onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
            placeholder="Subject or topic (e.g. Calculus Final)"
            onKeyDown={(e) => e.key === 'Enter' && void generate()}
            style={{ flex: 2, minWidth: 200 }}
          />
          <input
            type="date"
            value={form.examDate}
            onChange={(e) => setForm((f) => ({ ...f, examDate: e.target.value }))}
            style={{ flex: 1, minWidth: 140 }}
          />
          <button type="button" className="btn btn-primary" onClick={() => void generate()} disabled={!canGenerate}>
            {loading ? 'Generating…' : '✨ Generate'}
          </button>
        </div>
        {error && <p style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.5rem' }}>{error}</p>}
      </div>

      {/* Saved plan chips */}
      {plans.length > 0 && (
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
          {plans.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setActiveId(p.id)}
              className="btn btn-sm"
              style={activeId === p.id ? { color: 'var(--info)', borderColor: 'var(--info)', background: 'var(--info-muted)' } : undefined}
            >
              {p.subject}
            </button>
          ))}
        </div>
      )}

      {/* Active plan */}
      {active ? (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              {active.subject}
              {active.exam_date ? <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>exam {active.exam_date}</span> : null}
            </h2>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => exportStudyPlanToPDF(active.subject, active.exam_date, active.weeks)}>
                📄 Export PDF
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => void handleDelete(active.id)}>
                🗑 Delete
              </button>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {active.weeks.map((w) => (
              <div key={w.week} className="card" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <span
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 10,
                      background: 'var(--info)',
                      color: '#0b0e14',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: '0.8rem',
                      flexShrink: 0,
                      boxShadow: '0 4px 12px var(--info-muted)',
                    }}
                  >
                    W{w.week}
                  </span>
                  <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{w.topic}</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {w.tasks.map((t, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--info)', flexShrink: 0 }} />
                      {t}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="card empty-state">
          <div className="empty-icon">📚</div>
          <div className="empty-title">No study plans yet</div>
          <div className="empty-message">Type a subject above and let AI build you a week-by-week plan.</div>
        </div>
      )}
    </div>
  );
};
