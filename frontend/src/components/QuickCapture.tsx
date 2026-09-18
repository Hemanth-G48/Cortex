import { useEffect, useRef, useState } from 'react';
import { endpoints } from '../services/api';
import type { Course } from '../services/api';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const PRIORITY_COLORS: Record<string, string> = {
  high: 'var(--danger, #ff4d6a)',
  medium: 'var(--warning, #ffd6a0)',
  low: 'var(--success, #4dff91)',
};

const PRIORITY_STATUS: Record<string, string> = {
  high: 'Not started',
  medium: 'Not started',
  low: 'Not started',
};

export const QuickCapture = ({ open, onOpenChange }: Props) => {
  const [title, setTitle] = useState('');
  const [courseId, setCourseId] = useState<number | ''>('');
  const [dueDate, setDueDate] = useState('');
  const [priority, setPriority] = useState('medium');
  const [courses, setCourses] = useState<Course[]>([]);
  // Defect #53: assignment-name suggestions come from the real curriculum
  // (enrollment summary) + the vault's auto-detected subjects.
  const [subjects, setSubjects] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endpoints.courses.list().then(setCourses).catch(() => {});
    endpoints.enrollment
      .summary()
      .then((s) => setSubjects(s.subjects.map((sub) => sub.name)))
      .catch(() => {});
    endpoints.kb.autoSubjects
      .preview()
      .then((p) =>
        setSubjects((cur) => [...new Set([...cur, ...p.top_subjects.map(([name]) => name)])]),
      )
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 80);
      return () => clearTimeout(t);
    }
  }, [open]);

  const handleSubmit = async () => {
    if (!title.trim() || saving) return;
    setSaving(true);
    try {
      await endpoints.assignments.create({
        title: title.trim(),
        ...(courseId === '' ? {} : { course_id: courseId }),
        due_date: dueDate || new Date().toISOString().slice(0, 10),
        status: PRIORITY_STATUS[priority],
      });
      setSaved(true);
      setTimeout(() => {
        setTitle('');
        setCourseId('');
        setDueDate('');
        setPriority('medium');
        setSaved(false);
        setSaving(false);
        onOpenChange(false);
      }, 800);
    } catch {
      setSaving(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
    if (e.key === 'Escape') onOpenChange(false);
  };

  return (
    <>
      <button
        className="fab"
        onClick={() => onOpenChange(!open)}
        title="Quick capture (Ctrl+Shift+A)"
        aria-label="Quick capture"
      >
        <span className="fab-icon" style={{ transform: open ? 'rotate(45deg)' : 'none' }}>
          +
        </span>
      </button>

      {open && (
        <div className="quick-capture">
          <div className="quick-capture-header">
            <span>⚡ QUICK CAPTURE</span>
            <span className="muted">Ctrl+Shift+A</span>
          </div>

          <input
            ref={inputRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Assignment name…"
            list="quick-capture-subjects"
          />
          {/* Defect #53: curriculum + vault-detected subject suggestions. */}
          <datalist id="quick-capture-subjects">
            {subjects.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>

          <div className="quick-capture-row">
            <select value={courseId} onChange={(e) => setCourseId(e.target.value ? Number(e.target.value) : '')}>
              <option value="">Course…</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
            <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </div>

          <div className="quick-capture-priorities">
            {['high', 'medium', 'low'].map((p) => (
              <button
                key={p}
                onClick={() => setPriority(p)}
                className={priority === p ? 'active' : ''}
                style={{ borderColor: priority === p ? PRIORITY_COLORS[p] : undefined, color: priority === p ? PRIORITY_COLORS[p] : undefined }}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>

          <button className="quick-capture-submit" onClick={() => void handleSubmit()} disabled={!title.trim() || saving}>
            {saved ? '✓ SAVED!' : `+ ADD ASSIGNMENT${saving ? '…' : ''}`}
          </button>
        </div>
      )}
    </>
  );
};
