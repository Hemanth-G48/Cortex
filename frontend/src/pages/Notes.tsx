import { useCallback, useEffect, useMemo, useState } from 'react';
import { Header } from '../components/layout/Header';
import { confirmDelete } from '../utils/confirm';
import { endpoints } from '../services/api';
import type { Course, Note } from '../services/api';

/** Tiny markdown-ish renderer (headings, bold, italics, inline code, lists). */
const renderMarkdown = (text: string) => {
  const lines = text.split('\n');
  const out: string[] = [];
  let inList = false;
  for (const raw of lines) {
    const line = raw.trimEnd();
    const escape = (s: string) =>
      s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code style="background:var(--bg-hover);padding:1px 4px;border-radius:4px;font-size:0.85em">$1</code>');
    if (/^#{1,3}\s/.test(line)) {
      if (inList) {
        out.push('</ul>');
        inList = false;
      }
      const level = line.match(/^(#+)/)![1].length;
      out.push(`<h${level} style="margin:0.75rem 0 0.35rem;font-size:${level === 1 ? 1.25 : level === 2 ? 1.1 : 0.95}rem">${escape(line.replace(/^#+\s/, ''))}</h${level}>`);
    } else if (/^\s*[-*]\s/.test(line)) {
      if (!inList) {
        out.push('<ul style="padding-left:1.25rem;margin:0.35rem 0">');
        inList = true;
      }
      out.push(`<li style="margin:0.2rem 0">${escape(line.replace(/^\s*[-*]\s/, ''))}</li>`);
    } else {
      if (inList) {
        out.push('</ul>');
        inList = false;
      }
      if (line.trim() === '') out.push('<div style="height:0.5rem"></div>');
      else out.push(`<p style="margin:0.25rem 0;line-height:1.6">${escape(line)}</p>`);
    }
  }
  if (inList) out.push('</ul>');
  return out.join('\n');
};

export const Notes = () => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [courseId, setCourseId] = useState(0);
  const [preview, setPreview] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  const selectNote = useCallback((n: Note) => {
    setSelectedId(n.id);
    setTitle(n.title);
    setContent(n.content ?? '');
    setCourseId(n.course_id);
    setDirty(false);
    setPreview(false);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [n, c] = await Promise.all([endpoints.notes.list(), endpoints.courses.list()]);
      setNotes(n);
      setCourses(c);
      if (selectedId === null && n.length > 0) {
        selectNote(n[0]);
      } else if (selectedId !== null && !n.some((x) => x.id === selectedId)) {
        setSelectedId(null);
        setTitle('');
        setContent('');
        setCourseId(0);
        setDirty(false);
      }
    } catch {
      /* silent */
    }
  }, [selectedId, selectNote]);

  useEffect(() => {
    void refresh();
    // Initial load only — refresh() captures the initial (null) selection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return notes.filter((n) => n.title.toLowerCase().includes(q) || (n.content ?? '').toLowerCase().includes(q));
  }, [notes, search]);

  const newNote = async () => {
    try {
      const created = await endpoints.notes.create({
        title: 'Untitled',
        content: '',
        course_id: courses[0]?.id ?? 0,
        created_date: new Date().toISOString().slice(0, 10),
        pinned: false,
      });
      await refresh();
      setSelectedId(created.id);
      selectNote(created);
    } catch {
      /* silent */
    }
  };

  const save = async () => {
    if (selectedId === null) return;
    setSaving(true);
    try {
      await endpoints.notes.update(selectedId, {
        title: title.trim() || 'Untitled',
        content,
        course_id: courseId,
        created_date: notes.find((n) => n.id === selectedId)?.created_date ?? new Date().toISOString().slice(0, 10),
      });
      setDirty(false);
      await refresh();
    } catch {
      /* silent */
    }
    setSaving(false);
  };

  const togglePin = async () => {
    if (selectedId === null) return;
    try {
      await endpoints.notes.pin(selectedId);
      await refresh();
    } catch {
      /* silent */
    }
  };

  const remove = async () => {
    if (selectedId === null) return;
    if (!confirmDelete('this note')) return;
    try {
      await endpoints.notes.delete(selectedId);
      setSelectedId(null);
      setTitle('');
      setContent('');
      await refresh();
    } catch {
      /* silent */
    }
  };

  const selected = notes.find((n) => n.id === selectedId) ?? null;

  return (
    <div className="fade-in">
      <Header title="Notes" />
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'stretch', minHeight: '60vh' }}>
        {/* ── List pane ── */}
        <div style={{ width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="🔍 Search notes…"
            style={{ width: '100%' }}
          />
          <button type="button" className="btn btn-primary" onClick={() => void newNote()} style={{ justifyContent: 'center' }}>
            ＋ New Note
          </button>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', overflowY: 'auto', flex: 1 }}>
            {filtered.length === 0 ? (
              <div className="empty-state" style={{ padding: '1rem' }}>
                <div className="empty-message">No notes found.</div>
              </div>
            ) : (
              filtered.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => selectNote(n)}
                  style={{
                    textAlign: 'left',
                    padding: '0.6rem 0.75rem',
                    borderRadius: 'var(--radius)',
                    border: `1px solid ${selectedId === n.id ? 'var(--accent)' : 'var(--border)'}`,
                    background: selectedId === n.id ? 'var(--accent-muted)' : 'var(--bg-card)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s, background 0.15s',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: '0.82rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {n.pinned ? '📌 ' : ''}{n.title}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {(n.content ?? '').slice(0, 60) || 'Empty note'}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* ── Editor pane ── */}
        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.75rem', minWidth: 0 }}>
          {selected === null ? (
            <div className="empty-state" style={{ flex: 1 }}>
              <div className="empty-icon">📓</div>
              <div className="empty-title">Select a note or create one</div>
              <div className="empty-message">Your notes open in a split-pane editor with markdown preview.</div>
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <input
                  value={title}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    setDirty(true);
                  }}
                  placeholder="Note title"
                  style={{ flex: 1, fontWeight: 600, minWidth: 180 }}
                />
                <select
                  value={courseId}
                  onChange={(e) => {
                    setCourseId(Number(e.target.value));
                    setDirty(true);
                  }}
                  style={{ width: 'auto' }}
                >
                  <option value={0}>— No course —</option>
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>{c.title}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', gap: '0.35rem' }}>
                  {(['edit', 'preview'] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      className="btn btn-ghost btn-sm"
                      style={preview === (m === 'preview') ? { color: 'var(--accent)', borderColor: 'var(--accent)' } : undefined}
                      onClick={() => setPreview(m === 'preview')}
                    >
                      {m === 'edit' ? '✏️ Edit' : '👁 Preview'}
                    </button>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => void togglePin()}>
                    {selected.pinned ? '📌 Pinned' : '📌 Pin'}
                  </button>
                  <button type="button" className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }} onClick={() => void remove()}>
                    🗑 Delete
                  </button>
                  <button type="button" className="btn btn-primary btn-sm" onClick={() => void save()} disabled={!dirty || saving}>
                    {saving ? 'Saving…' : dirty ? '💾 Save' : 'Saved ✓'}
                  </button>
                </div>
              </div>
              {preview ? (
                <div
                  style={{ flex: 1, overflowY: 'auto', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem', fontSize: '0.85rem' }}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
                />
              ) : (
                <textarea
                  value={content}
                  onChange={(e) => {
                    setContent(e.target.value);
                    setDirty(true);
                  }}
                  placeholder="Write your note… supports **bold**, *italic*, `code`, # headings and - lists"
                  style={{ flex: 1, resize: 'none', minHeight: 300 }}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
