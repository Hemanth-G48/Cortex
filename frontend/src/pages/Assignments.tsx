import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Assignment, Course } from '../services/api';
import { exportAssignmentsToICal } from '../utils/icalExport';
import { exportAssignmentsToPDF } from '../utils/pdfExport';

type Tab = 'current' | 'course' | 'type' | 'completed';

const TABS: { key: Tab; label: string }[] = [
  { key: 'current', label: 'Current' },
  { key: 'course', label: 'By Course' },
  { key: 'type', label: 'By Type' },
  { key: 'completed', label: 'Completed' },
];

const TYPE_COLORS: Record<string, string> = {
  Homework: 'var(--info)',
  Quiz: 'var(--warning)',
  Project: 'var(--success)',
  Test: 'var(--danger)',
  Other: 'var(--text-secondary)',
};

export const Assignments = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [tab, setTab] = useState<Tab>('current');
  const [courseFilter, setCourseFilter] = useState<string>('');
  const fileRef = useRef<HTMLInputElement>(null);
  const [attachId, setAttachId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await endpoints.assignments.list();
      setAssignments(data);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    void refresh();
    endpoints.courses.list().then(setCourses).catch(() => {});
  }, [refresh]);

  const courseName = useCallback((cid: number) => courses.find((c) => c.id === cid)?.title ?? '—', [courses]);

  const filtered = useMemo(() => {
    const visible =
      tab === 'completed'
        ? assignments.filter((a) => a.status === 'Completed')
        : tab === 'current'
          ? assignments.filter((a) => a.status !== 'Completed')
          : assignments;
    if (courseFilter) return visible.filter((a) => String(a.course_id) === courseFilter);
    return visible;
  }, [assignments, tab, courseFilter]);

  const grouped = useMemo(() => {
    if (tab === 'course') {
      const map = new Map<string, Assignment[]>();
      for (const a of filtered) {
        const key = courseName(a.course_id);
        map.set(key, [...(map.get(key) ?? []), a]);
      }
      return Array.from(map.entries());
    }
    if (tab === 'type') {
      const map = new Map<string, Assignment[]>();
      for (const a of filtered) {
        const key = a.type ?? 'Other';
        map.set(key, [...(map.get(key) ?? []), a]);
      }
      return Array.from(map.entries());
    }
    return null;
  }, [filtered, tab, courseName]);

  const setStatus = async (id: number, status: string) => {
    try {
      await endpoints.assignments.setStatus(id, status);
      await refresh();
    } catch {
      /* silent */
    }
  };

  const handleComplete = async (id: number) => {
    try {
      await endpoints.assignments.complete(id);
      await refresh();
    } catch {
      /* silent */
    }
  };

  const handleAttach = async (id: number, file: File) => {
    try {
      await endpoints.assignments.attach(id, file);
      await refresh();
    } finally {
      setAttachId(null);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleICal = () => {
    exportAssignmentsToICal(
      assignments.map((a) => ({
        id: a.id,
        title: a.title,
        description: a.description,
        courseName: courseName(a.course_id),
        due_date: a.due_date,
        status: a.status,
      })),
    );
  };

  const handlePDF = () => {
    exportAssignmentsToPDF(
      assignments.map((a) => ({
        title: a.title,
        courseName: courseName(a.course_id),
        due_date: a.due_date,
        status: a.status,
      })),
    );
  };

  const statusBadge = (a: Assignment) => {
    const cls =
      a.status === 'Completed'
        ? 'badge badge-success'
        : a.status === 'In progress'
          ? 'badge badge-warning'
          : 'badge badge-info';
    return <span className={cls}>{a.status}</span>;
  };

  const typeTag = (a: Assignment) => (
    <span
      className="badge"
      style={{
        background: TYPE_COLORS[a.type ?? 'Other'] ?? 'var(--text-secondary)',
        color: '#fff',
        marginRight: '0.4rem',
      }}
    >
      {a.type ?? 'Other'}
    </span>
  );

  const actionCell = (a: Assignment) => {
    if (a.status === 'Completed') {
      return (
        <button className="btn btn-ghost btn-sm" onClick={() => setStatus(a.id, 'In progress')}>
          Reopen
        </button>
      );
    }
    return (
      <button className="btn btn-success btn-sm" onClick={() => handleComplete(a.id)}>
        Complete
      </button>
    );
  };

  const attachmentCell = (a: Assignment) => (
    <span>
      {a.file_url && (
        <a className="btn btn-ghost btn-sm" href={a.file_url} target="_blank" rel="noreferrer">
          ⬇
        </a>
      )}
      <input
        ref={fileRef}
        type="file"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void handleAttach(a.id, f);
        }}
      />
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => {
          setAttachId(a.id);
          fileRef.current?.click();
        }}
      >
        📎
      </button>
      {attachId === a.id && <span className="text-muted"> uploading…</span>}
    </span>
  );

  const renderRow = (a: Assignment) => (
    <tr key={a.id}>
      <td>
        {typeTag(a)}
        {a.title}
      </td>
      <td style={{ color: 'var(--text-secondary)' }}>{courseName(a.course_id)}</td>
      <td style={{ fontSize: '0.8rem' }}>{a.due_date}</td>
      <td>{statusBadge(a)}</td>
      <td>{actionCell(a)}</td>
      <td>{attachmentCell(a)}</td>
    </tr>
  );

  return (
    <div>
      <Header title="Assignments" />
      <div className="page-section">
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-ghost btn-sm" onClick={handleICal}>
            <span className="emoji">📅</span> Export iCal
          </button>
          <button className="btn btn-ghost btn-sm" onClick={handlePDF}>
            <span className="emoji">📄</span> Export PDF
          </button>
          <select className="form-input" value={courseFilter} onChange={(e) => setCourseFilter(e.target.value)} style={{ marginLeft: 'auto' }}>
            <option value="">All courses</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        </div>
        <div className="tabs" role="tablist" aria-label="Assignment views">
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              className={`tab${tab === t.key ? ' active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <div className="card">
        {filtered.length === 0 ? (
          <p className="empty-text">No assignments in this view.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Course</th>
                <th>Due</th>
                <th>Status</th>
                <th>Action</th>
                <th>File</th>
              </tr>
            </thead>
            <tbody>
              {grouped
                ? grouped.map(([group, items]) => (
                    <>
                      <tr key={group} className="group-row">
                        <td colSpan={6}>
                          <strong>{group}</strong> <span className="text-muted">({items.length})</span>
                        </td>
                      </tr>
                      {items.map(renderRow)}
                    </>
                  ))
                : filtered.map(renderRow)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
