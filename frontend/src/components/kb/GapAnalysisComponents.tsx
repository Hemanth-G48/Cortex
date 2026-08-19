import type { GapHistorySnapshot, GapItem, GapPathItem, GapPathPhase } from '../../services/api';

const formatTime = (iso?: string | null) => {
  if (!iso) return 'never';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? 'unknown' : d.toLocaleString();
};

const levelColor = (level: string) => {
  switch (level) {
    case 'Mastered': return 'var(--success)';
    case 'Strong': return 'var(--info)';
    case 'Familiar': return 'var(--warning)';
    case 'Weak': return 'var(--warning)';
    case 'Not Found': return 'var(--danger)';
    case 'Prerequisite Missing': return 'var(--danger)';
    default: return 'var(--text-muted)';
  }
};

export const LevelBadge = ({ level }: { level: string }) => (
  <span
    className="gap-level-badge"
    style={{ color: levelColor(level), background: `${levelColor(level)}1a`, border: `1px solid ${levelColor(level)}55` }}
  >
    {level}
  </span>
);

export const PriorityBadge = ({ priority }: { priority?: string | null }) => {
  if (!priority) return null;
  const cls = priority === 'High' ? 'gap-pri-high' : priority === 'Medium' ? 'gap-pri-med' : 'gap-pri-low';
  return <span className={`gap-priority-badge ${cls}`}>{priority}</span>;
};

/** One expandable gap card: why, prerequisites, learn, practice, next, resources. */
export const GapCard = ({
  gap,
  open,
  onToggle,
  onOpenDoc,
  onCreateNote,
  noteBusy,
}: {
  gap: GapItem;
  open: boolean;
  onToggle: () => void;
  onOpenDoc: (id: number) => void;
  onCreateNote?: (gap: GapItem) => void;
  noteBusy?: boolean;
}) => (
  <div className={`gap-item-card ${open ? 'gap-item-open' : ''}`}>
    <div className="gap-item-head" onClick={onToggle} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onToggle(); }}>
      <span className="gap-item-caret">{open ? '▾' : '▸'}</span>
      <span className="gap-item-name">{gap.name}</span>
      <LevelBadge level={gap.level} />
      <PriorityBadge priority={gap.priority} />
      {(gap.sources ?? []).length > 0 && <span className="badge badge-info">📚 {(gap.sources ?? []).length}</span>}
    </div>
    {open && (
      <div className="gap-item-body">
        {gap.why && <p className="gap-why">💡 {gap.why}</p>}
        {(gap.prerequisites ?? []).length > 0 && (
          <div className="gap-field">
            <span className="gap-field-label">Prerequisites</span>
            <div className="gap-chip-wrap">
              {(gap.prerequisites ?? []).map((p) => (
                <span
                  key={p.name}
                  className={`gap-prereq-chip ${p.known ? 'gap-prereq-known' : ''}`}
                  title={`${p.level}${p.known ? ' — you have evidence' : ' — missing'}`}
                >
                  {p.name} {p.known ? '✓' : '⚠'}
                </span>
              ))}
            </div>
          </div>
        )}
        {(gap.learn ?? []).length > 0 && (
          <div className="gap-field">
            <span className="gap-field-label">Learn</span>
            <ol className="gap-steps">{(gap.learn ?? []).map((s, i) => <li key={i}>{s}</li>)}</ol>
          </div>
        )}
        {(gap.practice ?? []).length > 0 && (
          <div className="gap-field">
            <span className="gap-field-label">Practice</span>
            <ul className="gap-steps">{(gap.practice ?? []).map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
        )}
        {gap.next && (
          <div className="gap-field">
            <span className="gap-field-label">After this</span>
            <span className="gap-next-chip">→ {gap.next}</span>
          </div>
        )}
        {(gap.related_known ?? []).length > 0 && (
          <div className="gap-field">
            <span className="gap-field-label">Connects to what you know</span>
            <div className="gap-chip-wrap">
              {(gap.related_known ?? []).map((n) => (
                <span key={n} className="gap-related-chip">🔗 {n}</span>
              ))}
            </div>
          </div>
        )}
        <div className="gap-field">
          <span className="gap-field-label">Second Brain resources</span>
          {(gap.sources ?? []).length > 0 ? (
            <div className="gap-chip-wrap">
              {(gap.sources ?? []).map((s) => (
                <button key={s.document_id} type="button" className="btn btn-ghost btn-sm" onClick={() => onOpenDoc(s.document_id)}>
                  📄 {s.title}
                </button>
              ))}
            </div>
          ) : (
            <span className="gap-hint">No suitable Second Brain resource found — add a note or study material for this topic.</span>
          )}
        </div>
        {onCreateNote && (
          <div className="gap-field gap-field-actions">
            <button
              type="button"
              className="gap-create-note"
              disabled={noteBusy}
              onClick={() => onCreateNote(gap)}
              title="Draft a ready-to-edit capture note for this gap"
            >
              {noteBusy ? <span className="spinner spinner-sm" /> : '📝'} {noteBusy ? 'Drafting…' : 'Create note for this gap'}
            </button>
          </div>
        )}
      </div>
    )}
  </div>
);

/**
 * Learning path with per-item Second Brain document links.
 *
 * Each path item is a real gap: its `sources` are the actual documents that
 * mention the concept, so every item deep-links into the vault. The optional
 * "📝 Note" button drafts a capture note for the same gap.
 */
export const GapPathPhaseView = ({
  phases,
  onOpenDoc,
  onCreateNote,
  noteBusy,
}: {
  phases: GapPathPhase[];
  onOpenDoc: (id: number) => void;
  onCreateNote?: (item: GapPathItem) => void;
  noteBusy?: string | null;
}) => (
  <div className="gap-path">
    {phases.map((phase) => (
      <div key={phase.phase} className="gap-phase">
        <div className="gap-phase-label">{phase.title}</div>
        <div className="gap-phase-items">
          {(phase.items ?? []).map((item, i) => {
            const sources = item.sources ?? [];
            return (
              <div key={item.name} className="gap-phase-item-card">
                <span className="gap-phase-item" title={`${item.level}`}>
                  <span className="gap-phase-num">{i + 1}</span> {item.name}
                </span>
                {sources.length > 0 && (
                  <span className="gap-phase-docs">
                    {sources.map((s) => (
                      <button
                        key={s.document_id}
                        type="button"
                        className="gap-doc-link"
                        onClick={() => onOpenDoc(s.document_id)}
                        title={`Open “${s.title}” in Second Brain`}
                      >
                        📄 {s.title}
                      </button>
                    ))}
                  </span>
                )}
                {onCreateNote && (
                  <button
                    type="button"
                    className="gap-create-note"
                    disabled={noteBusy === item.name}
                    onClick={() => onCreateNote(item)}
                    title="Draft a ready-to-edit capture note for this gap"
                  >
                    {noteBusy === item.name ? 'Drafting…' : '📝 Note'}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    ))}
  </div>
);

/**
 * Gap Analysis history — a timeline of a scope's analyses over time.
 *
 * Snapshots come from the backend's compact log (``GapHistorySnapshot``). Each
 * entry shows when it ran, the gap/strength counts, and — compared against the
 * previous snapshot — the deltas: new gaps, resolved gaps, improved concepts
 * and regressed concepts. Rendered oldest → newest so you can watch the
 * subject's gaps shrink as you study.
 */
const LEVEL_RANK: Record<string, number> = {
  'Prerequisite Missing': 0,
  'Not Found': 1,
  Weak: 2,
  Familiar: 3,
  Strong: 4,
  Mastered: 5,
};

const levelRank = (level?: string | null) => LEVEL_RANK[level ?? ''] ?? -1;

const deltaStyle = (color: string) => ({
  color,
  background: `${color}1a`,
  border: `1px solid ${color}55`,
});

export const GapHistoryView = ({ snapshots, title }: { snapshots: GapHistorySnapshot[]; title?: string }) => {
  if (snapshots.length === 0) {
    return (
      <div className="gap-history" data-testid="gap-history-view">
        {title && <h4 className="gap-history-title">{title}</h4>}
        <p className="gap-hint">
          No past analyses recorded yet — run Gap Analysis at least twice to see how this scope's gaps
          change over time.
        </p>
      </div>
    );
  }

  return (
    <div className="gap-history" data-testid="gap-history-view">
      {title && <h4 className="gap-history-title">{title}</h4>}
      {snapshots.map((snap, i) => {
        const prev = i > 0 ? snapshots[i - 1] : null;
        const gaps = snap.gaps ?? [];
        const prevNames = new Set((prev?.gaps ?? []).map((g) => g.name));
        const curNames = new Set(gaps.map((g) => g.name));
        const newGaps = gaps.filter((g) => !prevNames.has(g.name));
        const resolved = (prev?.gaps ?? []).filter((g) => !curNames.has(g.name));
        const improved = prev
          ? gaps.filter((g) => {
              const p = (prev.gaps ?? []).find((pg) => pg.name === g.name);
              return p && levelRank(g.level) > levelRank(p.level);
            })
          : [];
        const curLevels = new Map(gaps.map((g) => [g.name, g]));
        const regressed = prev
          ? (prev.gaps ?? []).filter((p) => {
              const c = curLevels.get(p.name);
              return c && levelRank(c.level) < levelRank(p.level);
            })
          : [];
        const changed =
          i > 0 && (newGaps.length > 0 || resolved.length > 0 || improved.length > 0 || regressed.length > 0);
        return (
          <div key={snap.analyzed_at ?? i} className="gap-history-entry">
            <div className="gap-history-entry-head">
              <span className="gap-history-when">🕐 {formatTime(snap.analyzed_at)}</span>
              <span className="badge badge-muted">{snap.gap_count} gap{snap.gap_count === 1 ? '' : 's'}</span>
              <span className="badge badge-info">{snap.strength_count} strength{snap.strength_count === 1 ? '' : 's'}</span>
              {snap.coverage && (
                <span className="gap-meta">coverage {Math.round(snap.coverage.percent)}%</span>
              )}
              {snap.document_count != null && (
                <span className="gap-meta">{snap.document_count} doc{snap.document_count === 1 ? '' : 's'}</span>
              )}
              {snap.next && <span className="gap-meta">next: {snap.next}</span>}
            </div>
            {changed && (
              <div className="gap-history-diff">
                {newGaps.length > 0 && (
                  <span className="gap-history-delta" style={deltaStyle('var(--danger)')} title="Gaps that appeared in this analysis">
                    +{newGaps.length} new
                  </span>
                )}
                {resolved.length > 0 && (
                  <span className="gap-history-delta" style={deltaStyle('var(--success)')} title="Gaps no longer reported in this analysis">
                    ✓ {resolved.length} resolved
                  </span>
                )}
                {improved.length > 0 && (
                  <span className="gap-history-delta" style={deltaStyle('var(--info)')} title="Concepts whose evidence level improved">
                    ↑ {improved.length} improved
                  </span>
                )}
                {regressed.length > 0 && (
                  <span className="gap-history-delta" style={deltaStyle('var(--warning)')} title="Concepts whose evidence level weakened">
                    ↓ {regressed.length} regressed
                  </span>
                )}
              </div>
            )}
            {gaps.length > 0 && (
              <div className="gap-chip-wrap" style={{ marginTop: '0.4rem' }}>
                {gaps.slice(0, 12).map((g) => (
                  <span key={g.name} className="gap-prereq-chip" title={g.priority ? `Priority: ${g.priority}` : undefined}>
                    {g.name} <LevelBadge level={g.level ?? 'Not Found'} />
                  </span>
                ))}
                {gaps.length > 12 && <span className="gap-hint">+{gaps.length - 12} more</span>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

