import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { SkeletonCard } from '../components/shared/Skeleton';
import { PDFReader } from '../components/reading/PDFReader';
import {
  bookApi,
  bookGapApi,
} from '../services/api';
import type {
  BookGapAnalysis,
  BookGapChapter,
  BookGapItem,
  BookGapOverview,
  BookGapStatus,
  BookGapTopic,
} from '../services/api';

type DetailTab = 'topics' | 'gaps' | 'chapters';

// Matches the backend BOOK_MAX_UPLOAD_MB default (configurable via env).
const BOOK_MAX_MB = 100;

const STATUS_META: Record<BookGapStatus, { icon: string; label: string; badge: string }> = {
  KNOWN: { icon: '✓', label: 'Already know', badge: 'badge-success' },
  PARTIALLY_KNOWN: { icon: '◐', label: 'Partially known', badge: 'badge-warning' },
  UNKNOWN: { icon: '✗', label: 'Not in your Second Brain', badge: 'badge-danger' },
  NEEDS_REVIEW: { icon: '?', label: 'Needs review', badge: 'badge-info' },
};

const LEVEL_LABEL: Record<number, string> = { 1: 'Chapter', 2: 'Section', 3: 'Subsection' };

function statusOf(topic: BookGapTopic | BookGapItem): BookGapStatus {
  return topic.status;
}

/* ─────────────────────────── small building blocks ─────────────────────────── */

function KnowledgeDots({ level }: { level: number }) {
  return (
    <span className="bgp-dots" title={`Knowledge level ${level}/5`} aria-label={`Knowledge level ${level}/5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`bgp-dot${i <= level ? ' on' : ''}`} />
      ))}
      <span className="bgp-dots-label">{level}/5</span>
    </span>
  );
}

function StatTile({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color?: string }) {
  return (
    <div className="stat-tile">
      <div className="label">{label}</div>
      <div className="value" style={color ? { color } : undefined}>{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

function DeepResultPanel({
  topic,
  onReAnalyze,
  onOpenPage,
  busy,
}: {
  topic: BookGapTopic;
  onReAnalyze: (topic: BookGapTopic) => void;
  onOpenPage: (page: number) => void;
  busy: boolean;
}) {
  const deep = topic.deep_result;
  if (topic.deep_status === 'ANALYZING') {
    return <p className="bgp-deep-hint">⏳ Analyzing this topic against your Second Brain…</p>;
  }
  if (topic.deep_status === 'FAILED') {
    return (
      <div className="bgp-deep-result bgp-deep-failed">
        <p>⚠ Deep analysis failed{deep?.error ? `: ${deep.error}` : ''}. </p>
        <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onReAnalyze(topic)}>
          ↻ Retry
        </button>
      </div>
    );
  }
  if (topic.deep_status !== 'ANALYZED' || !deep) return null;

  const missing = deep.missing ?? [];
  const covered = deep.covered ?? [];
  return (
    <div className="bgp-deep-result">
      {deep.summary && <p className="bgp-why">{deep.summary}</p>}
      {covered.length > 0 && (
        <div style={{ marginBottom: '0.6rem' }}>
          <span className="bgp-deep-label">Already covered in your Second Brain</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.3rem' }}>
            {covered.map((c) => (
              <span key={c} className="badge badge-success">✓ {c}</span>
            ))}
          </div>
        </div>
      )}
      {missing.length > 0 && (
        <div>
          <span className="bgp-deep-label">Missing from your Second Brain</span>
          <ul className="bgp-deep-missing">
            {missing.map((m, idx) => (
              <li key={`${m.concept}-${idx}`}>
                <span className="bgp-deep-missing-name">❌ {m.concept}</span>
                {m.why && <span className="bgp-deep-missing-why"> — {m.why}</span>}
                {m.deterministic && <span className="badge badge-info" style={{ marginLeft: '0.4rem' }}>heading check</span>}
              </li>
            ))}
          </ul>
          <p className="bgp-deep-hint" style={{ marginTop: '0.5rem' }}>
            Open the pages to review — gaps are only added to your Second Brain when you add them.
          </p>
        </div>
      )}
      <div style={{ marginTop: '0.6rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {topic.page_start != null && (
          <button type="button" className="btn btn-primary btn-sm" onClick={() => onOpenPage(topic.page_start!)}>
            📄 Read in Book (p. {topic.page_start})
          </button>
        )}
        <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onReAnalyze(topic)}>
          ↻ Re-analyze
        </button>
      </div>
    </div>
  );
}

function TopicRow({
  topic,
  onAnalyze,
  onAddToBrain,
  onOpenPage,
  busyAnalyze,
  busyAdd,
  added,
}: {
  topic: BookGapTopic;
  onAnalyze: (topic: BookGapTopic) => void;
  onAddToBrain: (topic: BookGapTopic) => void;
  onOpenPage: (page: number) => void;
  busyAnalyze: boolean;
  busyAdd: boolean;
  added: boolean;
}) {
  const meta = STATUS_META[statusOf(topic)];
  const isGap = topic.status === 'UNKNOWN' || topic.status === 'NEEDS_REVIEW';
  return (
    <div className={`card bgp-topic bgp-topic-${statusOf(topic).toLowerCase()}`} style={{ marginLeft: `${(topic.level - 1) * 1.25}rem` }}>
      <div className="bgp-topic-head">
        <span className={`bgp-status-icon ${statusOf(topic).toLowerCase()}`}>{meta.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="bgp-topic-title">
            {topic.title}
            <span className="badge" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
              {LEVEL_LABEL[topic.level] ?? 'Topic'}
            </span>
          </div>
          <div className="bgp-topic-meta">
            <span className="badge" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>{meta.label}</span>
            {topic.second_brain_match && (
              <span className="badge badge-success">Second Brain → {topic.second_brain_match}</span>
            )}
            {topic.page_start != null && (
              <span className="badge" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>
                pp. {topic.page_start}–{topic.page_end ?? topic.page_start}
              </span>
            )}
          </div>
        </div>
        <div className="bgp-topic-actions">
          {isGap ? (
            <button type="button" className="btn btn-primary btn-sm" disabled={busyAdd || added} onClick={() => onAddToBrain(topic)}>
              {added ? '✓ Added to Second Brain' : busyAdd ? '⏳ Adding…' : '+ Add to Second Brain'}
            </button>
          ) : (
            <button type="button" className="btn btn-primary btn-sm" disabled={busyAnalyze} onClick={() => onAnalyze(topic)}>
              {topic.deep_status === 'ANALYZED' ? '↻ Re-analyze Knowledge Gap' : busyAnalyze ? '⏳ Analyzing…' : 'Analyze Knowledge Gap'}
            </button>
          )}
          {topic.deep_status === 'ANALYZED' && topic.deep_result && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => onOpenPage(topic.page_start ?? 1)}>
              📄 Read in Book
            </button>
          )}
        </div>
      </div>
      <DeepResultPanel topic={topic} onReAnalyze={onAnalyze} onOpenPage={onOpenPage} busy={busyAnalyze} />
    </div>
  );
}

function GapItemCard({
  item,
  onOpen,
  onSetStatus,
  busy,
}: {
  item: BookGapItem;
  onOpen: (item: BookGapItem) => void;
  onSetStatus: (item: BookGapItem, s: 'learning' | 'learned' | 'mastered') => void;
  busy: boolean;
}) {
  const pages =
    item.page_start != null && item.page_end != null
      ? item.page_start === item.page_end
        ? `p. ${item.page_start}`
        : `pp. ${item.page_start}–${item.page_end}`
      : 'pages n/a';

  return (
    <div className={`card bgp-item`}>
      <div className="bgp-item-head">
        <span className="bgp-status-icon unknown">✗</span>
        <div className="bgp-item-title">
          <button type="button" className="bgp-item-name" onClick={() => onOpen(item)}>
            {item.display_name}
          </button>
          <div className="bgp-item-meta">
            <span className="badge badge-danger">Missing from Second Brain</span>
            <span className="badge" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>{pages}</span>
            {item.chapter && (
              <span className="badge" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>{item.chapter}</span>
            )}
          </div>
        </div>
        <div className="bgp-item-side">
          <KnowledgeDots level={item.knowledge_level} />
          <div className="bgp-est">{item.est_minutes} min</div>
        </div>
      </div>
      {item.why && <p className="bgp-why">{item.why}</p>}
      <div className="bgp-item-actions">
        {item.page_start != null && (
          <button type="button" className="btn btn-primary btn-sm" onClick={() => onOpen(item)}>
            📄 Read in Book
          </button>
        )}
        {item.my_status === 'LEARNED' || item.my_status === 'MASTERED' ? (
          <span className={`badge ${item.my_status === 'MASTERED' ? 'badge-info' : 'badge-success'}`}>
            {item.my_status === 'MASTERED' ? '★ Mastered' : '✓ Learned'}
          </span>
        ) : (
          <>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={busy || item.my_status === 'LEARNING'}
              onClick={() => onSetStatus(item, 'learning')}
            >
              {item.my_status === 'LEARNING' ? '… Learning' : 'Learn'}
            </button>
            <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onSetStatus(item, 'learned')}>
              Mark Learned
            </button>
            <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onSetStatus(item, 'mastered')}>
              Mastered
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────── page ─────────────────────────────────── */

export const BookGapReader = () => {
  const { bookId } = useParams();
  const navigate = useNavigate();

  const [overview, setOverview] = useState<BookGapOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  const [selectedBookId, setSelectedBookId] = useState<number | null>(bookId ? Number(bookId) : null);
  const [detailTab, setDetailTab] = useState<DetailTab>('topics');

  const [analysis, setAnalysis] = useState<BookGapAnalysis | null>(null);
  const [chapters, setChapters] = useState<BookGapChapter[]>([]);
  const [topics, setTopics] = useState<BookGapTopic[]>([]);
  const [queue, setQueue] = useState<BookGapItem[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const [selectedItem, setSelectedItem] = useState<BookGapItem | null>(null);
  const [statusBusyId, setStatusBusyId] = useState<number | null>(null);
  // Per-topic busy states for deep analysis + add-to-brain.
  const [deepBusyId, setDeepBusyId] = useState<number | null>(null);
  const [addBusyId, setAddBusyId] = useState<number | null>(null);
  const [addedTopicIds, setAddedTopicIds] = useState<Set<number>>(new Set());

  const [pdf, setPdf] = useState<{ url: string; page: number | null } | null>(null);
  const [toast, setToast] = useState<{ kind: string; msg: string } | null>(null);
  const toastTimer = useRef<number | undefined>(undefined);

  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const showToast = useCallback((kind: string, msg: string) => {
    setToast({ kind, msg });
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 5000);
  }, []);

  // Load the book shelf.
  const loadOverview = useCallback(async () => {
    setOverviewLoading(true);
    setOverviewError(null);
    try {
      setOverview(await bookGapApi.overview());
    } catch {
      setOverviewError('Could not load your books. Is the backend running?');
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
    return () => window.clearTimeout(toastTimer.current);
  }, [loadOverview]);

  const selectedBook = overview?.books.find((b) => b.book_id === selectedBookId) ?? null;

  const loadDetail = useCallback(
    async (bookIdNum: number) => {
      setDetailLoading(true);
      setDetailError(null);
      try {
        const [dash, itemRes, queueRes] = await Promise.all([
          bookGapApi.dashboard(bookIdNum),
          bookGapApi.items(bookIdNum),
          bookGapApi.queue(bookIdNum),
        ]);
        setAnalysis(dash.analysis);
        setChapters(dash.chapters);
        setTopics(dash.topics ?? []);
        setQueue(queueRes.items);
        void itemRes; // items endpoint kept for deep gaps; queue covers the actionable list
      } catch {
        setDetailError('Could not load the book analysis.');
      } finally {
        setDetailLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (selectedBookId != null) void loadDetail(selectedBookId);
  }, [selectedBookId, loadDetail]);

  const selectBook = useCallback(
    (id: number) => {
      setSelectedBookId(id);
      setDetailTab('topics');
      setAddedTopicIds(new Set());
      navigate(`/book-gaps/${id}`, { replace: true });
    },
    [navigate],
  );

  const backToShelf = useCallback(() => {
    setSelectedBookId(null);
    navigate('/book-gaps', { replace: true });
  }, [navigate]);

  const runAnalysis = useCallback(
    async (bookIdNum: number) => {
      setAnalyzing(true);
      setDetailError(null);
      try {
        const result = await bookGapApi.analyze(bookIdNum);
        setAnalysis(result.analysis);
        setChapters(result.chapters);
        setTopics(result.topics ?? []);
        await loadOverview();
        showToast(
          'success',
          `Stage 1 complete — ${result.topics?.length ?? 0} topics compared against your Second Brain. ` +
            'Click “Analyze Knowledge Gap” on any topic for a deep comparison.',
        );
      } catch {
        setDetailError('Analysis failed. The book may have no extractable text.');
        showToast('error', 'Analysis failed for this book.');
      } finally {
        setAnalyzing(false);
      }
    },
    [loadOverview, showToast],
  );

  const runDeepAnalysis = useCallback(
    async (topic: BookGapTopic) => {
      if (selectedBookId == null) return;
      setDeepBusyId(topic.id);
      setDetailError(null);
      // Optimistic: mark as analyzing in the list.
      setTopics((prev) => prev.map((t) => (t.id === topic.id ? { ...t, deep_status: 'ANALYZING' } : t)));
      try {
        const updated = await bookGapApi.analyzeTopic(selectedBookId, topic.id);
        setTopics((prev) => prev.map((t) => (t.id === topic.id ? updated : t)));
        // Refresh queue (missing sub-concepts became actionable items).
        const queueRes = await bookGapApi.queue(selectedBookId);
        setQueue(queueRes.items);
        void loadOverview();
        const missing = updated.deep_result?.missing?.length ?? 0;
        showToast(
          'success',
          missing > 0
            ? `Deep analysis done — ${missing} sub-concept(s) missing from your Second Brain.`
            : 'Deep analysis done — no gaps found in this topic.',
        );
      } catch {
        setDetailError('Deep analysis failed. Please try again.');
        showToast('error', 'Deep analysis failed.');
      } finally {
        setDeepBusyId(null);
      }
    },
    [selectedBookId, loadOverview, showToast],
  );

  const addTopicToBrain = useCallback(
    async (topic: BookGapTopic) => {
      if (selectedBookId == null) return;
      setAddBusyId(topic.id);
      try {
        const result = await bookGapApi.addTopicToBrain(selectedBookId, topic.id);
        setAddedTopicIds((prev) => new Set(prev).add(topic.id));
        showToast(
          'success',
          result.created
            ? `Created “${result.document.title}” in your Second Brain — open it to fill in what you learn.`
            : 'That topic already has a Second Brain study note.',
        );
      } catch {
        showToast('error', 'Could not add the topic to your Second Brain.');
      } finally {
        setAddBusyId(null);
      }
    },
    [selectedBookId, showToast],
  );

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = '';
      if (!file) return;
      if (file.size > BOOK_MAX_MB * 1024 * 1024) {
        showToast('error', `File too large (max ${BOOK_MAX_MB} MB)`);
        return;
      }
      setUploading(true);
      try {
        const { url } = await bookApi.uploadFile(file);
        const fname = file.name.replace(/\.pdf$/i, '') || 'Untitled book';
        const created = await bookApi.create({ title: fname, category: 'reading' });
        await bookApi.update(created.id, { file_url: url });
        await loadOverview();
        selectBook(created.id);
        setDetailTab('topics');
        await runAnalysis(created.id);
      } catch (err) {
        showToast('error', err instanceof Error ? err.message : 'Upload failed.');
      } finally {
        setUploading(false);
      }
    },
    [loadOverview, selectBook, runAnalysis, showToast],
  );

  const setStatus = useCallback(
    async (item: BookGapItem, s: 'learning' | 'learned' | 'mastered') => {
      if (selectedBookId == null) return;
      setStatusBusyId(item.id);
      try {
        const updated = await bookGapApi.setStatus(selectedBookId, item.id, s);
        setQueue((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
        setSelectedItem((cur) => (cur?.id === item.id ? updated : cur));
        void loadOverview();
        showToast('success', `Marked “${item.display_name}” as ${s}.`);
      } catch {
        showToast('error', 'Could not update status.');
      } finally {
        setStatusBusyId(null);
      }
    },
    [selectedBookId, loadOverview, showToast],
  );

  const openPdf = useCallback((page: number | null) => {
    if (!selectedBook?.file_url) return;
    setPdf({ url: selectedBook.file_url, page });
  }, [selectedBook]);

  const openItemPdf = useCallback((item: BookGapItem) => {
    if (!selectedBook?.file_url) return;
    setPdf({ url: selectedBook.file_url, page: item.page_start ?? null });
  }, [selectedBook]);

  const closeModal = useCallback(() => setSelectedItem(null), []);

  // Escape closes the modal / pdf overlay.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedItem(null);
        setPdf(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const byParent = (parent: string | null) => topics.filter((t) => (t.parent_title ?? null) === parent);
  const chaptersInTopics = topics.filter((t) => t.level === 1 && !t.parent_title);

  return (
    <div className="page-section">
      <Header title="📚 Knowledge Gap Reader" />

      {toast && (
        <div className={`toast toast-${toast.kind}`} style={{ position: 'fixed', bottom: '1.5rem', right: '1.5rem', zIndex: 9999 }} onClick={() => setToast(null)}>
          <span className="toast-icon">{toast.kind === 'success' ? '✅' : '⚠️'}</span>
          <span className="toast-message">{toast.msg}</span>
        </div>
      )}

      {selectedBook == null ? (
        /* ─────────────── SHELF VIEW ─────────────── */
        <>
          <div className="card" style={{ marginBottom: '1.25rem', background: 'linear-gradient(135deg, var(--bg-card), var(--bg-hover))' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '0.35rem' }}>
              Upload a book
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.9rem' }}>
              StudentOS analyzes the book&apos;s <strong>table of contents first</strong> (chapters → sections →
              subsections) and compares each topic against your Second Brain — so you see what you already know and
              what&apos;s completely missing. Deep per-topic analysis runs only when you click{' '}
              <strong>Analyze Knowledge Gap</strong>.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              style={{ display: 'none' }}
              onChange={handleUpload}
              disabled={uploading}
            />
            <button type="button" className="btn btn-primary" disabled={uploading} onClick={() => fileInputRef.current?.click()}>
              {uploading ? '⏳ Uploading & analyzing…' : '⬆️ Upload PDF'}
            </button>
            {!uploading && overview && overview.books.length > 0 && (
              <span style={{ marginLeft: '0.75rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {overview.total_concepts} topics tracked across {overview.books.length} books · {overview.learned_concepts} learned
              </span>
            )}
          </div>

          <div className="page-section">
            <h2>My Books</h2>
            {overviewLoading ? (
              <div className="card-grid"><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>
            ) : overviewError ? (
              <EmptyState icon="⚠️" title="Something went wrong" message={overviewError} />
            ) : !overview || overview.books.length === 0 ? (
              <EmptyState
                icon="📚"
                title="No books yet"
                message="Upload a PDF to compare its table of contents against your Second Brain."
                action={
                  <button type="button" className="btn btn-primary" onClick={() => fileInputRef.current?.click()}>
                    Upload a book
                  </button>
                }
              />
            ) : (
              <div className="card-grid">
                {overview.books.map((b) => {
                  const pct = b.analyzed ? Math.round((1 - b.recommended_pct / 100) * 100) : 0;
                  return (
                    <div key={b.book_id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{b.title}</div>
                      {b.author && <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{b.author}</div>}
                      {b.analyzed ? (
                        <>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            {b.total_concepts} topics · {b.known} known · {b.partial} partial · {b.unknown} unknown
                            {b.needs_review ? ` · ${b.needs_review} review` : ''}
                            {b.deep_analyzed ? ` · ${b.deep_analyzed} deep` : ''}
                          </div>
                          <div className="bgp-progress">
                            <div className="bgp-progress-fill" style={{ width: `${pct}%` }} />
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                            {b.recommended_pct > 0
                              ? `~${Math.round(b.recommended_pct)}% of pages need your attention.`
                              : 'Everything this book covers is already in your Second Brain.'}
                          </div>
                          <div style={{ marginTop: 'auto', display: 'flex', gap: '0.5rem' }}>
                            <button type="button" className="btn btn-primary btn-sm" onClick={() => selectBook(b.book_id)}>
                              View Topics & Gaps
                            </button>
                            <button type="button" className="btn btn-ghost btn-sm" disabled={analyzing} onClick={() => void runAnalysis(b.book_id)}>
                              ↻ Re-analyze TOC
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                            Not analyzed yet{b.file_url ? '' : ' — no PDF attached'}.
                          </div>
                          <div style={{ marginTop: 'auto', display: 'flex', gap: '0.5rem' }}>
                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              disabled={!b.file_url || analyzing}
                              onClick={() => {
                                selectBook(b.book_id);
                                void runAnalysis(b.book_id);
                              }}
                            >
                              {analyzing ? '⏳ Analyzing…' : 'Start TOC Analysis'}
                            </button>
                            {b.file_url && (
                              <button type="button" className="btn btn-ghost btn-sm" onClick={() => selectBook(b.book_id)}>
                                Open
                              </button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      ) : (
        /* ─────────────── BOOK DETAIL VIEW ─────────────── */
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={backToShelf}>← All books</button>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>{selectedBook.title}</h2>
            {selectedBook.file_url && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => openPdf(null)}>
                📄 Open PDF
              </button>
            )}
            <button type="button" className="btn btn-primary btn-sm" disabled={analyzing || !selectedBook.file_url} onClick={() => void runAnalysis(selectedBook.book_id)}>
              {analyzing ? '⏳ Analyzing…' : '↻ Re-analyze TOC'}
            </button>
          </div>

          {detailError && (
            <div className="notice" style={{ background: 'var(--danger-muted, var(--accent-muted))', color: 'var(--danger)', border: '1px solid var(--danger)', borderRadius: 'var(--radius)', padding: '0.75rem 1rem', marginBottom: '1rem' }}>
              {detailError}
            </div>
          )}

          {detailLoading ? (
            <div className="card-grid"><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>
          ) : !analysis ? (
            <EmptyState
              icon="🔬"
              title="Not analyzed yet"
              message="Run the table-of-contents analysis to see which topics you already know and which are missing from your Second Brain."
              action={
                <button type="button" className="btn btn-primary" disabled={!selectedBook.file_url || analyzing} onClick={() => void runAnalysis(selectedBook.book_id)}>
                  {analyzing ? '⏳ Analyzing…' : 'Start TOC Analysis'}
                </button>
              }
            />
          ) : (
            <>
              {/* Dashboard */}
              <div className="stat-grid">
                <StatTile label="Topics in TOC" value={analysis.total_concepts} sub={`${analysis.chapters} chapters`} />
                <StatTile label="Already known" value={analysis.known} color="var(--success)" />
                <StatTile label="Partially known" value={analysis.partial} color="var(--warning)" />
                <StatTile label="Missing" value={analysis.unknown} color="var(--danger)" />
                <StatTile label="Needs review" value={analysis.needs_review ?? 0} sub="low-confidence match" color="var(--info)" />
                <StatTile label="Deep analyzed" value={analysis.deep_analyzed ?? 0} sub="topics" color="var(--accent)" />
              </div>

              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                Stage 1 matched the book&apos;s headings against your Second Brain — no AI was used for this. For a deep
                comparison of any topic&apos;s actual content, click <strong>Analyze Knowledge Gap</strong>.
              </p>

              {/* Tabs */}
              <div className="tabs" role="tablist" aria-label="Book analysis sections">
                {([
                  ['topics', `Topics (${topics.length})`],
                  ['gaps', `Deep Gaps (${queue.length})`],
                  ['chapters', `Chapters (${chapters.length})`],
                ] as [DetailTab, string][]).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={detailTab === key}
                    className={`tab-btn${detailTab === key ? ' active' : ''}`}
                    onClick={() => setDetailTab(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {detailTab === 'topics' && (
                <div>
                  {topics.length === 0 ? (
                    <EmptyState icon="🗂️" title="No topics extracted" message="Re-analyze the TOC, or upload a book with extractable headings." />
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                      {chaptersInTopics.map((ch) => (
                        <div key={ch.id}>
                          <TopicRow
                            topic={ch}
                            onAnalyze={runDeepAnalysis}
                            onAddToBrain={addTopicToBrain}
                            onOpenPage={(p) => openPdf(p)}
                            busyAnalyze={deepBusyId === ch.id}
                            busyAdd={addBusyId === ch.id}
                            added={addedTopicIds.has(ch.id)}
                          />
                          {byParent(ch.title).map((s) => (
                            <TopicRow
                              key={s.id}
                              topic={s}
                              onAnalyze={runDeepAnalysis}
                              onAddToBrain={addTopicToBrain}
                              onOpenPage={(p) => openPdf(p)}
                              busyAnalyze={deepBusyId === s.id}
                              busyAdd={addBusyId === s.id}
                              added={addedTopicIds.has(s.id)}
                            />
                          ))}
                        </div>
                      ))}
                      {/* Any topics not nested under a chapter (edge case) */}
                      {topics.filter((t) => t.level > 1 && !chaptersInTopics.some((c) => c.title === t.parent_title)).map((t) => (
                        <TopicRow
                          key={t.id}
                          topic={t}
                          onAnalyze={runDeepAnalysis}
                          onAddToBrain={addTopicToBrain}
                          onOpenPage={(p) => openPdf(p)}
                          busyAnalyze={deepBusyId === t.id}
                          busyAdd={addBusyId === t.id}
                          added={addedTopicIds.has(t.id)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {detailTab === 'gaps' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {queue.length === 0 ? (
                    <EmptyState
                      icon="🎉"
                      title="No deep gaps yet"
                      message="Run 'Analyze Knowledge Gap' on a topic to find sub-concepts that are missing from your Second Brain — they appear here with page evidence."
                    />
                  ) : (
                    <>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {queue.length} missing sub-concept(s) found by deep analysis, ordered by priority. Each one is a
                        concrete thing to capture in your Second Brain.
                      </p>
                      {queue.map((it) => (
                        <GapItemCard key={it.id} item={it} onOpen={openItemPdf} onSetStatus={setStatus} busy={statusBusyId === it.id} />
                      ))}
                    </>
                  )}
                </div>
              )}

              {detailTab === 'chapters' && (
                <div className="card">
                  {chapters.length === 0 ? (
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>No chapters detected.</p>
                  ) : (
                    <div className="data-table">
                      {chapters.map((c) => (
                        <div key={c.chapter} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.6rem 0', borderBottom: '1px solid var(--border)' }}>
                          <span style={{ flex: 1, fontWeight: 600, fontSize: '0.85rem' }}>{c.chapter}</span>
                          <span className="badge badge-success">✓ {c.known}</span>
                          <span className="badge badge-warning">◐ {c.partial}</span>
                          <span className="badge badge-danger">✗ {c.unknown}</span>
                          {c.historical > 0 && <span className="badge badge-info">⚠ {c.historical}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ── Deep gap item modal ── */}
      {selectedItem && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" style={{ maxWidth: '680px', width: '100%' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <span className="bgp-status-icon unknown">✗</span>
                  <h2 className="modal-title" style={{ margin: 0 }}>{selectedItem.display_name}</h2>
                </div>
                <div className="bgp-item-meta">
                  <span className="badge badge-danger">Missing from Second Brain</span>
                  <KnowledgeDots level={selectedItem.knowledge_level} />
                </div>
              </div>
              <button type="button" className="btn btn-ghost btn-sm" onClick={closeModal}>✕</button>
            </div>

            {selectedItem.chapter && (
              <div className="bgp-source-block" style={{ marginTop: '1rem' }}>
                <div className="bgp-chapter">📖 {selectedItem.chapter}</div>
                {selectedItem.page_start != null && (
                  <div className="bgp-chapter">
                    📄 {selectedItem.page_start === selectedItem.page_end ? `Page ${selectedItem.page_start}` : `Pages ${selectedItem.page_start}–${selectedItem.page_end}`}
                  </div>
                )}
              </div>
            )}

            {selectedItem.why && <p className="bgp-why" style={{ marginTop: '0.9rem' }}>{selectedItem.why}</p>}

            <div className="modal-actions" style={{ justifyContent: 'flex-start', flexWrap: 'wrap' }}>
              {selectedItem.page_start != null && (
                <button type="button" className="btn btn-primary" onClick={() => { openItemPdf(selectedItem); setSelectedItem(null); }}>
                  Open Page {selectedItem.page_start}
                </button>
              )}
              {selectedItem.my_status === 'LEARNED' || selectedItem.my_status === 'MASTERED' ? (
                <span className={`badge ${selectedItem.my_status === 'MASTERED' ? 'badge-info' : 'badge-success'}`} style={{ fontSize: '0.85rem', padding: '0.45rem 1rem' }}>
                  {selectedItem.my_status === 'MASTERED' ? '★ Mastered' : '✓ Learned'}
                </span>
              ) : (
                <>
                  <button type="button" className="btn btn-ghost" disabled={statusBusyId === selectedItem.id} onClick={() => void setStatus(selectedItem, 'learning')}>
                    Mark as Learning
                  </button>
                  <button type="button" className="btn btn-ghost" disabled={statusBusyId === selectedItem.id} onClick={() => void setStatus(selectedItem, 'learned')}>
                    Mark as Learned
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── PDF reader (page jump via #page=N) ── */}
      {pdf && selectedBook?.file_url && (
        <PDFReader url={pdf.url} title={selectedBook.title} initialPage={pdf.page} onClose={() => setPdf(null)} />
      )}
    </div>
  );
};
