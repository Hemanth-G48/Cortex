import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { endpoints, type SubjectProfile, type UserSkillItem } from '../services/api';

const levelColor = (level: number) => (level >= 4 ? '#10b981' : level >= 3 ? '#3b82f6' : level >= 2 ? '#f59e0b' : '#9aa0a6');
const levelLabel = (level: number) => ['None', 'Novice', 'Developing', 'Proficient', 'Advanced', 'Expert'][Math.min(5, Math.max(0, Math.round(level)))] ?? 'Novice';

export const Skills = () => {
  const [skills, setSkills] = useState<UserSkillItem[]>([]);
  const [subjects, setSubjects] = useState<SubjectProfile[]>([]);
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportText, setExportText] = useState('');
  const [exportFormat, setExportFormat] = useState<'markdown' | 'json'>('markdown');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [sk, subj] = await Promise.all([endpoints.kb.skills.profile(), endpoints.subjects.list()]);
      setSkills(sk.skills ?? []);
      const confirmed = (subj.items ?? []).filter((s) => s.status === 'confirmed');
      setSubjects(confirmed);
      if (confirmed.length && subjectId == null) setSubjectId(confirmed[0].curriculum_subject_id ?? confirmed[0].id);
    } catch (e) {
      setError((e as Error).message);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const mapSubject = async () => {
    if (subjectId == null) return;
    setBusy(true);
    setError(null);
    try {
      await endpoints.kb.skills.map(subjectId);
      const sk = await endpoints.kb.skills.profile();
      setSkills(sk.skills ?? []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const downloadExport = async (fmt: 'markdown' | 'json') => {
    setExportFormat(fmt);
    setBusy(true);
    setError(null);
    try {
      const res = await endpoints.kb.skills.export(fmt);
      setExportText(res.content);
      setExportOpen(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const saveFile = () => {
    const blob = new Blob([exportText], { type: exportFormat === 'json' ? 'application/json' : 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `skills-portfolio.${exportFormat === 'json' ? 'json' : 'md'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page-section">
      <Header title="Skill Profile" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Skills derived from your topics and mastery — interview scores and practice nudges keep the profile fresh.
      </p>

      {error && (
        <div style={{ padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '0.75rem', background: '#ef444422', color: '#ef4444', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="card" style={{ padding: '0.9rem 1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Map a confirmed subject’s topics → skills:</span>
        <select value={subjectId ?? ''} onChange={(e) => setSubjectId(Number(e.target.value) || null)} style={{ minWidth: 220 }}>
          {subjects.map((s) => (
            <option key={s.id} value={s.curriculum_subject_id ?? s.id}>
              {s.parsed?.title ?? `Subject #${s.id}`}
            </option>
          ))}
        </select>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => void mapSubject()} disabled={busy || subjectId == null}>
          {busy ? 'Mapping…' : '🗺 Map subject'}
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.4rem' }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void downloadExport('markdown')} disabled={busy}>
            ⬇ Markdown
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void downloadExport('json')} disabled={busy}>
            ⬇ JSON
          </button>
        </div>
      </div>

      {skills.length === 0 ? (
        <EmptyState icon="🛠️" title="No skills mapped yet" message="Map a confirmed subject to build your skill profile — or complete an interview to seed it." />
      ) : (
        <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}>
          {skills.map((s) => (
            <div key={s.skill_id} className="card" style={{ padding: '0.9rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 800, color: levelColor(s.level), background: `${levelColor(s.level)}1f`, borderRadius: 999, padding: '0.15rem 0.6rem' }}>
                  Lv {s.level}
                </span>
                <strong style={{ fontSize: '0.82rem', flex: 1 }}>{s.name}</strong>
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {levelLabel(s.level)}
              </div>
              <div style={{ height: 8, borderRadius: 4, background: 'var(--bg-hover)', overflow: 'hidden' }}>
                <div style={{ width: `${Math.round(s.mastery * 100)}%`, height: '100%', background: levelColor(s.level), transition: 'width 0.5s ease' }} />
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>{Math.round(s.mastery * 100)}% mastery</div>
              {s.contributing_topics.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                  {s.contributing_topics.slice(0, 5).map((t) => (
                    <span key={t.topic_id} style={{ fontSize: '0.62rem', color: 'var(--text-muted)', background: 'var(--bg-hover)', borderRadius: 999, padding: '0.1rem 0.45rem' }}>
                      {t.topic_name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Export preview modal */}
      {exportOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
            zIndex: 1000,
          }}
          onClick={() => setExportOpen(false)}
        >
          <div className="card" style={{ maxWidth: 640, width: '100%', maxHeight: '80vh', display: 'flex', flexDirection: 'column', padding: '1.1rem' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.6rem' }}>
              <strong style={{ flex: 1 }}>Skill portfolio ({exportFormat})</strong>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExportOpen(false)}>✕</button>
            </div>
            <pre
              style={{
                flex: 1,
                overflow: 'auto',
                fontSize: '0.72rem',
                lineHeight: 1.5,
                background: 'var(--bg-hover)',
                borderRadius: 8,
                padding: '0.75rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                margin: 0,
              }}
            >
              {exportText}
            </pre>
            <button type="button" className="btn btn-primary btn-sm" onClick={saveFile} style={{ marginTop: '0.6rem', alignSelf: 'flex-end' }}>
              ⬇ Download file
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Skills;
