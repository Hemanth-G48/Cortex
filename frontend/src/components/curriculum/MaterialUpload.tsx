import { useEffect, useRef, useState, type DragEvent } from 'react';
import { endpoints, type Course } from '../../services/api';
import { useToast } from '../../hooks/useToast';

const ACCEPTED = ['pdf', 'docx', 'txt', 'md'];
const MAX_MB = 10;

interface MaterialUploadProps {
  unitId: number;
  /** Subject owning this unit — lets the uploader link a personal course (Phase 81). */
  subjectId?: number | null;
  onUploaded: () => void;
}

/** Drag-drop / click upload with client-side validation and progress (plan Phase 61). */
export const MaterialUpload = ({ unitId, subjectId, onUploaded }: MaterialUploadProps) => {
  const { toast } = useToast();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  // G12 (Phase 81): optional personal-course link for this unit's subject.
  const [courses, setCourses] = useState<Course[]>([]);
  const [linkCourseId, setLinkCourseId] = useState<number | ''>('');
  const [linking, setLinking] = useState(false);

  useEffect(() => {
    setCourses([]);
    setLinkCourseId('');
    if (!subjectId) return;
    endpoints.courses
      .list()
      .then((rows) => {
        setCourses(rows);
        // Auto-select the course already linked to this subject, if any.
        const linked = rows.find((c) => c.curriculum_subject_id === subjectId);
        if (linked) setLinkCourseId(linked.id);
      })
      .catch(() => undefined);
  }, [subjectId]);

  const linkCourse = async (courseId: number | '') => {
    if (!subjectId || linking) return;
    setLinking(true);
    try {
      if (courseId === '') {
        // Unlink the previously linked course (set FK to null).
        const prev = courses.find((c) => c.curriculum_subject_id === subjectId);
        if (prev) {
          await endpoints.courses.update(prev.id, {
            ...prev,
            curriculum_subject_id: null,
          });
          toast('Unlinked from course', 'success');
        }
        return;
      }
      const course = courses.find((c) => c.id === courseId);
      if (!course) return;
      await endpoints.courses.update(courseId, {
        ...course,
        curriculum_subject_id: subjectId,
      });
      toast('Linked to course', 'success');
    } catch {
      toast('Could not update course link', 'error');
      setLinkCourseId('');
    } finally {
      setLinking(false);
    }
  };

  const validate = (file: File): string | null => {
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!ACCEPTED.includes(ext)) return `Unsupported file type. Allowed: ${ACCEPTED.join(', ')}`;
    if (file.size > MAX_MB * 1024 * 1024) return `File too large (max ${MAX_MB} MB)`;
    return null;
  };

  const upload = async (file: File) => {
    const problem = validate(file);
    if (problem) {
      toast(problem, 'warning');
      return;
    }
    setUploading(true);
    setProgress(15);
    const tick = window.setInterval(() => {
      setProgress((p) => Math.min(90, p + 12));
    }, 250);
    try {
      await endpoints.materials.upload(unitId, file);
      setProgress(100);
      toast('Material uploaded', 'success');
      onUploaded();
    } catch (e) {
      toast(e instanceof Error ? e.message.replace('API ', '') : 'Upload failed', 'error');
    } finally {
      window.clearInterval(tick);
      setUploading(false);
      window.setTimeout(() => setProgress(0), 400);
    }
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void upload(file);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload a material file"
      onClick={() => !uploading && inputRef.current?.click()}
      onKeyDown={(e) => e.key === 'Enter' && !uploading && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => void onDrop(e)}
      className="material-dropzone"
      style={{
        border: `2px dashed ${dragging ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 'var(--radius)',
        padding: '1.25rem 1rem',
        textAlign: 'center',
        cursor: uploading ? 'default' : 'pointer',
        transition: 'border-color 0.2s ease, background 0.2s ease',
        background: dragging ? 'var(--accent-muted, rgba(59,130,246,0.08))' : 'var(--bg-hover)',
        display: 'grid',
        gap: '0.35rem',
        justifyContent: 'center',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.map((e) => `.${e}`).join(',')}
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void upload(file);
          e.target.value = '';
        }}
      />
      <div style={{ fontSize: '1.4rem' }} aria-hidden>📤</div>
      <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
        {uploading ? 'Uploading…' : 'Drop a file here or click to browse'}
      </div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
        PDF · DOCX · TXT · MD — up to {MAX_MB} MB
      </div>
      {uploading && (
        <div style={{ height: 6, borderRadius: 3, overflow: 'hidden', background: 'var(--bg-card)', marginTop: '0.5rem', minWidth: 200 }}>
          <div style={{ height: '100%', width: `${progress}%`, background: 'var(--accent)', borderRadius: 3, transition: 'width 0.25s ease' }} />
        </div>
      )}

      {subjectId && !uploading && courses.length > 0 && (
        <label
          style={{ display: 'grid', gap: '0.3rem', marginTop: '0.75rem', minWidth: 260, textAlign: 'left' }}
          onClick={(e) => e.stopPropagation()}
        >
          <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            🔗 Link to my course (optional)
          </span>
          <select
            aria-label="Link to my course (optional)"
            value={linkCourseId}
            disabled={linking}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : '';
              setLinkCourseId(id);
              void linkCourse(id);
            }}
          >
            <option value="">{linking ? 'Updating…' : '— None —'}</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>{c.title}{c.curriculum_subject_id === subjectId ? ' ✓' : ''}</option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
};
