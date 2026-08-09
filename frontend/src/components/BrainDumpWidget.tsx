import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { brainDumpApi, endpoints, type KbSource } from '../services/api';

interface BrainDumpWidgetProps {
  className?: string;
}

/**
 * Phase 4 (Idea 40): the brain-dump textarea stays a dead-simple autosaving
 * widget, but every save also upserts a *draft* KbDocument on the backend.
 * When a draft exists we show an additive "File as note" card offering
 * title / source / tags plus AI section splitting for long dumps.
 */
export const BrainDumpWidget = ({ className = '' }: BrainDumpWidgetProps) => {
  const [content, setContent] = useState('');
  const [status, setStatus] = useState<'idle' | 'saving' | 'synced' | 'error'>('idle');
  const [linkedDocId, setLinkedDocId] = useState<number | null>(null);
  const [sources, setSources] = useState<KbSource[]>([]);
  const [fileTitle, setFileTitle] = useState('');
  const [fileTags, setFileTags] = useState('');
  const [fileSourceId, setFileSourceId] = useState<string>('');
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [filedId, setFiledId] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  const load = useCallback(async () => {
    try {
      const res = await brainDumpApi.get();
      if (isMountedRef.current) {
        setContent(res.content ?? '');
        setLinkedDocId(res.linked_document_id ?? null);
        setStatus('synced');
      }
    } catch {
      if (isMountedRef.current) setStatus('error');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Sources for the "file into a source" select — only needed once a draft exists.
  useEffect(() => {
    if (linkedDocId == null) return;
    endpoints.kb.sources
      .list()
      .then((r) => {
        if (isMountedRef.current) setSources(r.items);
      })
      .catch(() => {});
  }, [linkedDocId]);

  const debouncedSave = useCallback((value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setStatus('saving');
    timerRef.current = setTimeout(async () => {
      try {
        const res = await brainDumpApi.save(value);
        if (isMountedRef.current) {
          setStatus('synced');
          const nextLinked = res.linked_document_id ?? null;
          setLinkedDocId(nextLinked);
          // A *new* draft supersedes a previously filed note — reveal its filing
          // card again instead of keeping the stale "Filed ✓" banner.
          setFiledId((prev) => (prev != null && (nextLinked == null || nextLinked !== prev) ? null : prev));
        }
      } catch {
        if (isMountedRef.current) setStatus('error');
      }
    }, 700);
  }, []);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const val = e.target.value;
      setContent(val);
      debouncedSave(val);
    },
    [debouncedSave],
  );

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const flash = (msg: string) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(null), 3500);
  };

  const fileAsNote = async () => {
    if (linkedDocId == null) return;
    setBusy('file');
    try {
      const tags = fileTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const title = fileTitle.trim() || (content.split('\n')[0] || 'Brain dump').slice(0, 80);
      await endpoints.kb.documents.file(linkedDocId, {
        title,
        source_id: fileSourceId ? Number(fileSourceId) : null,
        tags,
      });
      setFiledId(linkedDocId);
      setNotice(null);
      flash('Filed as a note ✓');
    } catch (e) {
      flash(`File failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const splitSections = async () => {
    if (linkedDocId == null) return;
    setBusy('split');
    try {
      const res = await endpoints.kb.documents.split(linkedDocId);
      flash(
        res.sections_applied > 0
          ? `Split into ${res.sections_applied} section${res.sections_applied === 1 ? '' : 's'} ✓ — file it when ready`
          : 'No sections to split — add headings or more paragraphs.',
      );
      // Splitting does NOT file the doc — it stays a draft, so keep the filing card open.
    } catch (e) {
      flash(`Split failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const statusIcon = status === 'synced' ? '✅' : status === 'saving' ? '💾' : status === 'error' ? '⚠️' : '○';
  const statusLabel = status === 'synced' ? 'Synced' : status === 'saving' ? 'Saving…' : status === 'error' ? 'Error' : '';

  return (
    <div className={`card ${className}`.trim()}>
      <div className="card-header">
        <span>Brain Dump</span>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{statusIcon} {statusLabel}</span>
      </div>
      <textarea
        value={content}
        onChange={handleChange}
        placeholder="Dump your thoughts here…"
        rows={6}
        style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
        className="form-input"
      />

      {/* Phase 4 (Idea 40): draft → note filing card */}
      {filedId != null ? (
        <div style={{ marginTop: '0.6rem', padding: '0.6rem 0.75rem', borderRadius: 8, background: 'var(--success-muted)', color: 'var(--success)', fontSize: '0.78rem' }}>
          ✅ Filed as a note.
          <Link to={`/knowledge-base?doc=${filedId}`} style={{ marginLeft: '0.4rem', fontWeight: 700 }}>
            Open it →
          </Link>
        </div>
      ) : linkedDocId != null ? (
        <div style={{ marginTop: '0.6rem', padding: '0.7rem 0.8rem', borderRadius: 'var(--radius-lg)', border: '1px dashed var(--border)', background: 'var(--bg-primary)' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, marginBottom: '0.45rem', color: 'var(--text-secondary)' }}>
            📝 File as note{content.length > 600 ? ' · split long dumps into sections' : ''}
          </div>
          <input
            className="form-input"
            style={{ width: '100%', fontSize: '0.78rem', marginBottom: '0.35rem' }}
            placeholder="Note title (default: first line)"
            value={fileTitle}
            onChange={(e) => setFileTitle(e.target.value)}
          />
          <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
            <select
              className="form-input"
              style={{ flex: 1, minWidth: 140, fontSize: '0.78rem' }}
              value={fileSourceId}
              onChange={(e) => setFileSourceId(e.target.value)}
            >
              <option value="">No source (standalone)</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <input
              className="form-input"
              style={{ flex: 1, minWidth: 140, fontSize: '0.78rem' }}
              placeholder="tags, comma, separated"
              value={fileTags}
              onChange={(e) => setFileTags(e.target.value)}
            />
          </div>
          {notice && <div style={{ fontSize: '0.72rem', color: 'var(--accent)', marginBottom: '0.35rem' }}>{notice}</div>}
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              disabled={busy !== null}
              onClick={() => void fileAsNote()}
            >
              {busy === 'file' ? 'Filing…' : 'File as note'}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              disabled={busy !== null || content.length < 200}
              title={content.length < 200 ? 'Needs ~200+ characters to split' : 'AI-assisted section splitting'}
              onClick={() => void splitSections()}
            >
              {busy === 'split' ? 'Splitting…' : '✂️ Split sections'}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
};
