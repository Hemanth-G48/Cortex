import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { AISyllabusAssignment, Course, SubjectProfile } from '../services/api';

const priColor = (p: string) =>
  p === 'high' ? 'var(--danger)' : p === 'medium' ? 'var(--warning)' : 'var(--success)';

const statusColor: Record<string, string> = {
  proposed: 'var(--warning)',
  confirmed: 'var(--success)',
  rejected: 'var(--danger)',
};

/** Phase 5 (Idea 41–42): syllabus → parsed proposal → human review → confirm. */
export const SyllabusImport = () => {
  const [text, setText] = useState('');
  const [mode, setMode] = useState<'subject' | 'assignments'>('subject');
  const [loading, setLoading] = useState(false);
  const [drag, setDrag] = useState(false);
  const [fileError, setFileError] = useState('');

  // Phase 5 proposal state
  const [profile, setProfile] = useState<SubjectProfile | null>(null);
  const [reviewName, setReviewName] = useState('');
  const [reviewCode, setReviewCode] = useState('');
  const [reviewCredits, setReviewCredits] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState('');
  // Defect #74: pending vault links proposed after the subject is confirmed.
  const [linkedCount, setLinkedCount] = useState<number | null>(null);

  // Legacy assignment-extraction state
  const [extracted, setExtracted] = useState<AISyllabusAssignment[]>([]);
  const [imported, setImported] = useState(false);
  const [courses, setCourses] = useState<Course[]>([]);

  const fileRef = useRef<HTMLInputElement>(null);

  const resetProposal = () => {
    setProfile(null);
    setReviewName('');
    setReviewCode('');
    setReviewCredits('');
    setConfirmError('');
  };

  const extract = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    setFileError('');
    try {
      const res = await endpoints.subjects.import({ text });
      setProfile(res.profile);
      setReviewName(res.profile.parsed?.title ?? '');
      setReviewCredits(res.profile.parsed?.credits ? String(res.profile.parsed.credits) : '');
    } catch (e) {
      setFileError(e instanceof Error ? e.message : 'Parsing failed — please try again.');
    }
    setLoading(false);
  };

  const handleFile = (file: File | null) => {
    if (!file) return;
    setFileError('');
    if (file.size > 10 * 1024 * 1024) {
      setFileError('File too large (max 10 MB).');
      return;
    }
    setLoading(true);
    endpoints.subjects
      .importFile(file)
      .then((res) => {
        setProfile(res.profile);
        setReviewName(res.profile.parsed?.title ?? file.name.replace(/\.[^.]+$/, ''));
        setReviewCredits(res.profile.parsed?.credits ? String(res.profile.parsed.credits) : '');
      })
      .catch((e) => setFileError(e instanceof Error ? e.message : 'Could not parse that file.'))
      .finally(() => setLoading(false));
  };

  const confirmProposal = async () => {
    if (!profile || confirming) return;
    setConfirming(true);
    setConfirmError('');
    try {
      const raw = reviewCredits.trim();
      const parsed = Number(raw);
      // Backend credits is an int field — coerce floats (e.g. "3.5") to whole numbers.
      const credits = raw === '' || !Number.isFinite(parsed) ? null : Math.round(parsed);
      const res = await endpoints.subjects.confirm(profile.id, {
        name: reviewName.trim() || undefined,
        code: reviewCode.trim() || undefined,
        credits,
      });
      setProfile(res.profile);
      // Defect #74: straight after confirming, match the extracted topics
      // against the vault (POST /api/kb/links/auto) and surface how many links
      // are awaiting review. Best-effort — confirmation already succeeded.
      endpoints.kb.links
        .auto()
        .then((r) => setLinkedCount(r.queue.length))
        .catch(() => setLinkedCount(null));
    } catch (e) {
      setConfirmError(e instanceof Error ? e.message : 'Could not confirm the subject.');
    }
    setConfirming(false);
  };

  const rejectProposal = async () => {
    if (!profile) return;
    try {
      const res = await endpoints.subjects.reject(profile.id);
      setProfile(res.profile);
    } catch (e) {
      setConfirmError(e instanceof Error ? e.message : 'Could not reject the subject.');
    }
  };

  // ----- Legacy assignments-only flow (kept for existing users) -----
  const loadCourses = () => {
    endpoints.courses.list().then(setCourses).catch(() => {});
  };

  const extractAssignments = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    try {
      const res = await endpoints.ai.syllabus(text);
      setExtracted(res.assignments);
      loadCourses();
    } catch {
      setExtracted([]);
    }
    setLoading(false);
  };

  const importAll = async () => {
    if (extracted.length === 0) return;
    const courseByName = new Map(courses.map((c) => [c.title.toLowerCase(), c]));
    try {
      const existing = await endpoints.assignments.list();
      const existingTitles = new Set(existing.map((a) => a.title.toLowerCase()));
      let added = 0;
      for (const a of extracted) {
        if (existingTitles.has(a.title.toLowerCase())) continue;
        const course = courseByName.get((a.course || '').toLowerCase());
        await endpoints.assignments.create({
          title: a.title,
          due_date: a.due_date || new Date().toISOString().slice(0, 10),
          course_id: course?.id ?? courses[0]?.id ?? 0,
          status: 'Not started',
        });
        existingTitles.add(a.title.toLowerCase());
        added += 1;
      }
      setImported(true);
      window.setTimeout(() => setImported(false), 3000);
      if (added === 0) setFileError('Nothing new to import — all already exist.');
    } catch {
      setFileError('Import failed — please try again.');
    }
  };

  const canExtract = !loading && text.trim().length > 0;

  return (
    <div className="fade-in" style={{ maxWidth: 820 }}>
      <Header title="Import Syllabus" />

      {/* Mode switch */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
        <button
          type="button"
          className="btn btn-sm"
          style={mode === 'subject' ? { background: 'var(--accent)', color: '#0b0e14', border: 'none' } : {}}
          onClick={() => { setMode('subject'); resetProposal(); }}
        >
          📘 Build Subject (Phase 5)
        </button>
        <button
          type="button"
          className="btn btn-sm"
          style={mode === 'assignments' ? { background: 'var(--accent)', color: '#0b0e14', border: 'none' } : {}}
          onClick={() => setMode('assignments')}
        >
          📝 Extract Assignments (legacy)
        </button>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFile(e.dataTransfer.files?.[0] ?? null);
        }}
        onClick={() => fileRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && fileRef.current?.click()}
        style={{
          border: `2px dashed ${drag ? 'var(--info)' : 'var(--border)'}`,
          borderRadius: 16,
          padding: '2.25rem 1.5rem',
          textAlign: 'center',
          cursor: 'pointer',
          marginBottom: '1rem',
          transition: 'border-color 0.2s ease, background 0.2s ease',
          background: drag ? 'var(--info-muted)' : 'transparent',
        }}
      >
        <div style={{ fontSize: '2rem', marginBottom: '0.6rem' }}>📄</div>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.25rem' }}>Drop syllabus file here</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>or click to browse · PDF, DOCX, TXT, MD</div>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          style={{ display: 'none' }}
        />
      </div>

      <div style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>— or paste text —</div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste your syllabus text here..."
        rows={6}
        style={{ width: '100%', resize: 'vertical', marginBottom: '1rem' }}
      />

      {fileError && <p style={{ fontSize: '0.75rem', color: 'var(--danger)', marginBottom: '0.75rem' }}>{fileError}</p>}

      <button
        type="button"
        className="btn btn-primary"
        onClick={() => void (mode === 'subject' ? extract() : extractAssignments())}
        disabled={!canExtract}
        style={{ width: '100%', padding: '0.8rem', marginBottom: '1.5rem' }}
      >
        {loading ? 'Parsing…' : mode === 'subject' ? '✨ Parse Syllabus into a Subject' : '✨ Extract Assignments'}
      </button>

      {/* Phase 5: proposal preview + review step */}
      {profile && mode === 'subject' && (
        <div className="fade-in">
          <div className="card" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '0.9rem' }}>
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>
                {profile.parsed?.title || reviewName || 'Untitled Subject'}
              </div>
              <span
                className="badge"
                style={{
                  color: statusColor[profile.status] ?? 'var(--text-secondary)',
                  background: `${statusColor[profile.status] ?? 'var(--text-secondary)'}22`,
                  textTransform: 'capitalize',
                }}
              >
                {profile.status}
              </span>
            </div>

            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.9rem' }}>
              {profile.semester && <span className="badge" style={{ color: 'var(--info)' }}>🗓 {profile.semester}</span>}
              {profile.parsed?.credits != null && <span className="badge">{profile.parsed.credits} credits</span>}
              <span className="badge">{profile.parsed?.units.length ?? 0} units</span>
            </div>

            {profile.status === 'proposed' && (
              <>
                {/* Review form (phrase 9) */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                  <label style={{ fontSize: '0.75rem' }}>
                    <span style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Name</span>
                    <input value={reviewName} onChange={(e) => setReviewName(e.target.value)} style={{ width: '100%' }} />
                  </label>
                  <label style={{ fontSize: '0.75rem' }}>
                    <span style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Code</span>
                    <input value={reviewCode} onChange={(e) => setReviewCode(e.target.value)} placeholder="e.g. CS101" style={{ width: '100%' }} />
                  </label>
                  <label style={{ fontSize: '0.75rem' }}>
                    <span style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Credits</span>
                    <input
                      value={reviewCredits}
                      onChange={(e) => setReviewCredits(e.target.value)}
                      type="number"
                      min={0}
                      max={30}
                      style={{ width: '100%' }}
                    />
                  </label>
                </div>

                {confirmError && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--danger)', marginBottom: '0.75rem' }}>{confirmError}</p>
                )}

                <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={confirming || !reviewName.trim()}
                    onClick={() => void confirmProposal()}
                  >
                    {confirming ? 'Confirming…' : '✅ Confirm & Create Subject'}
                  </button>
                  <button type="button" className="btn btn-sm" onClick={() => void rejectProposal()} disabled={confirming}>
                    Reject
                  </button>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={resetProposal}>
                    Discard
                  </button>
                </div>
              </>
            )}

            {profile.status === 'confirmed' && (
              <>
                {/* Defect #74: the auto-link pass ran against the vault. */}
                {linkedCount !== null && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                    🔗 {linkedCount} vault link{linkedCount === 1 ? '' : 's'} proposed from this syllabus —
                    review them in the Knowledge Base.
                  </p>
                )}
                <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <Link className="btn btn-primary btn-sm" to={`/subjects/profiles/${profile.id}`}>
                    Open Subject Workspace →
                  </Link>
                  <Link className="btn btn-sm" to="/subjects">
                    View All Subjects
                  </Link>
                </div>
              </>
            )}

            {profile.status === 'rejected' && (
              <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-sm" onClick={resetProposal}>
                  ↻ Try a different syllabus
                </button>
                <Link className="btn btn-ghost btn-sm" to="/subjects">
                  View All Subjects
                </Link>
              </div>
            )}
          </div>

          {/* Parsed syllabus preview (phrase 20) */}
          <div className="page-section">
            <h2>Parsed Syllabus</h2>
            {(profile.parsed?.units ?? []).length === 0 ? (
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No units detected in this syllabus.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {profile.parsed?.units.map((unit, i) => (
                  <div key={i} className="card" style={{ padding: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.6rem' }}>
                      <span className="badge" style={{ background: 'var(--bg-hover)' }}>Unit {i + 1}</span>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{unit.title}</span>
                    </div>
                    {unit.description && (
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>{unit.description}</p>
                    )}
                    {unit.topics.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                        {unit.topics.map((t, j) => (
                          <span key={j} className="badge" style={{ color: 'var(--accent)', background: 'var(--accent)14' }}>
                            {t.name}
                          </span>
                        ))}
                      </div>
                    )}
                    {unit.deadlines.length > 0 && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                        ⏰ {unit.deadlines.join(' · ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Legacy assignment results */}
      {extracted.length > 0 && mode === 'assignments' && (
        <div className="fade-in">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.9rem', gap: '0.6rem', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 700 }}>Found {extracted.length} assignments</h2>
            <button type="button" className="btn" style={{ background: 'var(--success)', color: '#0b0e14' }} onClick={() => void importAll()}>
              {imported ? '✅ Imported!' : '＋ Add All to Assignments'}
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {extracted.map((a, i) => (
              <div key={i} className="card" style={{ padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{a.title}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                    {a.course} · Due {a.due_date}
                  </div>
                </div>
                <span className="badge" style={{ color: priColor(a.priority), background: `${priColor(a.priority)}22`, textTransform: 'capitalize' }}>
                  {a.priority}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SyllabusImport;
