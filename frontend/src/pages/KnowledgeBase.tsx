import { useCallback, useEffect, useRef, useState } from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { ExplainPanel } from '../components/kb/ExplainPanel';
import { MindMapView } from '../components/kb/MindMapView';
import { NoteActions } from '../components/kb/NoteActions';
import { QualityPanel } from '../components/kb/QualityPanel';
import { SummaryPanel } from '../components/kb/SummaryPanel';
import { Phase10Panel } from '../components/kb/Phase10Panel';
import {
  downloadAsFile,
  endpoints,
  type KbChunk,
  type KbCitation,
  type KbDiffResponse,
  type KbAutomationJob,
  type KbDocument,
  type KbDuplicateItem,
  type KbJob,
  type KbLinksResponse,
  type KbSource,
  type KbStats,
  type KbTagSuggestion,
  type KbVersion,
} from '../services/api';

const STATUS_COLORS: Record<string, string> = {
  new: '#3b82f6',
  changed: '#f59e0b',
  unchanged: '#10b981',
  deleted: '#6b7280',
  failed: '#ef4444',
  draft: '#8b5cf6',
};

const JOB_COLORS: Record<string, string> = {
  queued: '#6b7280',
  running: '#3b82f6',
  done: '#10b981',
  failed: '#ef4444',
  interrupted: '#f59e0b',
};

function Chip({ label, color }: { label: string; color: string }) {
  return (
    <span
      style={{
        fontSize: '0.68rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
        color: color,
        background: `${color}1a`,
        padding: '0.15rem 0.5rem',
        borderRadius: '999px',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}

const fmt = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '—';

export const KnowledgeBase = () => {
  const [sources, setSources] = useState<KbSource[]>([]);
  const [docs, setDocs] = useState<KbDocument[]>([]);
  const [jobs, setJobs] = useState<KbJob[]>([]);
  const [loading, setLoading] = useState(true);

  // filters
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');

  // modals
  const [showSource, setShowSource] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [showPaper, setShowPaper] = useState(false);
  const [sourceName, setSourceName] = useState('');
  const [sourcePath, setSourcePath] = useState('');
  const [arxivId, setArxivId] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // Per-source folder input for the "Update from folder" action (relative to
  // the source root; blank = whole source).
  const [folderInputs, setFolderInputs] = useState<Record<number, string>>({});
  // Per-source external-vault path for the "local" sync adapter (Copy Recent
  // Notes): the source-of-truth Obsidian vault mirrored into notes/.
  const [syncSourcePaths, setSyncSourcePaths] = useState<Record<number, string>>({});

  // Phase 2: stats + panels
  const [stats, setStats] = useState<KbStats | null>(null);
  const [duplicates, setDuplicates] = useState<KbDuplicateItem[]>([]);
  const [tagSuggestions, setTagSuggestions] = useState<KbTagSuggestion[]>([]);
  const [appliedTags, setAppliedTags] = useState<KbTagSuggestion[]>([]);
  const [newTagName, setNewTagName] = useState('');
  // Explicit "Suggest with AI" action state — the only path that re-runs the
  // AI tag proposal (the GET endpoint reads persisted suggestions only).
  const [proposingTags, setProposingTags] = useState(false);

  // Phase 4: manual concept/note linking autocomplete (Idea 37)
  const [linkKind, setLinkKind] = useState<'concept' | 'document'>('concept');
  const [linkQuery, setLinkQuery] = useState('');
  const [linkResults, setLinkResults] = useState<
    { kind: 'concept' | 'document'; id: number; label: string }[]
  >([]);
  const [linkBusy, setLinkBusy] = useState(false);

  // document detail drawer
  const [activeDoc, setActiveDoc] = useState<KbDocument | null>(null);
  const [chunks, setChunks] = useState<KbChunk[]>([]);
  const [versions, setVersions] = useState<KbVersion[]>([]);
  const [diff, setDiff] = useState<KbDiffResponse | null>(null);
  // Phase 4: per-document links + citations
  const [links, setLinks] = useState<KbLinksResponse | null>(null);
  const [citations, setCitations] = useState<KbCitation[]>([]);
  // Phase 8 (Idea 76): connect-suggestions for the open document
  const [connectItems, setConnectItems] = useState<
    { document_id: number; title: string; shared_concepts: string[]; reasons: string[]; target_status: string }[]
  >([]);
  const [connectBusy, setConnectBusy] = useState(false);

  // Phase 9 (Ideas 81–90): automation jobs + per-source sync
  const [autoJobs, setAutoJobs] = useState<KbAutomationJob[]>([]);
  const [autoRunning, setAutoRunning] = useState<string | null>(null);
  const [syncStatuses, setSyncStatuses] = useState<Record<number, { last_scanned_at: string | null; cursor: Record<string, unknown>; sync_type: string }>>({});

  const flash = (msg: string) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(null), 3500);
  };

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, j, st] = await Promise.all([
        endpoints.kb.sources.list(),
        endpoints.kb.jobs.list().catch(() => ({ items: [], total: 0 })),
        endpoints.kb.stats().catch(() => null),
      ]);
      setSources(s.items);
      setJobs(j.items);
      setStats(st);
    } catch {
      /* token may be missing — auth gate handles it */
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDuplicates = useCallback(async () => {
    try {
      const res = await endpoints.kb.duplicates.list();
      setDuplicates(res.items);
    } catch {
      setDuplicates([]);
    }
  }, []);

  const loadAutoJobs = useCallback(async () => {
    try {
      const res = await endpoints.kb.automation.jobs();
      setAutoJobs(res.jobs ?? []);
    } catch {
      setAutoJobs([]);
    }
  }, []);

  const runAutoJob = async (name: string) => {
    setAutoRunning(name);
    try {
      const res = await endpoints.kb.automation.run({ mode: 'one', name, force: true });
      if (res.skipped) {
        flash(`Automation “${name}” skipped${res.reason ? ` — ${res.reason}` : ''}`);
      } else if (res.status === 'queued') {
        flash(`Automation “${name}” queued — running in background (watch Jobs below)`);
      } else {
        flash(`Automation “${name}” done`);
      }
      await Promise.all([loadAll(), loadAutoJobs()]);
    } catch (e) {
      flash(`Automation failed: ${(e as Error).message}`);
    } finally {
      setAutoRunning(null);
    }
  };

  const syncSource = async (id: number) => {
    setBusy(`sync-${id}`);
    try {
      const res = await endpoints.kb.sources.sync(id);
      if (res.skipped) flash(`Sync skipped — ${res.reason ?? ''}`);
      else if (res.copied !== undefined) {
        // "local" adapter (Copy Recent Notes): delta-copied knowledge files.
        flash(`Copy Recent Notes — ${res.copied} copied, ${res.unchanged ?? 0} unchanged, ${res.removed ?? 0} removed`);
      } else {
        flash(`Sync done — ${res.imported ?? 0} imported, ${res.unchanged ?? 0} unchanged${res.skipped_stale ? `, ${res.skipped_stale} stale` : ''}`);
      }
      await Promise.all([loadAll(), loadDocs()]);
      void loadSyncStatuses();
    } catch (e) {
      flash(`Sync failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  // Save the external-vault path used by the "local" adapter (Copy Recent
  // Notes). Only a directory path is accepted; saving does not sync.
  const saveSyncSourcePath = async (s: KbSource) => {
    const value = (syncSourcePaths[s.id] ?? '').trim();
    if (!value) {
      flash('Enter the external vault folder path first');
      return;
    }
    setBusy(`syncpath-${s.id}`);
    try {
      await endpoints.kb.sources.update(s.id, { sync_source_path: value, sync_type: 'local' });
      flash('External vault saved — hit Copy Recent Notes to sync');
      await Promise.all([loadAll(), loadDocs()]);
    } catch (e) {
      flash(`Could not save external vault: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const loadSyncStatuses = useCallback(async () => {
    const next: Record<number, { last_scanned_at: string | null; cursor: Record<string, unknown>; sync_type: string }> = {};
    await Promise.all(
      sources.map(async (s) => {
        if (s.sync_type === 'none') return;
        try {
          const st = await endpoints.kb.sources.syncStatus(s.id);
          next[s.id] = { last_scanned_at: st.last_scanned_at, cursor: st.cursor, sync_type: st.sync_type };
        } catch {
          /* source not syncable yet */
        }
      }),
    );
    setSyncStatuses(next);
  }, [sources]);

  useEffect(() => {
    void loadAutoJobs();
  }, [loadAutoJobs]);

  useEffect(() => {
    void loadSyncStatuses();
  }, [loadSyncStatuses]);

  const loadDocs = useCallback(async () => {
    try {
      const res = await endpoints.kb.documents.list({
        source_id: sourceFilter ? Number(sourceFilter) : undefined,
        status: statusFilter || undefined,
        q: query || undefined,
        page_size: 100,
      });
      setDocs(res.items);
    } catch {
      setDocs([]);
    }
  }, [sourceFilter, statusFilter, query]);

  useEffect(() => {
    void loadAll();
    void loadDuplicates();
  }, [loadAll, loadDuplicates]);

  useEffect(() => {
    void loadDocs();
  }, [loadDocs]);

  // poll job status while any job is queued/running
  useEffect(() => {
    const active = jobs.some((j) => j.status === 'queued' || j.status === 'running');
    if (!active) return;
    const t = window.setInterval(() => void loadAll(), 1500);
    return () => window.clearInterval(t);
  }, [jobs, loadAll]);

  const addSource = async () => {
    if (!sourceName.trim() || !sourcePath.trim()) return;
    setBusy('source');
    try {
      await endpoints.kb.sources.create({ name: sourceName.trim(), root_path: sourcePath.trim(), source_type: 'vault_folder' });
      setSourceName('');
      setSourcePath('');
      setShowSource(false);
      flash('Source registered ✓');
      await loadAll();
    } catch (e) {
      flash(`Failed to add source: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const scanSource = async (id: number, path?: string) => {
    setBusy(`scan-${id}`);
    const where = path ? ` from “${path}”` : '';
    try {
      const res = await endpoints.kb.sources.scan(id, path);
      const s = res.summary;
      flash(
        s
          ? `Update${where} — ${s.added ?? 0} added, ${s.changed ?? 0} changed, ${s.duplicates_found ?? 0} duplicates`
          : 'Scan job queued',
      );
      await Promise.all([loadAll(), loadDocs()]);
    } catch (e) {
      flash(`Update from folder failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const toggleSource = async (s: KbSource) => {
    await endpoints.kb.sources.update(s.id, { enabled: !s.enabled });
    await loadAll();
  };

  const removeSource = async (id: number) => {
    if (!window.confirm('Delete this source and ALL of its documents, chunks and versions?')) return;
    await endpoints.kb.sources.remove(id);
    if (activeDoc?.source_id === id) setActiveDoc(null);
    await loadAll();
    await loadDocs();
  };

  const uploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy('upload');
    try {
      const res = await endpoints.kb.documents.upload(file, sourceFilter ? Number(sourceFilter) : undefined);
      if (res.deduped) flash(`Duplicate detected — linked to document #${res.duplicate_of_id} (deduplicated)`);
      else flash('Document uploaded & ingested ✓');
      setShowUpload(false);
      await loadAll();
      await loadDocs();
    } catch (err) {
      flash(`Upload failed: ${(err as Error).message}`);
    } finally {
      setBusy(null);
    }
    e.target.value = '';
  };

  const importPaper = async () => {
    if (!arxivId.trim()) return;
    setBusy('paper');
    try {
      const res = await endpoints.kb.papers.import(arxivId.trim(), sourceFilter ? Number(sourceFilter) : undefined);
      flash(res.metadata_fetched ? `Imported “${res.document.title}” ✓` : 'Paper added (arXiv offline — metadata skipped)');
      setArxivId('');
      setShowPaper(false);
      await loadAll();
      await loadDocs();
    } catch (err) {
      flash(`Import failed: ${(err as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const removeDoc = async (id: number) => {
    if (!window.confirm('Delete this document?')) return;
    await endpoints.kb.documents.remove(id);
    if (activeDoc?.id === id) setActiveDoc(null);
    await loadDocs();
  };

  const reindexDoc = async (id: number) => {
    await endpoints.kb.documents.reindex(id);
    flash('Reindex job queued');
    await loadAll();
  };

  const openDoc = async (doc: KbDocument) => {
    setActiveDoc(doc);
    setDiff(null);
    try {
      const [c, v, t, l, cite] = await Promise.all([
        endpoints.kb.documents.chunks(doc.id),
        endpoints.kb.documents.versions(doc.id).catch(() => [] as KbVersion[]),
        endpoints.kb.tags.forDocument(doc.id).catch(() => ({ tags: [] as KbTagSuggestion[], applied: [] as KbTagSuggestion[], document_id: doc.id })),
        endpoints.kb.documents.links(doc.id).catch(() => ({ document_id: doc.id, concepts: [], related: [] })),
        endpoints.kb.citations.forDocument(doc.id).catch(() => ({ items: [] as KbCitation[], total: 0 })),
      ]);
      setChunks(c);
      setVersions(v);
      setTagSuggestions(t.tags ?? []);
      setAppliedTags(t.applied ?? []);
      setLinks(l);
      setCitations(cite.items ?? []);
      // Phase 8 (Idea 76): load connect-suggestions alongside the drawer.
      endpoints.kb.connect
        .suggestions(doc.id)
        .then((res) => setConnectItems(res.items ?? []))
        .catch(() => setConnectItems([]));
    } catch {
      setChunks([]);
      setVersions([]);
      setTagSuggestions([]);
      setAppliedTags([]);
      setLinks(null);
      setCitations([]);
      setConnectItems([]);
    }
  };

  const confirmConnect = async (targetId: number) => {
    if (!activeDoc) return;
    setConnectBusy(true);
    try {
      await endpoints.kb.connect.confirm(activeDoc.id, targetId);
      flash('Connected ✓ — manual edge created');
      setConnectItems((prev) => prev.filter((c) => c.document_id !== targetId));
      await reloadLinks();
    } catch (e) {
      flash(`Connect failed: ${(e as Error).message}`);
    } finally {
      setConnectBusy(false);
    }
  };

  // Deep links: ?doc=<id> (from search results / the graph / insights) opens
  // the document drawer on arrival (Phase 3, Idea 25 phrase 50).
  useEffect(() => {
    const docParam = new URLSearchParams(window.location.search).get('doc');
    if (!docParam) return;
    const docId = Number(docParam);
    if (!Number.isInteger(docId) || docId <= 0) return;
    endpoints.kb.documents
      .get(docId)
      .then((doc) => void openDoc(doc))
      .catch(() => {});
    // openDoc is stable-per-render and we only want the arrival URL once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reindexSource = async (id: number) => {
    setBusy(`reindex-${id}`);
    try {
      await endpoints.kb.reindex.source(id);
      flash('Reindex job queued for source');
    } catch (e) {
      flash(`Reindex failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
    await loadAll();
  };

  const backfillAll = async () => {
    if (!window.confirm('Reindex ALL documents? This re-embeds and re-tags everything.')) return;
    setBusy('backfill');
    try {
      await endpoints.kb.reindex.backfill();
      flash('Full reindex queued');
    } catch (e) {
      flash(`Backfill failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
    await loadAll();
  };

  const scanDuplicates = async () => {
    setBusy('dup-scan');
    try {
      const res = await endpoints.kb.duplicates.scan();
      setDuplicates(res.items);
      flash(`Near-dup scan done — ${res.total} pair${res.total === 1 ? '' : 's'} found`);
    } catch (e) {
      flash(`Scan failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const mergeDuplicate = async (keepId: number, mergeId: number) => {
    if (!window.confirm(`Merge document #${mergeId} into #${keepId}? Chunks, tags and versions will be reassigned.`)) return;
    try {
      await endpoints.kb.duplicates.merge(keepId, [mergeId]);
      flash(`Merged #${mergeId} into #${keepId}`);
      await Promise.all([loadDuplicates(), loadDocs()]);
    } catch (e) {
      flash(`Merge failed: ${(e as Error).message}`);
    }
  };

  const archiveDuplicate = async (docId: number) => {
    try {
      await endpoints.kb.duplicates.archive(docId);
      flash(`Archived #${docId}`);
      await loadDuplicates();
    } catch (e) {
      flash(`Archive failed: ${(e as Error).message}`);
    }
  };

  // Explicit user action: re-run the AI (or deterministic-fallback) tag
  // proposal and persist the result. Never triggered by navigation.
  const proposeTagsWithAi = async () => {
    if (!activeDoc) return;
    setProposingTags(true);
    try {
      const res = await endpoints.kb.tags.propose(activeDoc.id);
      setTagSuggestions(res.tags ?? []);
      setAppliedTags(res.applied ?? []);
      flash('Tag suggestions refreshed ✓');
    } catch (e) {
      flash(`Suggest failed: ${(e as Error).message}`);
    } finally {
      setProposingTags(false);
    }
  };

  const applyTag = async (tagId: number) => {
    if (!activeDoc) return;
    try {
      const res = await endpoints.kb.tags.apply(activeDoc.id, [tagId]);
      setTagSuggestions(res.tags ?? []);
      setAppliedTags(res.applied ?? []);
      flash('Tag applied ✓');
    } catch (e) {
      flash(`Apply failed: ${(e as Error).message}`);
    }
  };

  const rejectTag = async (tagId: number) => {
    if (!activeDoc) return;
    try {
      await endpoints.kb.tags.reject(activeDoc.id, tagId);
      setTagSuggestions((prev) => prev.filter((t) => t.tag_id !== tagId));
      setAppliedTags((prev) => prev.filter((t) => t.tag_id !== tagId));
      flash('Tag removed');
    } catch (e) {
      flash(`Reject failed: ${(e as Error).message}`);
    }
  };

  const createTag = async (rawName?: string) => {
    if (!activeDoc) return;
    const name = (rawName ?? newTagName).trim();
    if (!name) return;
    try {
      const res = await endpoints.kb.tags.create(activeDoc.id, name);
      setTagSuggestions(res.tags ?? []);
      setAppliedTags(res.applied ?? []);
      setNewTagName('');
      flash(name.startsWith('course:') ? `Course tag added — sync Courses to see it 🧠` : 'Tag added ✓');
    } catch (e) {
      flash(`Add tag failed: ${(e as Error).message}`);
    }
  };

  const restoreVersion = async (versionId: number) => {
    if (!activeDoc) return;
    if (!window.confirm('Restore this version? A rollback snapshot will be saved.')) return;
    const res = await endpoints.kb.documents.restore(activeDoc.id, versionId);
    flash(`Restored — new version #${res.new_version_seq} created`);
    const v = await endpoints.kb.documents.versions(activeDoc.id);
    setVersions(v);
    await loadDocs();
  };

  const loadDiff = async (from: number, to: number) => {
    if (!activeDoc) return;
    try {
      setDiff(await endpoints.kb.documents.diff(activeDoc.id, from, to));
    } catch {
      setDiff(null);
    }
  };

  // ── Phase 4: manual concept/note linking (Idea 37) ──
  const linkSeqRef = useRef(0);

  const searchLinks = async (q: string) => {
    setLinkQuery(q);
    const seq = ++linkSeqRef.current;
    if (!q.trim()) {
      setLinkResults([]);
      return;
    }
    try {
      if (linkKind === 'concept') {
        const res = await endpoints.kb.concepts.list(q, 1, 8);
        const results = res.items.map((c) => ({ kind: 'concept' as const, id: c.id, label: c.canonical_name }));
        if (linkSeqRef.current === seq) setLinkResults(results);
      } else {
        const res = await endpoints.kb.documents.list({ q, page_size: 8 });
        const results = res.items.map((d) => ({
          kind: 'document' as const,
          id: d.id,
          label: d.title ?? d.path_rel ?? `#${d.id}`,
        }));
        if (linkSeqRef.current === seq) setLinkResults(results);
      }
    } catch {
      if (linkSeqRef.current === seq) setLinkResults([]);
    }
  };

  // Refresh only the links + citations state (cheaper than re-opening the drawer).
  const reloadLinks = async () => {
    if (!activeDoc) return;
    try {
      const [l, cite] = await Promise.all([
        endpoints.kb.documents.links(activeDoc.id).catch(() => ({ document_id: activeDoc.id, concepts: [], related: [] })),
        endpoints.kb.citations.forDocument(activeDoc.id).catch(() => ({ items: [] as KbCitation[], total: 0 })),
      ]);
      setLinks(l);
      setCitations(cite.items ?? []);
    } catch {
      setLinks(null);
      setCitations([]);
    }
  };

  const createLink = async (target: { kind: 'concept' | 'document'; id: number; label: string }) => {
    if (!activeDoc) return;
    setLinkBusy(true);
    try {
      await endpoints.kb.edges.create({
        source_document_id: activeDoc.id,
        target_id: target.id,
        relation: target.kind === 'concept' ? 'MENTIONS' : 'RELATED',
        target_type: target.kind,
      });
      flash(`Linked to “${target.label}” ✓`);
      setLinkQuery('');
      setLinkResults([]);
      await reloadLinks(); // refresh the links panel only
    } catch (e) {
      flash(`Link failed: ${(e as Error).message}`);
    } finally {
      setLinkBusy(false);
    }
  };

  const deleteEdge = async (edgeId: number) => {
    try {
      await endpoints.kb.edges.remove(edgeId);
      flash('Link removed');
      await reloadLinks();
    } catch (e) {
      flash(`Remove failed: ${(e as Error).message}`);
    }
  };

  const exportBibtex = async () => {
    try {
      await downloadAsFile(endpoints.kb.citations.exportUrl(), 'citations.bib');
      flash('BibTeX downloaded ✓');
    } catch (e) {
      flash(`Export failed: ${(e as Error).message}`);
    }
  };

  const progress = (j: KbJob) =>
    j.total_items > 0 ? Math.round((j.processed_items / j.total_items) * 100) : 0;

  return (
    <div className="page-section">
      <Header title="Second Brain" />

      {notice && (
        <div
          style={{
            padding: '0.6rem 1rem', borderRadius: '8px', marginBottom: '1rem',
            background: 'var(--accent, #2563eb)22', color: 'var(--text, #111)', fontSize: '0.85rem',
          }}
        >
          {notice}
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowSource(true)}>＋ Add Source</button>
        <button type="button" className="btn btn-ghost" onClick={() => setShowUpload(true)}>📤 Upload Document</button>
        <button type="button" className="btn btn-ghost" onClick={() => setShowPaper(true)}>📄 Import arXiv Paper</button>
        <button type="button" className="btn btn-ghost" disabled={busy === 'backfill'} onClick={() => void backfillAll()}>
          {busy === 'backfill' ? 'Queuing…' : '⟳ Reindex All'}
        </button>
      </div>

      {/* ── Phase 2 stats strip ── */}
      {stats && (
        <div className="card" style={{ padding: '0.75rem 1rem', marginBottom: '1rem', display: 'flex', gap: '1.25rem', flexWrap: 'wrap', fontSize: '0.78rem' }}>
          <span>📄 <strong>{stats.document_count}</strong> docs</span>
          <span>🧩 <strong>{stats.chunk_count}</strong> chunks</span>
          <span>🧠 <strong>{stats.embedding_count}</strong> embedded ({stats.embedded_documents} docs)</span>
          <span>🏷️ <strong>{stats.tag_count}</strong> tags</span>
          <span>💡 <strong>{stats.concept_count}</strong> concepts</span>
          <span>🔗 <strong>{stats.edge_count}</strong> edges · <strong>{stats.duplicate_count}</strong> dup</span>
          {stats.dirty_documents > 0 && (
            <span style={{ color: '#f59e0b', fontWeight: 700 }}>⚠ {stats.dirty_documents} need reindex</span>
          )}
        </div>
      )}

      {/* ── Sources ── */}
      <h3 style={{ margin: '0.75rem 0 0.5rem', fontSize: '0.95rem' }}>🗂️ Sources</h3>
      {loading ? (
        <p style={{ color: 'var(--text-secondary)' }}>Loading…</p>
      ) : sources.length === 0 ? (
        <EmptyState
          icon="🗂️"
          title="No knowledge sources"
          message="Register your Obsidian vault folder (or any notes directory) to start ingesting."
          action={<button type="button" className="btn btn-primary" onClick={() => setShowSource(true)}>Add Source</button>}
        />
      ) : (
        <div className="card-grid">
          {sources.map((s) => (
            <div key={s.id} className="card" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>{s.name}</strong>
                <Chip label={s.enabled ? 'enabled' : 'disabled'} color={s.enabled ? '#10b981' : '#6b7280'} />
              </div>
              <code style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', overflowWrap: 'anywhere' }}>{s.root_path}</code>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {s.document_count} docs · {s.files_seen} files · last scan {fmt(s.last_scanned_at)}
              </div>
              {/* Knowledge-root badge: sources rooted at a `notes` folder are
                  the knowledge area — daily-life/ is never indexed. */}
              {s.root_path?.split(/[\\/]/).filter(Boolean).pop()?.toLowerCase() === 'notes' && (
                <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>
                  📚 knowledge root — daily-life/ excluded
                </span>
              )}
              {/* Phase 9 (Idea 89): external-sync badge + status */}
              {s.sync_type !== 'none' && (
                <div style={{ fontSize: '0.72rem', color: '#7c3aed', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Chip label={s.sync_type === 'local' ? 'external vault' : s.sync_type} color="#7c3aed" />
                  <span>
                    last sync {fmt(syncStatuses[s.id]?.last_scanned_at ?? null)}
                  </span>
                </div>
              )}
              {/* "local" adapter: external vault path editor (Copy Recent Notes). */}
              {s.sync_type === 'local' && (
                <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    value={syncSourcePaths[s.id] ?? s.sync_source_path ?? ''}
                    onChange={(e) => setSyncSourcePaths((prev) => ({ ...prev, [s.id]: e.target.value }))}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') void saveSyncSourcePath(s);
                    }}
                    placeholder="/path/to/your/Obsidian vault (source of truth)"
                    aria-label={`External vault path for ${s.name}`}
                    style={{ flex: 1, minWidth: 200, fontSize: '0.72rem', padding: '0.25rem 0.55rem', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg, #fff)', color: 'var(--text)' }}
                  />
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost"
                    disabled={busy === `syncpath-${s.id}`}
                    title="Save this folder as the external vault that Copy Recent Notes mirrors into notes/"
                    onClick={() => void saveSyncSourcePath(s)}
                  >
                    {busy === `syncpath-${s.id}` ? 'Saving…' : '💾 Save'}
                  </button>
                </div>
              )}
              <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.25rem', flexWrap: 'wrap' }}>
                {s.sync_type !== 'none' && (
                  <button type="button" className="btn btn-sm btn-ghost" disabled={busy === `sync-${s.id}`} onClick={() => void syncSource(s.id)}>
                    {busy === `sync-${s.id}` ? 'Syncing…' : s.sync_type === 'local' ? '📋 Copy Recent Notes' : '🔁 Sync now'}
                  </button>
                )}
                <button type="button" className="btn btn-sm btn-primary" disabled={busy === `scan-${s.id}`} onClick={() => void scanSource(s.id)}>
                  {busy === `scan-${s.id}` ? 'Scanning…' : '▶ Scan now'}
                </button>
                {/* Update from folder: scan a subfolder (or the whole source)
                    so updated & newly created files land in the Second Brain. */}
                <input
                  value={folderInputs[s.id] ?? ''}
                  onChange={(e) => setFolderInputs((prev) => ({ ...prev, [s.id]: e.target.value }))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const p = (folderInputs[s.id] ?? '').trim();
                      void scanSource(s.id, p || undefined);
                    }
                  }}
                  placeholder="folder… (e.g. cybersecurity)"
                  aria-label={`Update ${s.name} from a folder`}
                  style={{ flex: 1, minWidth: 150, fontSize: '0.72rem', padding: '0.25rem 0.55rem', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg, #fff)', color: 'var(--text)' }}
                />
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  disabled={busy === `scan-${s.id}`}
                  title="Scan just this folder (blank = whole source) and ingest new/changed files"
                  onClick={() => void scanSource(s.id, (folderInputs[s.id] ?? '').trim() || undefined)}
                >
                  {busy === `scan-${s.id}` ? 'Updating…' : '📁 Update from folder'}
                </button>
                <button type="button" className="btn btn-sm btn-ghost" disabled={busy === `reindex-${s.id}`} onClick={() => void reindexSource(s.id)}>
                  {busy === `reindex-${s.id}` ? 'Reindexing…' : '⟳ Reindex'}
                </button>
                <button type="button" className="btn btn-sm btn-ghost" onClick={() => void toggleSource(s)}>
                  {s.enabled ? 'Pause' : 'Resume'}
                </button>
                <button type="button" className="btn btn-sm btn-ghost" onClick={() => void removeSource(s.id)}>🗑</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Documents ── */}
      <h3 style={{ margin: '1.25rem 0 0.5rem', fontSize: '0.95rem' }}>📄 Documents</h3>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <select className="form-input" style={{ maxWidth: 200 }} value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <select className="form-input" style={{ maxWidth: 160 }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">Any status</option>
          {['new', 'changed', 'unchanged', 'deleted', 'failed'].map((st) => (
            <option key={st} value={st}>{st}</option>
          ))}
        </select>
        <input
          className="form-input"
          style={{ minWidth: 200, flex: 1 }}
          placeholder="Search title / path…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && setQuery(search)}
        />
      </div>

      {docs.length === 0 ? (
        <EmptyState icon="📄" title="No documents" message="Scan a source or upload a file to populate your knowledge base." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {docs.map((d) => (
            <div
              key={d.id}
              className="card"
              style={{ padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', cursor: 'pointer' }}
              onClick={() => void openDoc(d)}
            >
              <div style={{ flex: 1, minWidth: 180 }}>
                <strong style={{ fontSize: '0.9rem' }}>{d.title ?? d.path_rel}</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                  {d.doc_type.toUpperCase()} · {d.char_count.toLocaleString()} chars · {d.chunk_count} chunks
                  {d.path_rel ? ` · ${d.path_rel}` : ''}
                </div>
                {d.metadata?.wikilinks?.length ? (
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    🔗 {d.metadata.wikilinks.slice(0, 4).join(', ')}{d.metadata.wikilinks.length > 4 ? '…' : ''}
                  </div>
                ) : null}
              </div>
              <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <Chip label={d.status} color={STATUS_COLORS[d.status] ?? '#6b7280'} />
                {d.ocr_used && <Chip label="OCR" color="#8b5cf6" />}
                {d.needs_ocr && !d.ocr_used && <Chip label="needs OCR" color="#f59e0b" />}
              </div>
              <div style={{ display: 'flex', gap: '0.35rem' }}>
                <button type="button" className="btn btn-sm btn-ghost" title="Reindex" onClick={(e) => { e.stopPropagation(); void reindexDoc(d.id); }}>⟳</button>
                <button type="button" className="btn btn-sm btn-ghost" title="Delete" onClick={(e) => { e.stopPropagation(); void removeDoc(d.id); }}>🗑</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Phase 2 duplicates review queue ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: '1.25rem 0 0.5rem' }}>
        <h3 style={{ fontSize: '0.95rem', margin: 0 }}>♻️ Near-duplicates ({duplicates.length})</h3>
        <button type="button" className="btn btn-sm btn-ghost" disabled={busy === 'dup-scan'} onClick={() => void scanDuplicates()}>
          {busy === 'dup-scan' ? 'Scanning…' : '▶ Scan now'}
        </button>
      </div>
      {duplicates.length === 0 ? (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No duplicate pairs — run a scan to detect near-duplicate documents.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {duplicates.slice(0, 10).map((d) => (
            <div key={`${d.document_id}-${d.duplicate_of_id}`} className="card" style={{ padding: '0.6rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.8rem' }}>
                #<strong>{d.document_id}</strong> ≅ #<strong>{d.duplicate_of_id}</strong>
              </span>
              <Chip label={`${(d.similarity * 100).toFixed(0)}%`} color={d.similarity >= 0.95 ? '#ef4444' : '#f59e0b'} />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{d.method}</span>
              <span style={{ flex: 1 }} />
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => void mergeDuplicate(d.duplicate_of_id, d.document_id)}>Merge</button>
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => void archiveDuplicate(d.document_id)}>Archive</button>
            </div>
          ))}
        </div>
      )}

      {/* ── Phase 9 automation (Ideas 81–90) ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', margin: '1.25rem 0 0.5rem' }}>
        <h3 style={{ fontSize: '0.95rem', margin: 0 }}>🤖 Automation ({autoJobs.length} jobs)</h3>
        <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>
          Batch jobs → review queues → apply. Toggles default off.
        </span>
      </div>
      {autoJobs.length === 0 ? (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No automation jobs registered.</p>
      ) : (
        <div className="card-grid">
          {autoJobs.map((j) => (
            <div key={j.name} className="card" style={{ padding: '0.7rem 0.9rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.4rem' }}>
                <strong style={{ fontSize: '0.8rem' }}>{j.name}</strong>
                <Chip label={j.enabled ? 'on' : 'off'} color={j.enabled ? '#10b981' : '#6b7280'} />
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                {j.description}
              </div>
              <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                {j.budget_kind ? `budget: ${j.budget_kind}` : 'no LLM cost'}
                {j.cap != null ? ` · cap: ${j.cap}` : ''}
              </div>
              <div style={{ marginTop: '0.15rem' }}>
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  disabled={autoRunning != null}
                  onClick={() => void runAutoJob(j.name)}
                >
                  {autoRunning === j.name ? 'Running…' : `▶ Run ${j.name}`}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Phase 10 (Ideas 91–100) ── */}
      <Phase10Panel onFlash={flash} />

      {/* ── Jobs ── */}
      <h3 style={{ margin: '1.25rem 0 0.5rem', fontSize: '0.95rem' }}>⚙️ Jobs</h3>
      {jobs.length === 0 ? (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No jobs yet — scan a source to get started.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {jobs.slice(0, 8).map((j) => (
            <div key={j.id} className="card" style={{ padding: '0.6rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Chip label={j.status} color={JOB_COLORS[j.status] ?? '#6b7280'} />
              <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{j.job_type}</span>
              <div style={{ flex: 1, minWidth: 120 }}>
                <div style={{ height: 6, borderRadius: 3, background: 'var(--muted, #e5e7eb)', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%', width: `${progress(j)}%`, background: JOB_COLORS[j.status] ?? '#3b82f6',
                      transition: 'width 0.4s',
                    }}
                  />
                </div>
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                {j.processed_items}/{j.total_items} · {fmt(j.finished_at ?? j.created_at)}
              </span>
              {j.summary && (
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                  +{j.summary.added ?? 0} · ~{j.summary.changed ?? 0} · dup {j.summary.duplicates_found ?? 0}
                </span>
              )}
              {j.error && <span style={{ fontSize: '0.72rem', color: '#ef4444' }} title={j.error}>⚠ error</span>}
            </div>
          ))}
        </div>
      )}

      {/* ── Document detail drawer ── */}
      {activeDoc && (
        <div className="modal-overlay" onClick={() => setActiveDoc(null)}>
          <div className="modal modal-lg" style={{ maxWidth: 720, maxHeight: '85vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">{activeDoc.title ?? activeDoc.path_rel}</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
              {activeDoc.doc_type.toUpperCase()} · {activeDoc.char_count.toLocaleString()} chars ·{' '}
              {activeDoc.frontmatter?.title ? `frontmatter title: ${String(activeDoc.frontmatter.title)} · ` : ''}
              hash {activeDoc.content_hash?.slice(0, 10)}…
            </p>

            {activeDoc.metadata?.tags && activeDoc.metadata.tags.length > 0 && (
              <div style={{ marginBottom: '0.75rem' }}>
                {activeDoc.metadata.tags.map((t) => (
                  <span key={t} style={{ marginRight: '0.3rem', fontSize: '0.72rem', background: 'var(--accent, #2563eb)18', color: 'var(--accent, #2563eb)', padding: '0.1rem 0.5rem', borderRadius: 999 }}>
                    #{t}
                  </span>
                ))}
              </div>
            )}

            {activeDoc.metadata?.arxiv_id && (
              <div style={{ marginBottom: '0.75rem', padding: '0.6rem 0.75rem', borderRadius: 8, background: '#f8fafc', border: '1px solid #e2e8f0', fontSize: '0.75rem' }}>
                <div style={{ fontWeight: 700 }}>📄 arXiv:{activeDoc.metadata.arxiv_id}</div>
                {activeDoc.metadata.authors?.length ? (
                  <div style={{ color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    {activeDoc.metadata.authors.join(', ')}
                  </div>
                ) : null}
                {activeDoc.metadata.abstract ? (
                  <div style={{ marginTop: '0.3rem', opacity: 0.9 }}>
                    {activeDoc.metadata.abstract.slice(0, 280)}{activeDoc.metadata.abstract.length > 280 ? '…' : ''}
                  </div>
                ) : null}
              </div>
            )}

            {/* ── Phase 4: note intelligence (Ideas 31–34, 38, 39) ── */}
            <SummaryPanel documentId={activeDoc.id} />
            <NoteActions documentId={activeDoc.id} onFlash={flash} />
            <ExplainPanel documentId={activeDoc.id} />
            <MindMapView documentId={activeDoc.id} />
            <QualityPanel documentId={activeDoc.id} />

            <h4 style={{ fontSize: '0.85rem', margin: '0.75rem 0 0.35rem' }}>
              🏷️ Tags{' '}
              <span style={{ fontWeight: 400, color: 'var(--text-secondary)' }}>({appliedTags.length} on note)</span>
            </h4>
            {appliedTags.length === 0 ? (
              <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>No tags on this note yet.</p>
            ) : (
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                {appliedTags.map((t) => (
                  <span key={`applied-${t.tag_id}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', background: 'var(--accent, #2563eb)18', color: 'var(--accent, #2563eb)', padding: '0.15rem 0.55rem', borderRadius: 999 }}>
                    #{t.name}
                    {t.provenance === 'manual' && (
                      <button type="button" className="btn btn-sm" style={{ padding: 0, minWidth: 0, fontSize: '0.68rem' }} title="Remove tag" onClick={() => void rejectTag(t.tag_id)}>✕</button>
                    )}
                  </span>
                ))}
              </div>
            )}

            {/* Add-tag input + course: quick chip (Second Brain dynamic courses) */}
            <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '0.5rem' }}>
              <input
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    void createTag();
                  }
                }}
                placeholder="Add a tag…"
                style={{ flex: 1, minWidth: 140, fontSize: '0.75rem', padding: '0.3rem 0.55rem', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg, #fff)', color: 'var(--text)' }}
              />
              <button type="button" className="btn btn-sm" onClick={() => void createTag()} disabled={!newTagName.trim()}>Add</button>
              <button
                type="button"
                className="btn btn-sm"
                title="Quick-tag this note as a course — it will appear on the Courses page after sync"
                onClick={() => setNewTagName((prev) => (prev.startsWith('course:') ? prev : `course:${prev}`))}
              >
                course: 💡
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', margin: '0.5rem 0 0.35rem' }}>
              <h4 style={{ fontSize: '0.85rem', margin: 0 }}>✨ Suggested tags</h4>
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                disabled={proposingTags}
                title="Re-run the AI tag proposal for this note and save the suggestions (browsing never triggers AI)"
                onClick={() => void proposeTagsWithAi()}
              >
                {proposingTags ? 'Suggesting…' : '✨ Suggest with AI'}
              </button>
            </div>
            {tagSuggestions.filter((t) => t.provenance !== 'rule').length === 0 ? (
              <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>No suggestions yet — click “Suggest with AI” to analyze this note.</p>
            ) : (
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                {tagSuggestions
                  .filter((t) => t.provenance !== 'rule')
                  .map((t) => (
                    <span key={t.tag_id} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', background: '#f59e0b22', color: '#b45309', padding: '0.15rem 0.55rem', borderRadius: 999 }}>
                      #{t.name}
                      <button type="button" className="btn btn-sm" style={{ padding: 0, minWidth: 0, fontSize: '0.68rem' }} title="Apply" onClick={() => void applyTag(t.tag_id)}>✓</button>
                      <button type="button" className="btn btn-sm" style={{ padding: 0, minWidth: 0, fontSize: '0.68rem' }} title="Dismiss" onClick={() => void rejectTag(t.tag_id)}>✕</button>
                    </span>
                  ))}
              </div>
            )}


            {/* ── Phase 8: connect suggestions (Idea 76) ── */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', margin: '1rem 0 0.35rem' }}>
              <h4 style={{ fontSize: '0.85rem', margin: 0 }}>🔌 Connect this note ({connectItems.length})</h4>
            </div>
            {connectItems.length === 0 ? (
              <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                No connect suggestions — ingest related notes and they'll appear here to link.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '0.5rem' }}>
                {connectItems.map((c) => (
                  <div key={c.document_id} className="card" style={{ padding: '0.55rem 0.8rem', display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: 140 }}>
                      <div style={{ fontSize: '0.76rem', fontWeight: 600 }}>{c.title}</div>
                      <div style={{ fontSize: '0.66rem', color: 'var(--text-secondary)' }}>
                        {c.reasons.join(' · ')}
                      </div>
                      {c.shared_concepts.length > 0 && (
                        <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', marginTop: '0.2rem' }}>
                          {c.shared_concepts.slice(0, 3).map((sc) => (
                            <span key={sc} style={{ fontSize: '0.62rem', background: '#10b98122', color: '#047857', padding: '0.05rem 0.4rem', borderRadius: 999 }}>
                              {sc}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      disabled={connectBusy}
                      onClick={() => void confirmConnect(c.document_id)}
                    >
                      Link
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* ── Phase 4: concept linking (Idea 37) ── */}
            <h4 style={{ fontSize: '0.85rem', margin: '1rem 0 0.35rem' }}>🔗 Links & concepts</h4>

            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', margin: '0.35rem 0 0.2rem' }}>
              CONCEPTS ({(links?.concepts ?? []).length})
            </div>
            {(links?.concepts ?? []).length === 0 ? (
              <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>No concepts linked to this note yet.</p>
            ) : (
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                {(links?.concepts ?? []).map((c) => (
                  <span key={c.concept_id} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', background: '#10b98122', color: '#047857', padding: '0.15rem 0.55rem', borderRadius: 999 }}>
                    {c.name}
                    <span style={{ opacity: 0.6, fontWeight: 400 }}>· {Math.round(c.weight * 100)}%</span>
                    {c.edge_id != null && (
                      <button
                        type="button"
                        className="btn btn-sm"
                        style={{ padding: 0, minWidth: 0, fontSize: '0.62rem' }}
                        title="Remove link"
                        onClick={() => void deleteEdge(c.edge_id as number)}
                      >
                        ✕
                      </button>
                    )}
                  </span>
                ))}
              </div>
            )}

            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', margin: '0.35rem 0 0.2rem' }}>
              LINKED NOTES ({(links?.related ?? []).length})
            </div>
            {(links?.related ?? []).length === 0 ? (
              <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>No linked notes yet — add one below (auto edges can be removed too).</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginBottom: '0.5rem' }}>
                {(links?.related ?? []).map((r) => (
                  <div key={`${r.id}-${r.relation}`} style={{ fontSize: '0.72rem', display: 'flex', justifyContent: 'space-between', gap: '0.5rem', alignItems: 'center' }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{r.title || `#${r.id}`}</span>
                    <span style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{r.relation}</span>
                    {r.edge_id != null && (
                      <button
                        type="button"
                        className="btn btn-sm btn-ghost"
                        style={{ padding: 0, minWidth: 0, fontSize: '0.62rem' }}
                        title="Remove link"
                        onClick={() => void deleteEdge(r.edge_id as number)}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div style={{ marginTop: '0.5rem' }}>
              <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.35rem' }}>
                <button
                  type="button"
                  className={`btn btn-sm ${linkKind === 'concept' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => {
                    setLinkKind('concept');
                    setLinkResults([]);
                  }}
                >
                  💡 Link to concept
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${linkKind === 'document' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => {
                    setLinkKind('document');
                    setLinkResults([]);
                  }}
                >
                  📄 Link to note
                </button>
              </div>
              <input
                className="form-input"
                style={{ width: '100%', fontSize: '0.75rem' }}
                placeholder={linkKind === 'concept' ? 'Type to search concepts…' : 'Type to search documents…'}
                value={linkQuery}
                onChange={(e) => void searchLinks(e.target.value)}
              />
              {linkResults.length > 0 && (
                <div style={{ marginTop: '0.3rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  {linkResults.map((r) => (
                    <button
                      key={`${r.kind}-${r.id}`}
                      type="button"
                      disabled={linkBusy}
                      className="btn btn-sm btn-ghost"
                      style={{ justifyContent: 'flex-start', textAlign: 'left' }}
                      onClick={() => void createLink(r)}
                    >
                      {r.kind === 'concept' ? '💡' : '📄'} {r.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* ── Phase 4: citations (Idea 36) ── */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', margin: '1.1rem 0 0.35rem' }}>
              <h4 style={{ fontSize: '0.85rem', margin: 0 }}>📚 Citations ({citations.length})</h4>
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => void exportBibtex()}>
                Export BibTeX
              </button>
            </div>
            {citations.length === 0 ? (
              <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                No citations found — they're parsed from PDF reference lists and @cite syntax on ingest.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '0.5rem' }}>
                {citations.map((c) => (
                  <div key={c.id} style={{ fontSize: '0.74rem', borderLeft: '3px solid var(--accent, #2563eb)', paddingLeft: '0.6rem' }}>
                    <span style={{ fontStyle: 'italic' }}>{c.title ?? c.raw_text ?? c.cite_key}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {c.authors?.length ? ` — ${c.authors.slice(0, 3).join(', ')}${c.authors.length > 3 ? ' et al.' : ''}` : ''}
                      {c.year ? ` (${c.year})` : ''}
                      {c.venue ? ` · ${c.venue}` : ''}
                    </span>
                    <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                      [{c.cite_key}]
                      {c.doi ? ` · doi:${c.doi}` : ''}
                      {c.arxiv_id ? ` · arXiv:${c.arxiv_id}` : ''}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <h4 style={{ fontSize: '0.85rem', margin: '0.75rem 0 0.35rem' }}>🧩 Chunks ({chunks.length})</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: 220, overflowY: 'auto' }}>
              {chunks.slice(0, 30).map((c) => (
                <div key={c.id} style={{ fontSize: '0.75rem', borderLeft: '3px solid var(--accent, #2563eb)', paddingLeft: '0.6rem' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.65rem' }}>
                    #{c.seq} {c.heading_path ?? '—'} · {c.token_estimate} tok · {c.char_start}–{c.char_end}
                  </div>
                  <div style={{ opacity: 0.85 }}>{c.content.slice(0, 160)}{c.content.length > 160 ? '…' : ''}</div>
                </div>
              ))}
              {chunks.length > 30 && <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>… and {chunks.length - 30} more</span>}
            </div>

            <h4 style={{ fontSize: '0.85rem', margin: '1rem 0 0.35rem' }}>🕘 Versions ({versions.length})</h4>
            {versions.length === 0 ? (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>No snapshots yet — they appear when a document changes.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                {versions.slice(0, 6).map((v) => (
                  <div key={v.id} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.75rem', flexWrap: 'wrap' }}>
                    <Chip label={`v${v.version_seq}`} color="#8b5cf6" />
                    <span style={{ color: 'var(--text-secondary)' }}>{fmt(v.created_at)}</span>
                    <button type="button" className="btn btn-sm btn-ghost" onClick={() => void restoreVersion(v.id)}>Restore</button>
                    <button
                      type="button"
                      className="btn btn-sm btn-ghost"
                      onClick={() => void loadDiff(v.version_seq, versions[0].version_seq)}
                    >
                      Diff vs latest
                    </button>
                  </div>
                ))}
              </div>
            )}

            {diff && (
              <>
                <h4 style={{ fontSize: '0.85rem', margin: '1rem 0 0.35rem' }}>
                  Diff v{diff.from_version} → v{diff.to_version} {diff.changed ? '' : '(identical)'}
                </h4>
                <pre
                  style={{
                    fontSize: '0.7rem', background: '#0f172a', color: '#e2e8f0', padding: '0.75rem',
                    borderRadius: 8, maxHeight: 240, overflow: 'auto', whiteSpace: 'pre-wrap',
                  }}
                >
                  {diff.diff || '(no differences)'}
                </pre>
              </>
            )}

            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => void reindexDoc(activeDoc.id)}>⟳ Reindex</button>
              <button type="button" className="btn btn-ghost" onClick={() => void removeDoc(activeDoc.id)}>🗑 Delete</button>
              <button type="button" className="btn btn-primary" onClick={() => setActiveDoc(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Add Source modal ── */}
      {showSource && (
        <div className="modal-overlay" onClick={() => setShowSource(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Register Knowledge Source</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Point at your Obsidian vault folder or any notes directory on this machine. It must exist on disk.
            </p>
            <label className="form-label">Name</label>
            <input className="form-input" style={{ width: '100%', marginBottom: '0.75rem' }} value={sourceName}
              onChange={(e) => setSourceName(e.target.value)} placeholder="My Obsidian Vault" />
            <label className="form-label">Root path</label>
            <input className="form-input" style={{ width: '100%', marginBottom: '1.25rem' }} value={sourcePath}
              onChange={(e) => setSourcePath(e.target.value)} placeholder="/home/me/Obsidian Vault" />
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowSource(false)}>Cancel</button>
              <button type="button" className="btn btn-primary" disabled={busy === 'source'} onClick={() => void addSource()}>
                {busy === 'source' ? 'Adding…' : 'Add Source'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Upload modal ── */}
      {showUpload && (
        <div className="modal-overlay" onClick={() => setShowUpload(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Upload Document</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              PDF, DOCX, TXT or MD (max 10 MB). Duplicate content is auto-deduplicated.
            </p>
            <input type="file" accept=".pdf,.docx,.txt,.md" onChange={uploadFile} disabled={busy === 'upload'} style={{ marginBottom: '1.25rem' }} />
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowUpload(false)} disabled={busy === 'upload'}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* ── arXiv import modal ── */}
      {showPaper && (
        <div className="modal-overlay" onClick={() => setShowPaper(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Import arXiv Paper</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Paste an arXiv ID or URL — metadata (title, authors, abstract) is fetched and ingested.
            </p>
            <input className="form-input" style={{ width: '100%', marginBottom: '1.25rem' }} value={arxivId}
              onChange={(e) => setArxivId(e.target.value)} placeholder="1706.03762 or https://arxiv.org/abs/1706.03762" />
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowPaper(false)}>Cancel</button>
              <button type="button" className="btn btn-primary" disabled={busy === 'paper'} onClick={() => void importPaper()}>
                {busy === 'paper' ? 'Importing…' : 'Import'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
