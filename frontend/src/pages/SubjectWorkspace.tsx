import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { SkeletonCard } from '../components/shared/Skeleton';
import { endpoints } from '../services/api';
import type {
  DependencyGraph,
  KbAdaptation,
  RoadmapItem,
  SubjectProfile,
  TopicItem,
  TopicStatus,
  UnitMatchCandidate,
} from '../services/api';

const statusColor: Record<string, string> = {
  proposed: 'var(--warning)',
  confirmed: 'var(--success)',
  rejected: 'var(--danger)',
};

const diffColor = (d: string | null) =>
  d === 'E' ? 'var(--success)' : d === 'H' ? 'var(--danger)' : 'var(--warning)';

const bloomColor = (b: string | null) => {
  const map: Record<string, string> = {
    Remember: 'var(--info)',
    Understand: 'var(--success)',
    Apply: 'var(--warning)',
    Analyze: 'var(--danger)',
    Evaluate: '#a855f7',
    Create: 'var(--accent)',
  };
  return map[b ?? ''] ?? 'var(--text-muted)';
};

type Tab = 'overview' | 'topics' | 'dependencies' | 'roadmap';

/** Phase 5 subject workspace (Ideas 44–50): topics, unit match, DAG,
 * roadmap, difficulty/time, outcomes. */
export const SubjectWorkspace = () => {
  const { id } = useParams<{ id: string }>();
  const profileId = Number(id);

  const [profile, setProfile] = useState<SubjectProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('overview');
  const [busy, setBusy] = useState('');

  const refreshProfile = useCallback(() => {
    setLoading(true);
    setError('');
    endpoints.subjects
      .get(profileId)
      .then(setProfile)
      .catch(() => setError('Could not load this subject profile.'))
      .finally(() => setLoading(false));
  }, [profileId]);

  useEffect(() => {
    refreshProfile();
  }, [refreshProfile]);

  const confirmed = profile?.status === 'confirmed';

  return (
    <div className="fade-in" style={{ maxWidth: 980 }}>
      <Header title={profile?.parsed?.title ?? 'Subject Workspace'} />

      <nav aria-label="Breadcrumb" style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem', display: 'flex', gap: '0.35rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <Link to="/subjects" style={{ color: 'var(--accent)', textDecoration: 'none' }}>Subjects</Link>
        <span>/</span>
        <span>{profile?.parsed?.title ?? `#${profileId}`}</span>
      </nav>

      {loading ? (
        <SkeletonCard />
      ) : error || !profile ? (
        <EmptyState icon="📘" title="Subject not found" message={error || 'This profile may have been removed.'}
          action={<Link className="btn btn-primary" to="/subjects">Back to subjects</Link>} />
      ) : (
        <>
          {/* Header card */}
          <div className="card" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>{profile.parsed?.title ?? 'Untitled Subject'}</span>
                  <span className="badge" style={{ color: statusColor[profile.status], background: `${statusColor[profile.status]}22`, textTransform: 'capitalize' }}>{profile.status}</span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.4rem' }}>
                  {profile.semester && <span className="badge" style={{ color: 'var(--info)' }}>🗓 {profile.semester}</span>}
                  {profile.parsed?.credits != null && <span>{profile.parsed.credits} credits</span>}
                  <span>{profile.parsed?.units.length ?? 0} units</span>
                  <span>{profile.topics_count} topics</span>
                </div>
              </div>
              <Link className="btn btn-ghost btn-sm" to="/subjects">← All subjects</Link>
            </div>
            {profile.parsed?.grading && (
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.75rem', lineHeight: 1.5 }}>{profile.parsed.grading}</p>
            )}
          </div>

          {!confirmed ? (
            <div className="card" style={{ padding: '1.25rem', textAlign: 'center' }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '0.5rem' }}>⏳</div>
              <p style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.35rem' }}>This subject is still a proposal</p>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                Confirm it from the import page to create the curriculum rows and unlock topics, dependencies, and roadmaps.
              </p>
              <Link className="btn btn-primary btn-sm" to="/import">Review & confirm →</Link>
            </div>
          ) : (
            <>
              {/* Tabs */}
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '1.25rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.6rem' }}>
                {(
                  [
                    ['overview', '📋 Overview'],
                    ['topics', '🧩 Topics'],
                    ['dependencies', '🕸 Dependencies'],
                    ['roadmap', '🗺 Roadmap'],
                  ] as [Tab, string][]
                ).map(([t, label]) => (
                  <button
                    key={t}
                    type="button"
                    className="btn btn-sm"
                    style={tab === t ? { background: 'var(--accent)', color: '#0b0e14', border: 'none' } : {}}
                    onClick={() => setTab(t)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {tab === 'overview' && (
                <OverviewTab profile={profile} busy={busy} setBusy={setBusy} />
              )}
              {tab === 'topics' && (
                <TopicsTab profile={profile} busy={busy} setBusy={setBusy} />
              )}
              {tab === 'dependencies' && (
                <DependenciesTab profile={profile} busy={busy} setBusy={setBusy} />
              )}
              {tab === 'roadmap' && (
                <RoadmapTab profile={profile} busy={busy} setBusy={setBusy} />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Overview: parsed syllabus + unit-match confirmation (Idea 45)       */
/* ------------------------------------------------------------------ */

function OverviewTab({
  profile,
  busy,
  setBusy,
}: {
  profile: SubjectProfile;
  busy: string;
  setBusy: (b: string) => void;
}) {
  const [matches, setMatches] = useState<UnitMatchCandidate[] | null>(null);
  const [useEmbeddings, setUseEmbeddings] = useState(false);
  const [mapping, setMapping] = useState<Record<string, number | null>>({});
  const [assigned, setAssigned] = useState<number | null>(null);
  const [note, setNote] = useState('');

  const loadMatches = (emb = useEmbeddings) => {
    setBusy('match');
    setNote('');
    endpoints.subjects.matchUnits
      .list(profile.id, emb)
      .then((r) => {
        setMatches(r.items);
        setMapping(Object.fromEntries(r.items.map((m) => [m.title, m.candidate_unit_id])));
      })
      .catch((e) => setNote(e instanceof Error ? e.message : 'Could not load unit matches.'))
      .finally(() => setBusy(''));
  };

  const confirmMapping = async () => {
    setBusy('match');
    try {
      const r = await endpoints.subjects.matchUnits.confirm(profile.id, mapping);
      setAssigned(r.topics_assigned);
      setNote(`✅ ${r.topics_assigned} topics linked to units.`);
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not save the mapping.');
    }
    setBusy('');
  };

  return (
    <div>
      {/* Parsed units */}
      <div className="page-section">
        <h2>Parsed Units</h2>
        {(profile.parsed?.units ?? []).length === 0 ? (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No units were parsed from this syllabus.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {profile.parsed?.units.map((unit, i) => (
              <div key={i} className="card" style={{ padding: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.6rem' }}>
                  <span className="badge" style={{ background: 'var(--bg-hover)' }}>Unit {i + 1}</span>
                  <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{unit.title}</span>
                </div>
                {unit.description && <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>{unit.description}</p>}
                {unit.topics.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                    {unit.topics.map((t, j) => (
                      <span key={j} className="badge" style={{ color: 'var(--accent)', background: 'var(--accent)14' }}>{t.name}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Unit matching */}
      <div className="page-section">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
          <h2 style={{ margin: 0 }}>Match Units</h2>
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy === 'match'}
            onClick={() => { setUseEmbeddings(false); loadMatches(false); }}
          >
            {busy === 'match' ? '…' : 'Find matches'}
          </button>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={useEmbeddings}
              onChange={(e) => { setUseEmbeddings(e.target.checked); loadMatches(e.target.checked); }}
            />
            Use embeddings
          </label>
        </div>

        {note && <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>{note}</p>}

        {matches && matches.length > 0 && (
          <div className="card" style={{ padding: '1rem', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '0.4rem 0.5rem' }}>Parsed unit</th>
                  <th style={{ padding: '0.4rem 0.5rem' }}>Match to existing unit</th>
                  <th style={{ padding: '0.4rem 0.5rem' }}>Score</th>
                </tr>
              </thead>
              <tbody>
                {matches.map((m) => (
                  <tr key={m.title} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '0.5rem', fontWeight: 600 }}>{m.title}</td>
                    <td style={{ padding: '0.5rem' }}>
                      <select
                        value={mapping[m.title] ?? ''}
                        onChange={(e) => {
                          const v = e.target.value === '' ? null : Number(e.target.value);
                          setMapping((prev) => ({ ...prev, [m.title]: v }));
                        }}
                        style={{ width: '100%', maxWidth: 260 }}
                      >
                        <option value="">＋ Create new…</option>
                        {profile.units_count > 0 && matches
                          .map((x) => x.candidate_unit_id)
                          .filter((v, i, arr): v is number => !!v && arr.indexOf(v) === i)
                          .map((uid) => (
                            <option key={uid} value={uid}>
                              {matches.find((x) => x.candidate_unit_id === uid)?.candidate_title ?? `Unit #${uid}`}
                            </option>
                          ))}
                      </select>
                    </td>
                    <td style={{ padding: '0.5rem' }}>
                      {m.match_type === 'none' ? (
                        <span className="badge" style={{ color: 'var(--text-muted)' }}>new</span>
                      ) : (
                        <span className="badge" style={{ color: m.score >= 0.8 ? 'var(--success)' : 'var(--warning)' }}>
                          {Math.round(m.score * 100)}% {m.match_type === 'name' ? '' : '· emb'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ marginTop: '0.9rem' }}>
              <button type="button" className="btn btn-primary btn-sm" onClick={() => void confirmMapping()} disabled={busy === 'match'}>
                Save mapping
              </button>
              {assigned !== null && <span style={{ fontSize: '0.78rem', color: 'var(--success)', marginLeft: '0.75rem' }}>{assigned} topics assigned</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Topics: review grid + difficulty/time + outcomes (Ideas 44,48–50)   */
/* ------------------------------------------------------------------ */

function TopicsTab({ profile, busy, setBusy }: { profile: SubjectProfile; busy: string; setBusy: (b: string) => void }) {
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [filter, setFilter] = useState<TopicStatus | 'all'>('all');
  const [pacing, setPacing] = useState(1.0);
  const [note, setNote] = useState('');

  const load = useCallback(
    (st: TopicStatus | 'all' = filter) => {
      setBusy('topics');
      endpoints.subjects.topics
        .list(profile.id, st === 'all' ? undefined : st)
        .then((r) => setTopics(r.items))
        .catch(() => setTopics([]))
        .finally(() => setBusy(''));
      endpoints.subjects
        .timeBudget(profile.id)
        .then((r) => setPacing(r.pacing_multiplier))
        .catch(() => {});
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [profile.id, filter],
  );

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  const generate = async () => {
    setBusy('gen');
    setNote('');
    try {
      const r = await endpoints.subjects.topics.generate(profile.id);
      setNote(`Generated ${r.generated} topics${r.fallback ? ' (deterministic fallback — AI off or budget used)' : ''}.`);
      load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not generate topics.');
    }
    setBusy('');
  };

  const act = async (fn: () => Promise<unknown>, msg: string) => {
    setBusy('topic');
    try {
      await fn();
      load();
      setNote(msg);
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Action failed.');
    }
    setBusy('');
  };

  const mergeInto = async (from: TopicItem, intoId: number) => {
    setBusy('topic');
    setNote('');
    try {
      await endpoints.subjects.topics.merge(profile.id, from.id, intoId);
      setNote(`"${from.name}" merged into its target.`);
      load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not merge topics.');
    }
    setBusy('');
  };

  const expandOutcomes = async (t: TopicItem) => {
    setBusy('outcome');
    setNote('');
    try {
      await endpoints.subjects.outcomes.expand(t.id);
      setNote(`Expanded outcomes for "${t.name}".`);
      load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not expand outcomes.');
    }
    setBusy('');
  };

  const setDifficulty = (t: TopicItem) => (d: string) =>
    act(() => endpoints.subjects.topics.patch(t.id, { difficulty: d }), `Difficulty for "${t.name}" set to ${d}.`);

  const completeOutcome = async (t: TopicItem, index: number) => {
    setBusy('outcome');
    try {
      await endpoints.subjects.outcomes.complete(t.id, index);
      load();
    } finally {
      setBusy('');
    }
  };

  const addOutcome = async (t: TopicItem, text: string) => {
    if (!text.trim()) return;
    setBusy('outcome');
    try {
      await endpoints.subjects.outcomes.add(t.id, text.trim());
      load();
    } finally {
      setBusy('');
    }
  };

  const savePacing = async () => {
    setBusy('pacing');
    try {
      await endpoints.subjects.pacing(pacing);
      load();
    } finally {
      setBusy('');
    }
  };

  const pending = topics.filter((t) => t.status === 'pending').length;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => void generate()} disabled={busy === 'gen' || busy === 'topics'}>
          {busy === 'gen' ? 'Generating…' : '✨ Generate Topics from Syllabus'}
        </button>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{topics.length} topics · {pending} pending review</span>
        <div style={{ flex: 1 }} />
        <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          Pacing ×
          <input
            type="number"
            step={0.1}
            min={0.1}
            max={5}
            value={pacing}
            onChange={(e) => setPacing(Number(e.target.value))}
            style={{ width: 64 }}
          />
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void savePacing()} disabled={busy === 'pacing'}>Save</button>
        </label>
      </div>

      {note && <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>{note}</p>}

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        {(['all', 'pending', 'confirmed', 'merged', 'rejected'] as const).map((st) => (
          <button
            key={st}
            type="button"
            className="badge"
            style={{ cursor: 'pointer', border: 'none', background: filter === st ? 'var(--accent)' : 'var(--bg-hover)', color: filter === st ? '#0b0e14' : 'var(--text-secondary)', padding: '0.3rem 0.65rem', textTransform: 'capitalize' }}
            onClick={() => { setFilter(st); load(st); }}
          >
            {st}
          </button>
        ))}
      </div>

      {topics.length === 0 ? (
        <EmptyState icon="🧩" title="No topics yet" message="Generate topics from the parsed syllabus, then review each one." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {topics.map((t) => (
            <TopicCard
              key={t.id}
              topic={t}
              busy={busy}
              mergeTargets={topics.filter((x) => x.id !== t.id)}
              onConfirm={() => act(() => endpoints.subjects.topics.confirm(profile.id, t.id), `"${t.name}" confirmed.`)}
              onReject={() => act(() => endpoints.subjects.topics.reject(profile.id, t.id), `"${t.name}" rejected.`)}
              onMerge={(intoId) => void mergeInto(t, intoId)}
              onDifficulty={setDifficulty(t)}
              onExpandOutcomes={() => void expandOutcomes(t)}
              onCompleteOutcome={(i) => void completeOutcome(t, i)}
              onAddOutcome={(text) => void addOutcome(t, text)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TopicCard({
  topic,
  busy,
  mergeTargets,
  onConfirm,
  onReject,
  onMerge,
  onDifficulty,
  onExpandOutcomes,
  onCompleteOutcome,
  onAddOutcome,
}: {
  topic: TopicItem;
  busy: string;
  mergeTargets: TopicItem[];
  onConfirm: () => void;
  onReject: () => void;
  onMerge: (intoTopicId: number) => void;
  onDifficulty: (d: string) => void;
  onExpandOutcomes: () => void;
  onCompleteOutcome: (index: number) => void;
  onAddOutcome: (text: string) => void;
}) {
  const [newOutcome, setNewOutcome] = useState('');
  const [mergeInto, setMergeInto] = useState('');
  const done = topic.outcomes.filter((o) => o.status === 'done').length;
  const total = topic.outcomes.length;

  return (
    <div className="card" style={{ padding: '1rem 1.15rem' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 700, fontSize: '0.92rem' }}>{topic.name}</span>
            {topic.bloom_level && (
              <span className="badge" style={{ color: bloomColor(topic.bloom_level), background: `${bloomColor(topic.bloom_level)}18` }}>
                {topic.bloom_level}
              </span>
            )}
            <span
              className="badge"
              style={{
                color: statusColor[topic.status] ?? 'var(--text-muted)',
                background: `${statusColor[topic.status] ?? 'var(--text-muted)'}18`,
                textTransform: 'capitalize',
              }}
            >
              {topic.status}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.45rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            {/* Difficulty badge + inline edit */}
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <span className="badge" style={{ color: diffColor(topic.difficulty), background: `${diffColor(topic.difficulty)}1a`, fontWeight: 700 }} title={`confidence ${Math.round((topic.difficulty_confidence ?? 0) * 100)}%`}>
                {topic.difficulty ?? '?'}
              </span>
              {(['E', 'M', 'H'] as const).map((d) => (
                <button
                  key={d}
                  type="button"
                  className="btn btn-ghost btn-sm"
                  style={{ padding: '0.1rem 0.4rem', fontSize: '0.68rem', minWidth: 0 }}
                  disabled={busy === 'topic'}
                  onClick={() => onDifficulty(d)}
                  aria-label={`Set difficulty to ${d === 'E' ? 'Easy' : d === 'M' ? 'Medium' : 'Hard'}`}
                  title={`Set difficulty to ${d === 'E' ? 'Easy' : d === 'M' ? 'Medium' : 'Hard'}`}
                >
                  {d}
                </button>
              ))}
            </span>
            <span>·</span>
            <span title="First pass / review / mastery">
              ⏱ {topic.first_pass_mins ?? '—'}m · {topic.review_mins ?? '—'}m · {topic.mastery_mins ?? '—'}m
            </span>
            {total > 0 && (
              <>
                <span>·</span>
                <span style={{ color: done === total ? 'var(--success)' : 'var(--text-secondary)' }}>
                  🎯 {done}/{total} outcomes
                </span>
              </>
            )}
          </div>

          {/* Outcomes checklist */}
          {total > 0 && (
            <div style={{ marginTop: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {topic.outcomes.map((o, i) => (
                <label key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.78rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={o.status === 'done'}
                    onChange={() => onCompleteOutcome(i)}
                    disabled={busy === 'outcome'}
                    style={{ marginTop: '0.15rem' }}
                  />
                  <span style={o.status === 'done' ? { textDecoration: 'line-through', color: 'var(--text-muted)' } : {}}>{o.text}</span>
                </label>
              ))}
            </div>
          )}

          {/* Add outcome + LLM expansion (Idea 50, phrase 93) */}
          <form
            style={{ display: 'flex', gap: '0.4rem', marginTop: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}
            onSubmit={(e) => {
              e.preventDefault();
              onAddOutcome(newOutcome);
              setNewOutcome('');
            }}
          >
            <input
              value={newOutcome}
              onChange={(e) => setNewOutcome(e.target.value)}
              placeholder="Add a learning outcome…"
              style={{ flex: 1, maxWidth: 300, fontSize: '0.78rem' }}
            />
            <button type="submit" className="btn btn-ghost btn-sm" disabled={!newOutcome.trim()}>Add</button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={onExpandOutcomes} disabled={busy === 'outcome' || total === 0}>
              ✨ Expand
            </button>
          </form>
        </div>

        {/* Review actions: confirm / merge / reject (phrase 39) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', alignItems: 'flex-end' }}>
          {topic.status === 'pending' && (
            <>
              <button type="button" className="btn btn-primary btn-sm" onClick={onConfirm} disabled={busy === 'topic'}>✓ Confirm</button>
              <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
                <select
                  value={mergeInto}
                  onChange={(e) => setMergeInto(e.target.value)}
                  aria-label="Merge this topic into…"
                  style={{ maxWidth: 130, fontSize: '0.72rem' }}
                >
                  <option value="">merge into…</option>
                  {mergeTargets.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={busy === 'topic' || !mergeInto}
                  onClick={() => onMerge(Number(mergeInto))}
                >
                  Merge
                </button>
              </div>
              <button type="button" className="btn btn-ghost btn-sm" onClick={onReject} disabled={busy === 'topic'}>✕ Reject</button>
            </>
          )}
          {topic.status === 'confirmed' && <span className="badge" style={{ color: 'var(--success)' }}>✓ kept</span>}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Dependencies: topic DAG editor (Idea 46)                            */
/* ------------------------------------------------------------------ */

function DependenciesTab({ profile, busy, setBusy }: { profile: SubjectProfile; busy: string; setBusy: (b: string) => void }) {
  const [graph, setGraph] = useState<DependencyGraph | null>(null);
  const [note, setNote] = useState('');
  const [prereq, setPrereq] = useState('');
  const [postreq, setPostreq] = useState('');

  const load = useCallback(() => {
    setBusy('deps');
    endpoints.subjects.dependencies
      .get(profile.id)
      .then(setGraph)
      .catch(() => setGraph(null))
      .finally(() => setBusy(''));
  }, [profile.id, setBusy]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  const seed = async () => {
    setBusy('deps');
    setNote('');
    try {
      const r = await endpoints.subjects.dependencies.generate(profile.id);
      setNote(`Seeded ${r.created} dependency edge${r.created === 1 ? '' : 's'}.`);
      load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not seed dependencies.');
    }
  };

  const add = async () => {
    if (!prereq || !postreq) return;
    setBusy('deps');
    setNote('');
    try {
      await endpoints.subjects.dependencies.add(profile.id, Number(prereq), Number(postreq));
      setNote('Edge added.');
      load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not add edge.');
    }
  };

  const remove = async (depId: number) => {
    setBusy('deps');
    try {
      await endpoints.subjects.dependencies.remove(depId);
      load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not remove edge.');
    }
  };

  const topics = graph?.topics ?? [];
  const byId = new Map(topics.map((t) => [t.id, t.name]));
  // Group edges by the topic that depends on the prereq (postreq needs prereq).
  const edges = graph?.edges ?? [];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => void seed()} disabled={busy === 'deps' || topics.length === 0}>
          ✨ Seed from syllabus
        </button>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{topics.length} topics · {edges.length} edges</span>
      </div>

      {note && <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>{note}</p>}

      {/* Manual add */}
      <div className="card" style={{ padding: '1rem', marginBottom: '1rem', display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Add dependency:</span>
        <select value={prereq} onChange={(e) => setPrereq(e.target.value)} style={{ maxWidth: 220 }}>
          <option value="">prerequisite…</option>
          {topics.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <span style={{ color: 'var(--text-muted)' }}>→</span>
        <select value={postreq} onChange={(e) => setPostreq(e.target.value)} style={{ maxWidth: 220 }}>
          <option value="">depends on it…</option>
          {topics.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <button type="button" className="btn btn-sm" onClick={() => void add()} disabled={busy === 'deps' || !prereq || !postreq}>
          Add
        </button>
      </div>

      {edges.length === 0 ? (
        <EmptyState icon="🕸" title="No dependencies yet" message="Seed from the syllabus or add edges manually. Cycles are rejected automatically." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {edges.map((e) => (
            <div key={e.id} className="card" style={{ padding: '0.6rem 0.9rem', display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.82rem' }}>
              <span style={{ fontWeight: 600 }}>{byId.get(e.prereq_topic_id) ?? `#${e.prereq_topic_id}`}</span>
              <span style={{ color: 'var(--text-muted)' }}>→</span>
              <span style={{ fontWeight: 600 }}>{byId.get(e.postreq_topic_id) ?? `#${e.postreq_topic_id}`}</span>
              <span className="badge" style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{e.provenance}</span>
              <div style={{ flex: 1 }} />
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => void remove(e.id)}
                disabled={busy === 'deps'}
                aria-label={`Remove dependency ${byId.get(e.prereq_topic_id) ?? e.prereq_topic_id} → ${byId.get(e.postreq_topic_id) ?? e.postreq_topic_id}`}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Roadmap: versioned week-by-week plan (Idea 47)                       */
/* ------------------------------------------------------------------ */

function RoadmapTab({ profile, busy, setBusy }: { profile: SubjectProfile; busy: string; setBusy: (b: string) => void }) {
  const [roadmap, setRoadmap] = useState<RoadmapItem | null>(null);
  const [budget, setBudget] = useState(300);
  const [deadline, setDeadline] = useState('');
  const [note, setNote] = useState('');
  // Phase 8 (Idea 80): adaptive recompute + plan diff banner
  const [adaptation, setAdaptation] = useState<KbAdaptation | null>(null);

  const load = useCallback(() => {
    endpoints.subjects.roadmap
      .get(profile.id)
      .then((r) => {
        setRoadmap(r.roadmap);
        if (r.roadmap) setBudget(r.roadmap.plan.weekly_budget_minutes ?? 300);
      })
      .catch(() => setRoadmap(null));
  }, [profile.id]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  const generate = async () => {
    setBusy('roadmap');
    setNote('');
    try {
      const r = await endpoints.subjects.roadmap.generate(profile.id, {
        weekly_budget: budget || null,
        deadline: deadline || null,
      });
      setRoadmap(r.roadmap);
      setNote(`Roadmap v${r.roadmap.version} generated.`);
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not generate roadmap.');
    }
    setBusy('');
  };

  // Phase 8 (Idea 80): adapt to mastery + due reviews + concept gaps.
  const adapt = async () => {
    setBusy('adapt');
    setNote('');
    try {
      const r = await endpoints.kb.adapt.roadmap(profile.id, {
        weekly_budget: budget || null,
        deadline: deadline || null,
      });
      setAdaptation(r.adaptation);
      const d = r.adaptation.diff;
      setNote(
        `Plan adapted — v${r.adaptation.version}: ${d.reason}`,
      );
      load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not adapt roadmap.');
    }
    setBusy('');
  };

  const weeks = roadmap?.plan.weeks ?? [];

  return (
    <div>
      <div className="card" style={{ padding: '1rem', marginBottom: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <label style={{ fontSize: '0.75rem' }}>
          <span style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Weekly budget (minutes)</span>
          <input type="number" min={60} max={6000} step={30} value={budget} onChange={(e) => setBudget(Number(e.target.value))} style={{ width: 130 }} />
        </label>
        <label style={{ fontSize: '0.75rem' }}>
          <span style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Deadline (optional)</span>
          <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} style={{ width: 150 }} />
        </label>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => void generate()} disabled={busy === 'roadmap'}>
          {busy === 'roadmap' ? 'Generating…' : roadmap ? '↻ Regenerate (new version)' : '🗺 Generate Roadmap'}
        </button>
        <button type="button" className="btn btn-sm" style={{ border: '1px solid var(--accent)', color: 'var(--accent)' }} onClick={() => void adapt()} disabled={busy === 'adapt' || !roadmap}>
          {busy === 'adapt' ? 'Adapting…' : '✨ Adapt to mastery'}
        </button>
        {roadmap && <span className="badge" style={{ color: 'var(--info)' }}>v{roadmap.version}</span>}
      </div>

      {/* Phase 8 (Idea 80, phrase 99): "Plan updated" banner with the diff */}
      {adaptation && (
        <div
          className="card"
          style={{
            padding: '0.9rem 1rem', marginBottom: '1rem',
            borderLeft: '3px solid var(--accent)',
            background: 'var(--accent)0f',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <strong style={{ fontSize: '0.82rem' }}>🔄 Plan updated (v{adaptation.version})</strong>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              +{adaptation.diff.added_reviews} review{adaptation.diff.added_reviews === 1 ? '' : 's'}
              {adaptation.diff.removed_topics.length > 0 ? ` · −${adaptation.diff.removed_topics.length} topic${adaptation.diff.removed_topics.length === 1 ? '' : 's'}` : ''}
              {adaptation.diff.reordered.length > 0 ? ` · ${adaptation.diff.reordered.length} reordered` : ''}
            </span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            {adaptation.diff.reasons.join(' · ')}
          </div>
          <button type="button" className="btn btn-ghost btn-sm" style={{ marginTop: '0.4rem' }} onClick={() => setAdaptation(null)}>
            Got it
          </button>
        </div>
      )}

      {note && <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>{note}</p>}

      {weeks.length === 0 ? (
        <EmptyState icon="🗺" title="No roadmap yet" message="Generate a week-by-week plan from the topic dependency graph and time estimates." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {weeks.map((w) => (
            <div key={w.week} className="card" style={{ padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem' }}>
                <span className="badge" style={{ background: 'var(--accent)', color: '#0b0e14', fontWeight: 700 }}>Week {w.week}</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>≈ {w.est_mins} min</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                {w.topics.map((name, i) => (
                  <label key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                    <input type="checkbox" />
                    <span>{name}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default SubjectWorkspace;
