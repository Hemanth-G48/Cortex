import { useRef, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { AISyllabusAssignment, Course } from '../services/api';

const priColor = (p: string) =>
  p === 'high' ? 'var(--danger)' : p === 'medium' ? 'var(--warning)' : 'var(--success)';

export const SyllabusImport = () => {
  const [text, setText] = useState('');
  const [extracted, setExtracted] = useState<AISyllabusAssignment[]>([]);
  const [loading, setLoading] = useState(false);
  const [drag, setDrag] = useState(false);
  const [imported, setImported] = useState(false);
  const [courses, setCourses] = useState<Course[]>([]);
  const [fileError, setFileError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const loadCourses = () => {
    endpoints.courses.list().then(setCourses).catch(() => {});
  };

  const extract = async () => {
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

  const handleFile = (file: File | null) => {
    if (!file) return;
    setFileError('');
    if (file.size > 2 * 1024 * 1024) {
      setFileError('File too large (max 2 MB) — paste the text instead.');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => setText(String(e.target?.result ?? ''));
    reader.onerror = () => setFileError('Could not read that file — paste the text instead.');
    reader.readAsText(file);
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
    <div className="fade-in" style={{ maxWidth: 720 }}>
      <Header title="Import Syllabus" />

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
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>or click to browse · PDF, TXT, DOCX</div>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.docx"
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

      <button type="button" className="btn btn-primary" onClick={() => void extract()} disabled={!canExtract} style={{ width: '100%', padding: '0.8rem', marginBottom: '1.5rem' }}>
        {loading ? 'Extracting…' : '✨ Extract Assignments'}
      </button>

      {extracted.length > 0 && (
        <div className="fade-in">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.9rem', gap: '0.6rem', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 700 }}>Found {extracted.length} assignments</h2>
            <button
              type="button"
              className="btn"
              style={
                imported
                  ? { background: 'var(--success)', color: '#0b0e14' }
                  : { background: 'var(--success)', color: '#0b0e14' }
              }
              onClick={() => void importAll()}
            >
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
