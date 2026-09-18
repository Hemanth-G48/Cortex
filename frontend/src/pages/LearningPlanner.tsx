import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { confirmDelete } from '../utils/confirm';
import { endpoints } from '../services/api';
import type {
  GapGoalInfo,
  LearningCrawlReport,
  LearningPlanDetail,
  LearningPlanSummary,
  LearningReverifyReport,
  LearningSchedule,
  LearningSourcePath,
  LearningSourceResource,
  LearningTask,
  LearningTopic,
  PlanSessionState,
  PortswiggerSessionStatus,
} from '../services/api';

const styles = {
  card: { padding: '1rem 1.15rem', marginBottom: '0.9rem' },
  sub: { fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.05em' },
  row: {
    display: 'flex', alignItems: 'center', gap: '0.55rem', padding: '0.45rem 0.15rem',
    borderBottom: '1px solid var(--border)', fontSize: '0.8rem',
  },
  chip: {
    fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: '0.04em',
    padding: '0.1rem 0.45rem', borderRadius: 999, flexShrink: 0,
  },
  input: {
    fontSize: '0.8rem', padding: '0.4rem 0.6rem', borderRadius: 8, border: '1px solid var(--border)',
    background: 'var(--bg)', color: 'var(--text-primary)', outline: 'none', width: '100%',
  },
  textarea: {
    fontSize: '0.8rem', padding: '0.4rem 0.6rem', borderRadius: 8, border: '1px solid var(--border)',
    background: 'var(--bg)', color: 'var(--text-primary)', outline: 'none', width: '100%',
    fontFamily: 'monospace', minHeight: 88, resize: 'vertical' as const,
  },
  label: { fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: '0.05em', marginBottom: '0.3rem', display: 'block' },
  empty: { fontSize: '0.75rem', color: 'var(--text-muted)', padding: '0.4rem 0' },
};

const STATUS_STYLE: Record<string, { color: string; bg: string; label: string }> = {
  known: { color: 'var(--success)', bg: 'var(--success-muted)', label: '✓ known' },
  partial: { color: 'var(--warning)', bg: 'var(--warning-muted)', label: '◐ partial' },
  unknown: { color: 'var(--info)', bg: 'var(--info-muted)', label: '⬜ to learn' },
  advanced_unknown: { color: 'var(--danger)', bg: 'var(--danger-muted)', label: '⬜ advanced' },
};

const DIFFICULTY_COLOR: Record<string, string> = {
  beginner: 'var(--success)',
  intermediate: 'var(--warning)',
  advanced: 'var(--danger)',
};

// How the learner wants to study (roadmap → study schedule modes).
const SCHEDULE_MODES: { key: string; label: string; hint: string }[] = [
  { key: 'daily_hours', label: '⏱ Daily hours', hint: 'Pack tasks into days up to a fixed number of hours' },
  { key: 'modules_per_day', label: '📚 Modules per day', hint: 'A fixed number of tasks/modules per day' },
  { key: 'time_slots', label: '🕗 Fixed time slots', hint: 'Study at the same daily times (e.g. 07:00-08:00)' },
  { key: 'hybrid', label: '🧩 Both', hint: 'An hours budget AND a per-day module cap' },
  { key: 'ai_instruction', label: '✍️ Tell AI', hint: 'Describe your routine in your own words and let the AI schedule it' },
];

const fmtMins = (m: number) => {
  if (m >= 60) return `${(m / 60).toFixed(m % 60 === 0 ? 0 : 1)}h`;
  return `${m}m`;
};

// Honest crawl states — "CRAWLED" is only ever shown when the request actually
// succeeded and content was extracted (see backend source_crawler).
const CRAWL_STATUS: Record<string, { color: string; bg: string; label: string }> = {
  crawled: { color: 'var(--success)', bg: 'var(--success-muted)', label: 'CRAWLED' },
  discovered: { color: 'var(--info)', bg: 'var(--info-muted)', label: 'DISCOVERED' },
  auth_required: { color: 'var(--warning)', bg: 'var(--warning-muted)', label: 'SIGN-IN REQUIRED' },
  extraction_failed: { color: 'var(--warning)', bg: 'var(--warning-muted)', label: 'EXTRACTION FAILED' },
  http_error: { color: 'var(--danger)', bg: 'var(--danger-muted)', label: 'HTTP ERROR' },
  not_found: { color: 'var(--danger)', bg: 'var(--danger-muted)', label: 'NOT FOUND' },
  ai_generated: { color: 'var(--accent)', bg: 'var(--accent-muted)', label: 'AI-GENERATED' },
};

const crawlChip = (status?: string | null) => {
  const s = CRAWL_STATUS[status ?? ''] ?? CRAWL_STATUS.discovered;
  return (
    <span style={{ ...styles.chip, background: s.bg, color: s.color }} title={status === 'auth_required' ? 'URL discovered on the site; fetching it bounces to sign-in — open it in your browser to access' : undefined}>
      {s.label}
    </span>
  );
};

const parseResourceLines = (raw: string): { label?: string; url?: string }[] => {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split('|').map((s) => s.trim());
      if (parts.length >= 2 && parts[1]) return { label: parts[0] || undefined, url: parts[1] };
      if (parts[0].startsWith('http://') || parts[0].startsWith('https://')) return { url: parts[0] };
      return { label: parts[0] };
    });
};

const splitList = (raw: string) => raw.split(',').map((s) => s.trim()).filter(Boolean);

const fmtDate = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString() : '—');

export const LearningPlanner = () => {
  // Form state
  const [goal, setGoal] = useState('');
  const [description, setDescription] = useState('');
  const [resourcesRaw, setResourcesRaw] = useState('');
  const [knownRaw, setKnownRaw] = useState('');
  const [unknownRaw, setUnknownRaw] = useState('');
  const [goalKey, setGoalKey] = useState<string>('');
  const [goals, setGoals] = useState<GapGoalInfo[]>([]);
  const [busy, setBusy] = useState<'discover' | 'generate' | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Plan state
  const [plans, setPlans] = useState<LearningPlanSummary[]>([]);
  const [active, setActive] = useState<LearningPlanDetail | null>(null);
  const [busyTask, setBusyTask] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<number>>(new Set());

  // Study-Session Loop — micro-session on the next incomplete task.
  const [planSession, setPlanSession] = useState<PlanSessionState | null>(null);
  const [sessionBusy2, setSessionBusy2] = useState(false);

  // Study Schedule — roadmap → day-by-day plan (explicit user action only).
  const [schedule, setSchedule] = useState<LearningSchedule | null>(null);
  const [scheduleBusy, setScheduleBusy] = useState(false);
  const [scheduleMode, setScheduleMode] = useState('daily_hours');
  const [dailyHours, setDailyHours] = useState('1');
  const [modulesPerDay, setModulesPerDay] = useState('5');
  const [timeSlotsRaw, setTimeSlotsRaw] = useState('07:00-08:00');
  const [instruction, setInstruction] = useState('');

  // PortSwigger sign-in — lets the crawler verify auth-gated resource URLs.
  const [session, setSession] = useState<PortswiggerSessionStatus | null>(null);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [showConnect, setShowConnect] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [sessionEmail, setSessionEmail] = useState('');
  const [sessionPassword, setSessionPassword] = useState('');
  const [sessionRemember, setSessionRemember] = useState(true);

  const loadPlans = useCallback(async () => {
    try {
      const res = await endpoints.kb.learningPlans.list();
      setPlans(res.items);
    } catch {
      setPlans([]);
    }
  }, []);

  useEffect(() => { void loadPlans(); }, [loadPlans]);

  useEffect(() => {
    endpoints.kb.gaps
      .domains()
      .then((res) => setGoals(res.goals ?? []))
      .catch(() => setGoals([]));
  }, []);

  const loadSession = useCallback(async () => {
    try {
      const res = await endpoints.kb.learningPlans.session.status();
      setSession(res.session);
    } catch {
      setSession(null);
    }
  }, []);

  useEffect(() => { void loadSession(); }, [loadSession]);

  const loadPlanSession = useCallback(async (id: number) => {
    try {
      const res = await endpoints.kb.learningPlans.planSession.state(id);
      setPlanSession(res.session);
    } catch {
      setPlanSession(null);
    }
  }, []);

  // Read-only: the stored day-by-day study schedule (never calls the AI).
  const loadSchedule = useCallback(async (id: number) => {
    try {
      const res = await endpoints.kb.learningPlans.schedule.get(id);
      const s = res.schedule;
      setSchedule(s);
      // Pre-fill the form from the stored params so "Regenerate" reuses them.
      if (s) {
        setScheduleMode(s.mode);
        setDailyHours(String(s.params.daily_hours ?? 1));
        setModulesPerDay(String(s.params.modules_per_day ?? 5));
        setTimeSlotsRaw((s.params.time_slots ?? []).join(', '));
        setInstruction(s.params.instruction ?? '');
      }
    } catch {
      setSchedule(null);
    }
  }, []);

  const openPlan = useCallback(async (id: number) => {
    setActive(null);
    try {
      const res = await endpoints.kb.learningPlans.get(id);
      setActive(res.plan);
      setNotice(null);
      void loadPlanSession(id);
      void loadSchedule(id);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not load plan');
    }
  }, [loadPlanSession, loadSchedule]);

  const taskById = (id: number) => active?.tasks.find((t) => t.id === id) ?? null;

  const formPayload = () => {
    if (!goal.trim()) { setFormError('Describe your learning goal first.'); return null; }
    const resources = parseResourceLines(resourcesRaw);
    if (resources.length === 0) {
      setFormError('Add at least one source — the learning-path URL (e.g. https://portswigger.net/web-security/learning-paths).');
      return null;
    }
    setFormError(null);
    return {
      goal: goal.trim(),
      description: description.trim() || undefined,
      resources,
      known: splitList(knownRaw),
      unknown: splitList(unknownRaw),
      goal_key: goalKey || undefined,
    };
  };

  // Layer 1 — crawl the supplied source and persist the real platform structure.
  const discover = async () => {
    const payload = formPayload();
    if (!payload) return;
    setBusy('discover');
    setNotice(null);
    try {
      const res = await endpoints.kb.learningPlans.discover(payload);
      setActive(res.plan);
      setNotice(
        res.plan.source.report.paths_discovered > 0
          ? `Discovered ${res.plan.source.report.paths_discovered} learning path(s) from the source. Review the structure below, then build your roadmap.`
          : 'Discovery found no learning-path index at that URL — the submitted resources were persisted directly.',
      );
      void loadPlans();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Discovery failed');
    } finally {
      setBusy(null);
    }
  };

  // Layer 2 — build the personalised roadmap on top of the discovered structure.
  const buildRoadmap = async (knownOverride?: string[], unknownOverride?: string[]) => {
    if (!active) return;
    setBusy('generate');
    setNotice(null);
    try {
      const res = await endpoints.kb.learningPlans.generate(active.id, {
        known: knownOverride ?? splitList(knownRaw),
        unknown: unknownOverride ?? splitList(unknownRaw),
      });
      setActive(res.plan);
      setNotice(res.plan.engine === 'ai' ? 'Roadmap built from the discovered structure (AI-assisted)' : 'Roadmap built from the discovered structure (deterministic — AI off or unreachable)');
      void loadPlans();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setBusy(null);
    }
  };

  // One-shot convenience: discover + build in a single call.
  const generate = async () => {
    const payload = formPayload();
    if (!payload) return;
    setBusy('generate');
    setNotice(null);
    try {
      const res = await endpoints.kb.learningPlans.create(payload);
      setActive(res.plan);
      setNotice(res.plan.engine === 'ai' ? 'Roadmap generated (AI-assisted)' : 'Roadmap generated (deterministic — AI off or unreachable)');
      void loadPlans();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setBusy(null);
    }
  };

  const toggleTask = async (task: LearningTask) => {
    if (!active) return;
    setBusyTask(task.id);
    try {
      const res = await endpoints.kb.learningPlans.toggleTask(active.id, task.id, !task.done);
      setActive((prev) => {
        if (!prev) return prev;
        const tasks = prev.tasks.map((t) => (t.id === task.id ? res.task : t));
        const done = tasks.filter((t) => t.done).length;
        // Roll per-path progress up from the toggled task.
        const path_progress = prev.path_progress.map((p) => {
          const pt = tasks.filter((t) => t.path_id === p.path_id);
          const pd = pt.filter((t) => t.done).length;
          return { ...p, done_tasks: pd, total_tasks: pt.length, progress_percent: pt.length ? Math.round((pd / pt.length) * 100) : 0 };
        });
        return {
          ...prev,
          tasks,
          path_progress,
          stats: { total_tasks: tasks.length, done_tasks: done, progress_percent: tasks.length ? Math.round((done / tasks.length) * 100) : 0 },
          next_task: tasks.find((t) => !t.done) ?? null,
        };
      });
      if (active) void loadSchedule(active.id); // refresh schedule done/stale
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not update task');
    } finally {
      setBusyTask(null);
    }
  };

  const handleSessionLogin = async () => {
    if (!sessionEmail.trim() || !sessionPassword) {
      setSessionError('Enter your PortSwigger email and password.');
      return;
    }
    setSessionBusy(true);
    setSessionError(null);
    try {
      const res = await endpoints.kb.learningPlans.session.login({
        email: sessionEmail.trim(),
        password: sessionPassword,
        remember: sessionRemember,
      });
      setSession(res.session);
      setShowConnect(false);
      setSessionPassword('');
      setNotice('PortSwigger account connected — re-verify the gated resources below to unlock their URLs.');
    } catch (e) {
      setSessionError(
        e instanceof Error ? e.message.replace('API ', '') : 'Could not sign in to PortSwigger.'
      );
    } finally {
      setSessionBusy(false);
    }
  };

  const handleSessionLogout = async (clearCredentials = false) => {
    setSessionBusy(true);
    try {
      const res = await endpoints.kb.learningPlans.session.logout(clearCredentials ? { clear_credentials: true } : undefined);
      setSession(res.session);
      if (clearCredentials) {
        setShowConnect(false);
        setNotice('PortSwigger account disconnected.');
      } else {
        setNotice('PortSwigger session signed out — credentials kept for one-click reconnect.');
      }
    } catch {
      setSessionError('Could not sign out.');
    } finally {
      setSessionBusy(false);
    }
  };

  // Explicit user action: re-crawl the paths + re-verify gated URLs with the
  // stored session. Never runs automatically.
  const reverify = async () => {
    if (!active) return;
    setBusy('generate');
    setSessionError(null);
    try {
      const res = await endpoints.kb.learningPlans.reverify(active.id);
      setActive(res.plan);
      const r: LearningReverifyReport = res.reverify;
      setNotice(
        `Re-checked ${r.paths_rechecked} path page(s) with your session · unlocked ${r.resources_unlocked} gated URL(s) · verified ${r.resources_verified}, failed ${r.resources_failed}.`,
      );
    } catch (e) {
      setSessionError(e instanceof Error ? e.message : 'Re-verification failed.');
    } finally {
      setBusy(null);
    }
  };

  // Study-Session Loop — explicit user actions only.
  const startPlanSessionOn = async (taskId?: number) => {
    if (!active) return;
    setSessionBusy2(true);
    setNotice(null);
    try {
      const res = await endpoints.kb.learningPlans.planSession.start(active.id, taskId ? { task_id: taskId } : {});
      setPlanSession(res.state);
      setNotice(`⏱ Study session started on: ${res.session.practice_task ?? 'your next task'}`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not start study session');
    } finally {
      setSessionBusy2(false);
    }
  };

  const startPlanSession = async () => { void startPlanSessionOn(); };

  // Explicit user action: build the day-by-day schedule from the roadmap.
  const createSchedule = async () => {
    if (!active) return;
    setScheduleBusy(true);
    setNotice(null);
    try {
      const hours = parseFloat(dailyHours);
      const modules = parseInt(modulesPerDay, 10);
      const res = await endpoints.kb.learningPlans.schedule.create(active.id, {
        mode: scheduleMode,
        daily_hours: scheduleMode === 'daily_hours' || scheduleMode === 'hybrid' ? (Number.isFinite(hours) ? hours : 1) : null,
        modules_per_day: scheduleMode === 'modules_per_day' || scheduleMode === 'hybrid' ? (Number.isFinite(modules) ? modules : 5) : null,
        time_slots: scheduleMode === 'time_slots' ? timeSlotsRaw.split(',').map((s) => s.trim()).filter(Boolean) : [],
        instruction: scheduleMode === 'ai_instruction' ? instruction.trim() || null : null,
      });
      setSchedule(res.schedule);
      const d = res.schedule.stats.days;
      setNotice(
        res.schedule.engine === 'ai'
          ? `📅 Study plan built from your routine (${d} day${d === 1 ? '' : 's'}, ~${res.schedule.stats.total_hours}h total) — AI-assisted.`
          : `📅 Study plan built (${d} day${d === 1 ? '' : 's'}, ~${res.schedule.stats.total_hours}h total).`,
      );
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not build the study schedule');
    } finally {
      setScheduleBusy(false);
    }
  };

  const clearSchedule = async () => {
    if (!active) return;
    setScheduleBusy(true);
    try {
      await endpoints.kb.learningPlans.schedule.remove(active.id);
      setSchedule(null);
      setNotice('Study schedule cleared — rebuild it whenever you like.');
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not clear the study schedule');
    } finally {
      setScheduleBusy(false);
    }
  };

  const completePlanSession = async () => {
    if (!active || !planSession?.live_session) return;
    setSessionBusy2(true);
    setNotice(null);
    try {
      const res = await endpoints.kb.learningPlans.planSession.complete(active.id, planSession.live_session.id);
      setPlanSession({
        plan_id: res.plan_id,
        live_session: res.live_session,
        last_session: res.last_session,
        next_task: res.next_task,
        progress: res.progress,
        completed: res.completed,
      });
      setNotice(
        res.task_completed
          ? `✅ Session complete — task done (${res.progress.done_tasks}/${res.progress.total_tasks}). ${res.next_task ? `Next: ${res.next_task.title}` : 'All tasks complete!'}`
          : 'Session complete.',
      );
      void openPlan(active.id); // refresh progress + next-task rollups + schedule done/stale
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not complete study session');
    } finally {
      setSessionBusy2(false);
    }
  };

  // Plan Re-sync — explicit: refresh the real platform structure only.
  const resync = async () => {
    if (!active) return;
    setBusy('generate');
    setNotice(null);
    try {
      const res = await endpoints.kb.learningPlans.resync(active.id);
      setActive(res.plan);
      const r = res.resync;
      const bits = [
        `Re-crawled ${r.urls_checked} source URL(s)`,
        `${r.paths_added.length} new path(s) discovered`,
        `${r.paths_refreshed} refreshed`,
      ];
      if (r.paths_removed.length) bits.push(`${r.paths_removed.length} no longer on the source`);
      if (r.errors.length) bits.push(`${r.errors.length} error(s)`);
      setNotice(`🔄 Plan re-synced: ${bits.join(' · ')}. Your roadmap was not changed.`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Re-sync failed');
    } finally {
      setBusy(null);
    }
  };

  const removePlan = async (id: number) => {
    if (!confirmDelete('this learning plan and its progress')) return;
    try {
      await endpoints.kb.learningPlans.remove(id);
      if (active?.id === id) setActive(null);
      void loadPlans();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not delete plan');
    }
  };

  const togglePath = (id: number) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const topicRow = (t: LearningTopic) => {
    const st = STATUS_STYLE[t.status] ?? STATUS_STYLE.unknown;
    return (
      <div key={t.name} style={styles.row}>
        <span style={{ ...styles.chip, background: st.bg, color: st.color }}>{st.label}</span>
        <span style={{ flex: 1 }}>{t.name}</span>
        {t.difficulty && (
          <span style={{ ...styles.chip, background: 'var(--info-muted)', color: DIFFICULTY_COLOR[t.difficulty] ?? 'var(--info)' }}>{t.difficulty}</span>
        )}
        {t.est_time && <span style={{ ...styles.chip, background: 'var(--accent-muted)', color: 'var(--accent)' }}>{t.est_time}</span>}
      </div>
    );
  };

  const tasksByPhase = (phaseNo: number) => (active?.tasks ?? []).filter((t) => t.phase === phaseNo);

  const reportRow = (report: LearningCrawlReport | undefined) => {
    if (!report) return null;
    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
        <span>📡 <strong>{report.paths_discovered}</strong> path(s) discovered</span>
        <span>· <strong>{report.paths_crawled}</strong> crawled</span>
        {report.paths_failed > 0 && <span>· <strong style={{ color: 'var(--danger)' }}>{report.paths_failed} failed</strong></span>}
        <span>· <strong>{report.resources_extracted}</strong> resource(s) extracted</span>
        {report.resources_with_url > 0 && <span>· <strong>{report.resources_with_url}</strong> with public URL</span>}
        {report.resources_verified > 0 && <span>· <strong style={{ color: 'var(--success)' }}>{report.resources_verified} verified</strong></span>}
        {report.resources_failed > 0 && <span>· <strong style={{ color: 'var(--danger)' }}>{report.resources_failed} unreachable/sign-in</strong></span>}
      </div>
    );
  };

  const needsReverify = (active?.source?.paths ?? []).some((p) =>
    (p.resources ?? []).some(
      (r) => r.crawl_status === 'auth_required' || (r.crawl_status === 'discovered' && !r.url),
    ),
  );

  // PortSwigger session strip — shows connect form / status / re-verify action.
  // Only rendered when it is relevant (gated resources present, a session is
  // stored, or the connect form is open) so generic plans stay quiet.
  const sessionStrip = () => {
    const authed = session?.authenticated;
    if (!needsReverify && !session?.configured && !showConnect) return null;
    return (
      <div style={{ border: '1px dashed var(--border)', borderRadius: 8, padding: '0.55rem 0.7rem', marginBottom: '0.75rem', background: 'var(--bg)' }}>
        {authed ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ ...styles.chip, background: 'var(--success-muted)', color: 'var(--success)' }}>🔓 CONNECTED</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', flex: 1, minWidth: 140 }}>
              {session?.email}
              {session?.expires_at ? <> · expires {fmtDate(session.expires_at)}</> : ''}
            </span>
            {needsReverify ? (
              <button type="button" className="btn btn-sm" disabled={busy !== null || sessionBusy} onClick={() => void reverify()}>
                {busy === 'generate' ? 'Re-verifying…' : '🔓 Re-verify gated resources'}
              </button>
            ) : (
              <span style={{ fontSize: '0.72rem', color: 'var(--success)' }}>✓ All resource URLs verified with your session</span>
            )}
            <button type="button" className="btn btn-ghost btn-sm" disabled={sessionBusy} onClick={() => void handleSessionLogout()}>
              Sign out
            </button>
          </div>
        ) : session?.configured ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ ...styles.chip, background: 'var(--warning-muted)', color: 'var(--warning)' }}>SESSION EXPIRED</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', flex: 1, minWidth: 140 }}>
              Credentials stored for {session?.email} — reconnect to verify gated URLs.
            </span>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => {
                setSessionEmail(session?.email ?? '');
                setSessionError(null);
                setShowConnect(true);
              }}
            >
              Reconnect
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void handleSessionLogout(true)}>Disconnect</button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', flex: 1 }}>
              🔒 Some resource URLs on this platform are sign-in-gated. Connect your own PortSwigger account to unlock and verify them.
            </span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setShowConnect((v) => !v); setSessionError(null); }}>
              {showConnect ? 'Hide' : '🔑 Connect PortSwigger account'}
            </button>
          </div>
        )}

        {showConnect && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '0.5rem', marginTop: '0.6rem', alignItems: 'end' }}>
            <div>
              <label style={{ ...styles.label, marginBottom: '0.2rem' }}>PortSwigger email</label>
              <input style={styles.input} type="email" value={sessionEmail} onChange={(e) => setSessionEmail(e.target.value)} placeholder="you@example.com" autoComplete="username" />
            </div>
            <div>
              <label style={{ ...styles.label, marginBottom: '0.2rem' }}>Password</label>
              <input style={styles.input} type="password" value={sessionPassword} onChange={(e) => setSessionPassword(e.target.value)} placeholder="••••••••" autoComplete="current-password" />
            </div>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button type="button" className="btn btn-primary btn-sm" disabled={sessionBusy} onClick={() => void handleSessionLogin()}>
                {sessionBusy ? 'Signing in…' : 'Sign in'}
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowConnect(false)}>Cancel</button>
            </div>
            <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.3rem', gridColumn: '1 / -1' }}>
              <input type="checkbox" checked={sessionRemember} onChange={(e) => setSessionRemember(e.target.checked)} />
              Store my credentials on this device (obfuscated) so an expired session can refresh automatically — local single-user app only.
            </label>
          </div>
        )}
        {sessionError && <p style={{ fontSize: '0.72rem', color: 'var(--danger)', margin: '0.5rem 0 0' }}>⚠ {sessionError}</p>}
      </div>
    );
  };

  const sourcePathCard = (path: LearningSourcePath) => {
    const expanded = expandedPaths.has(path.id);
    const progress = (active?.path_progress ?? []).find((p) => p.path_id === path.id);
    return (
      <div key={path.id} style={{ border: '1px solid var(--border)', borderRadius: 10, marginBottom: '0.5rem', overflow: 'hidden' }}>
        <button
          type="button"
          onClick={() => togglePath(path.id)}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%', background: 'var(--bg-hover)', border: 'none', padding: '0.6rem 0.8rem', cursor: 'pointer', textAlign: 'left', color: 'var(--text-primary)' }}
        >
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', width: '0.9rem' }}>{expanded ? '▾' : '▸'}</span>
          <span style={{ flex: 1, fontWeight: 700, fontSize: '0.8rem' }}>{path.title}</span>
          {path.difficulty && (
            <span style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }}>{path.difficulty}</span>
          )}
          <span style={{ ...styles.chip, background: 'var(--accent-muted)', color: 'var(--accent)' }}>
            {(path.resources ?? []).length}{path.resource_total ? `/${path.resource_total}` : ''} resources
          </span>
          {crawlChip(path.crawl_status)}
        </button>

        {expanded && (
          <div style={{ padding: '0.6rem 0.8rem' }}>
            {path.description && <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0 0 0.5rem' }}>{path.description}</p>}
            {path.source_url && (
              <a href={path.source_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.72rem', color: 'var(--accent)', textDecoration: 'none', display: 'block', marginBottom: '0.4rem' }}>
                🔗 View path on {path.platform || 'the platform'}
              </a>
            )}
            {path.error && <p style={{ fontSize: '0.7rem', color: 'var(--danger)', margin: '0 0 0.5rem' }}>⚠ {path.error}</p>}
            {progress && progress.total_tasks > 0 && (
              <div style={{ marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                  <span>Path progress</span><span>{progress.done_tasks}/{progress.total_tasks} · {progress.progress_percent}%</span>
                </div>
                <div style={{ height: 5, borderRadius: 999, background: 'var(--border)', overflow: 'hidden', marginTop: '0.2rem' }}>
                  <div style={{ height: '100%', width: `${progress.progress_percent}%`, background: 'var(--accent)', transition: 'width 0.3s ease' }} />
                </div>
              </div>
            )}
            {(path.resources ?? []).length === 0 ? (
              <p style={styles.empty}>No resources extracted from this path page.</p>
            ) : (
              <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 8 }}>
                {(path.resources ?? []).map((r: LearningSourceResource) => (
                  <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', padding: '0.35rem 0.55rem', borderBottom: '1px solid var(--border)', fontSize: '0.75rem' }}>
                    <span style={{ flexShrink: 0 }}>{r.resource_type === 'lab' ? '🧪' : '📖'}</span>
                    <span style={{ flex: 1, minWidth: 0 }}>
                      {r.url ? (
                        <a href={r.url} target="_blank" rel="noreferrer" style={{ color: 'var(--text-primary)', textDecoration: 'none' }} title={r.url}>{r.title}</a>
                      ) : (
                        <span title={r.crawl_status === 'discovered' && !r.url ? 'This resource exists on the platform but its URL is only exposed to signed-in users — open the path page to access it.' : undefined}>{r.title}</span>
                      )}
                    </span>
                    {r.section && <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', flexShrink: 0 }}>{r.section}</span>}
                    {r.difficulty && <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', flexShrink: 0 }}>{r.difficulty}</span>}
                    {crawlChip(r.crawl_status)}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      <Header title="🗺️ Learning Path Planner" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Give it a goal and a learning-platform URL (e.g.{' '}
        <code style={{ fontSize: '0.7rem' }}>https://portswigger.net/web-security/learning-paths</code>). The planner crawls the site,
        discovers its real learning paths and resources (<strong>Source Structure</strong>), then builds your personalised
        roadmap on top of them. Only resources actually fetched from the site are labeled <strong>CRAWLED</strong> — anything
        else is labeled honestly (<strong>DISCOVERED</strong>, <strong>SIGN-IN REQUIRED</strong>, <strong>HTTP ERROR</strong>, …).
      </p>

      {notice && <div className="notice notice-success" style={{ marginBottom: '0.75rem' }}>{notice}</div>}
      {formError && <div className="notice notice-error" style={{ marginBottom: '0.75rem' }}>{formError}</div>}

      {!active && (
        <div className="card" style={styles.card}>
          <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.9rem' }}>🎯 New learning plan</h3>
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            <div>
              <label style={styles.label}>Learning goal</label>
              <input style={styles.input} value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="e.g. Complete all PortSwigger Web Security learning paths" />
            </div>
            <div>
              <label style={styles.label}>Source URL — one per line: <code>name | URL</code></label>
              <textarea
                style={styles.textarea}
                value={resourcesRaw}
                onChange={(e) => setResourcesRaw(e.target.value)}
                placeholder={'PortSwigger Academy | https://portswigger.net/web-security/learning-paths\nOWASP Juice Shop | https://owasp.org/www-project-juice-shop/'}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div>
                <label style={styles.label}>I already know (comma-separated)</label>
                <input style={styles.input} value={knownRaw} onChange={(e) => setKnownRaw(e.target.value)} placeholder="HTTP basics, Burp Suite, XSS, CSRF" />
              </div>
              <div>
                <label style={styles.label}>I don't know (comma-separated)</label>
                <input style={styles.input} value={unknownRaw} onChange={(e) => setUnknownRaw(e.target.value)} placeholder="SSRF, XXE, Deserialization" />
              </div>
            </div>
            {goals.length > 0 && (
              <div>
                <label style={styles.label}>Optional: match a catalog goal (uses your Second Brain evidence)</label>
                <select style={styles.input} value={goalKey} onChange={(e) => setGoalKey(e.target.value)}>
                  <option value="">— none —</option>
                  {goals.map((g) => (
                    <option key={g.key} value={g.key} title={g.description}>{g.title}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label style={styles.label}>Optional notes</label>
              <input style={styles.input} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. aiming for bug bounty / OSCP" />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
              <button type="button" className="btn" disabled={busy !== null} onClick={() => void discover()}>
                {busy === 'discover' ? 'Crawling source…' : '🔍 Discover paths'}
              </button>
              <button type="button" className="btn btn-primary" disabled={busy !== null} onClick={() => void generate()}>
                {busy === 'generate' ? 'Building roadmap…' : '⚡ Discover + roadmap'}
              </button>
              {busy && <span className="spinner spinner-sm" />}
            </div>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: 0 }}>
              <strong>Discover paths</strong> shows the real platform structure first (so you can verify it) — then build the roadmap.
              <strong> Discover + roadmap</strong> does both in one step.
            </p>
          </div>
        </div>
      )}

      {active && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setActive(null)}>← New plan</button>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {active.goal} · created {fmtDate(active.created_at)}
              {active.status === 'generated' && <> · generated {fmtDate(active.generated_at)}</>} ·{' '}
              <span style={{ fontWeight: 700, color: active.engine === 'ai' ? 'var(--accent)' : 'var(--warning)' }}>
                {active.engine === 'ai' ? 'AI-assisted' : 'deterministic'}
              </span>
            </span>
            <span style={{ flex: 1 }} />
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void removePlan(active.id)}>🗑 Delete</button>
          </div>

          {/* ── Layer 1: SOURCE STRUCTURE (the real platform) ── */}
          <div className="card" style={{ ...styles.card, borderLeft: '3px solid var(--info)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
              <h3 style={{ fontSize: '0.9rem', margin: 0 }}>🏗️ Source Structure</h3>
              <span className="badge badge-info">{active.source?.report?.platform || 'platform'}</span>
              <span style={{ flex: 1 }} />
              {active.status === 'discovered' && (
                <button type="button" className="btn btn-primary btn-sm" disabled={busy !== null} onClick={() => void buildRoadmap()}>
                  {busy === 'generate' ? 'Building…' : '🛣️ Build personalized roadmap'}
                </button>
              )}
              {active.status === 'generated' && (
                <button type="button" className="btn btn-ghost btn-sm" disabled={busy !== null} onClick={() => void buildRoadmap()}>
                  ↻ Rebuild roadmap
                </button>
              )}
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={busy !== null}
                onClick={() => void resync()}
                title="Re-crawl the source URL(s): adds new paths the site gained, flags removed ones. Your roadmap is never touched."
              >
                {busy === 'generate' ? 'Re-crawling…' : '🔄 Re-sync source'}
              </button>
            </div>
            <p style={styles.sub}>Layer 1 — exactly what exists on the external platform. Never modified by AI.</p>
            {reportRow(active.source?.report)}
            {sessionStrip()}
            {(active.source?.paths ?? []).length === 0 ? (
              <p style={styles.empty}>No learning paths were discovered for this plan's sources.</p>
            ) : (
              (active.source?.paths ?? []).map(sourcePathCard)
            )}
          </div>

          {active.status === 'generated' && (
            <>
              {/* Progress */}
              <div className="card" style={{ ...styles.card, padding: '0.9rem 1.1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>📈 Progress</span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {active.stats.done_tasks} / {active.stats.total_tasks} tasks · {active.stats.progress_percent}%
                  </span>
                </div>
                <div style={{ height: 8, borderRadius: 999, background: 'var(--border)', marginTop: '0.5rem', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${active.stats.progress_percent}%`, background: 'var(--accent)', transition: 'width 0.3s ease' }} />
                </div>
                {active.next_task && (
                  <div style={{ marginTop: '0.6rem', fontSize: '0.8rem' }}>
                    ▶ <strong>Next:</strong> {active.next_task.title}
                    {active.next_task.resource_url && (
                      <> — <a href={active.next_task.resource_url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>{active.next_task.resource_title ?? 'open'}</a></>
                    )}
                  </div>
                )}
                {active.next_task === null && active.stats.total_tasks > 0 && (
                  <div style={{ marginTop: '0.6rem', fontSize: '0.8rem', color: 'var(--success)' }}>🎉 All tasks complete — you've reached your goal!</div>
                )}
              </div>

              {/* Study-Session Loop — micro-session on the next incomplete task */}
              <div className="card" style={{ ...styles.card, borderLeft: '3px solid var(--accent)', marginTop: '0.9rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <h3 style={{ fontSize: '0.85rem', margin: 0 }}>⏱ Study Session</h3>
                  <span style={{ flex: 1 }} />
                  {planSession?.live_session ? (
                    <button type="button" className="btn btn-primary btn-sm" disabled={sessionBusy2} onClick={() => void completePlanSession()}>
                      {sessionBusy2 ? 'Completing…' : '✅ Complete session'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={sessionBusy2 || planSession?.completed}
                      onClick={() => void startPlanSession()}
                    >
                      {sessionBusy2 ? 'Starting…' : '▶ Start session on next task'}
                    </button>
                  )}
                </div>
                {planSession?.live_session ? (
                  <div style={{ marginTop: '0.55rem', fontSize: '0.8rem' }}>
                    <div style={{ fontWeight: 700 }}>{planSession.live_session.practice_task}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                      {planSession.live_session.duration_mins} min · started {fmtDate(planSession.live_session.created_at)} ·{' '}
                      complete it to mark the task done
                    </div>
                  </div>
                ) : planSession?.completed ? (
                  <p style={{ fontSize: '0.78rem', color: 'var(--success)', margin: '0.5rem 0 0' }}>
                    🎉 Every task in this plan is complete — nothing left to study.
                  </p>
                ) : (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0.5rem 0 0' }}>
                    Opens a focused {planSession?.next_task ? `session on “${planSession.next_task.title}”` : 'session on your next task'} —
                    completing it checks the task off and advances the roadmap.
                  </p>
                )}
              </div>

              {/* Study Schedule — roadmap → day-by-day plan (explicit action) */}
              <div className="card" style={{ ...styles.card, borderLeft: '3px solid var(--warning)', marginTop: '0.9rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <h3 style={{ fontSize: '0.85rem', margin: 0 }}>📅 Study Schedule</h3>
                  <span style={{ flex: 1 }} />
                  {schedule && (
                    <>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {schedule.engine === 'ai' ? 'AI-planned' : 'planned'} · {fmtDate(schedule.generated_at)}
                      </span>
                      <button type="button" className="btn btn-ghost btn-sm" disabled={scheduleBusy} onClick={() => void clearSchedule()}>
                        🗑 Clear
                      </button>
                    </>
                  )}
                </div>
                <p style={styles.sub}>
                  Your personalised roadmap, scheduled the way YOU want to study. Built only when you click — reading it never calls the AI.
                </p>

                {!schedule && (
                  <div style={{ display: 'grid', gap: '0.6rem' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                      {SCHEDULE_MODES.map((m) => (
                        <button
                          key={m.key}
                          type="button"
                          onClick={() => setScheduleMode(m.key)}
                          title={m.hint}
                          style={{
                            ...styles.chip,
                            background: scheduleMode === m.key ? 'var(--accent)' : 'var(--bg-hover)',
                            color: scheduleMode === m.key ? 'var(--bg)' : 'var(--text-secondary)',
                            cursor: 'pointer',
                            border: '1px solid var(--border)',
                            padding: '0.35rem 0.6rem',
                            fontSize: '0.72rem',
                          }}
                        >
                          {m.label}
                        </button>
                      ))}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.5rem', alignItems: 'end' }}>
                      {(scheduleMode === 'daily_hours' || scheduleMode === 'hybrid') && (
                        <div>
                          <label style={styles.label}>Hours per day</label>
                          <input style={styles.input} type="number" min={0.25} max={12} step={0.25} value={dailyHours} onChange={(e) => setDailyHours(e.target.value)} />
                        </div>
                      )}
                      {(scheduleMode === 'modules_per_day' || scheduleMode === 'hybrid') && (
                        <div>
                          <label style={styles.label}>Tasks / modules per day</label>
                          <input style={styles.input} type="number" min={1} max={30} step={1} value={modulesPerDay} onChange={(e) => setModulesPerDay(e.target.value)} />
                        </div>
                      )}
                      {scheduleMode === 'time_slots' && (
                        <div>
                          <label style={styles.label}>Daily time slots (comma-separated)</label>
                          <input style={styles.input} value={timeSlotsRaw} onChange={(e) => setTimeSlotsRaw(e.target.value)} placeholder="07:00-08:00, 20:00-21:00" />
                        </div>
                      )}
                      {scheduleMode === 'ai_instruction' && (
                        <div style={{ gridColumn: '1 / -1' }}>
                          <label style={styles.label}>Describe how you want to study</label>
                          <textarea
                            style={styles.textarea}
                            value={instruction}
                            onChange={(e) => setInstruction(e.target.value)}
                            placeholder={'e.g. 1 hour every morning at 7am, plus 2 hours on Saturday. No more than 3 topics a day — I like deep dives.'}
                          />
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <button type="button" className="btn btn-primary btn-sm" disabled={scheduleBusy} onClick={() => void createSchedule()}>
                        {scheduleBusy ? 'Planning…' : '📅 Create study plan'}
                      </button>
                      {scheduleBusy && <span className="spinner spinner-sm" />}
                      {scheduleMode === 'ai_instruction' && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          The AI assigns your real roadmap tasks to days — it can't invent new ones. Falls back to 1h/day if AI is unavailable.
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {schedule && (
                  <div style={{ marginTop: '0.55rem' }}>
                    {schedule.stale && (
                      <div className="notice notice-warning" style={{ margin: '0 0 0.6rem', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span>Task progress changed since this schedule was built — the layout may no longer match.</span>
                        <button type="button" className="btn btn-sm" disabled={scheduleBusy} onClick={() => void createSchedule()}>
                          {scheduleBusy ? 'Planning…' : '↻ Regenerate'}
                        </button>
                      </div>
                    )}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                      <span>📅 <strong>{schedule.stats.days}</strong> day{schedule.stats.days === 1 ? '' : 's'}</span>
                      <span>· ⏱ <strong>{schedule.stats.total_hours}</strong>h total</span>
                      <span>· 📚 <strong>{schedule.stats.remaining_tasks}</strong> task{schedule.stats.remaining_tasks === 1 ? '' : 's'} to do</span>
                      {schedule.stats.estimated_end_date && <span>· 🏁 ends {schedule.stats.estimated_end_date}</span>}
                      {schedule.stats.done_tasks > 0 && <span>· ✅ {schedule.stats.done_tasks} already done (skipped)</span>}
                      {schedule.stats.days === 0 && schedule.note && <span style={{ color: 'var(--success)' }}>{schedule.note}</span>}
                    </div>

                    {schedule.days.map((day) => {
                      const firstOpen = day.tasks.find((st) => !st.done);
                      return (
                        <div key={day.day} style={{ border: '1px solid var(--border)', borderRadius: 10, marginBottom: '0.5rem', overflow: 'hidden' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', padding: '0.5rem 0.8rem', background: 'var(--bg-hover)' }}>
                            <span style={{ fontWeight: 700, fontSize: '0.78rem' }}>Day {day.day} · {day.label}</span>
                            {day.slots.map((s) => (
                              <span key={s} style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }}>{s}</span>
                            ))}
                            <span style={{ ...styles.chip, background: 'var(--accent-muted)', color: 'var(--accent)' }}>{fmtMins(day.total_minutes)}</span>
                            <span style={{ flex: 1 }} />
                            <button
                              type="button"
                              className="btn btn-sm"
                              disabled={sessionBusy2 || !firstOpen || planSession?.live_session != null}
                              onClick={() => void startPlanSessionOn(firstOpen?.task_id)}
                              title={firstOpen ? `Start a session on “${firstOpen.title}”` : 'All tasks on this day are done'}
                            >
                              ▶ Start
                            </button>
                          </div>
                          {day.tasks.length === 0 ? (
                            <p style={styles.empty}>Rest day — nothing scheduled.</p>
                          ) : (
                            day.tasks.map((st) => (
                              <div key={st.task_id} style={{ ...styles.row, opacity: st.done ? 0.55 : 1 }}>
                                <input
                                  type="checkbox"
                                  checked={st.done}
                                  disabled={busyTask === st.task_id}
                                  onChange={() => {
                                    const t = taskById(st.task_id);
                                    if (t) void toggleTask(t);
                                  }}
                                  style={{ accentColor: 'var(--accent)', flexShrink: 0 }}
                                  aria-label={`Mark ${st.title}`}
                                />
                                <span style={{ flex: 1, textDecoration: st.done ? 'line-through' : 'none' }}>{st.title}</span>
                                {st.est_time && <span style={{ ...styles.chip, background: 'var(--accent-muted)', color: 'var(--accent)' }}>{st.est_time}</span>}
                                {st.resource_url && (
                                  <a href={st.resource_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem', color: 'var(--accent)', textDecoration: 'none' }} title={st.resource_title ?? st.resource_url}>🔗</a>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem', alignItems: 'start' }}>
                {/* Roadmap phases */}
                <div className="card" style={styles.card}>
                  <h3 style={{ fontSize: '0.9rem', margin: 0 }}>🛣️ Personalized Roadmap</h3>
                  <p style={styles.sub}>Layer 2 — AI organises the real resources above; check tasks off as you go</p>
                  {active.stats.truncated && (
                    <div className="notice notice-warning" style={{ margin: '0.5rem 0', fontSize: '0.72rem' }}>
                      This plan has more tasks than can be tracked at once — the roadmap was capped at {active.stats.total_tasks} checkable
                      tasks, but every discovered resource remains listed in <strong>Source Structure</strong> above.
                    </div>
                  )}
                  {active.phases.length === 0 && <p style={styles.empty}>No phases generated.</p>}
                  {active.phases.map((phase) => {
                    const phaseTasks = tasksByPhase(phase.phase);
                    const done = phaseTasks.filter((t) => t.done).length;
                    return (
                      <div key={phase.phase} style={{ marginTop: '0.8rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ ...styles.chip, background: 'var(--accent-muted)', color: 'var(--accent)' }}>P{phase.phase}</span>
                          <span style={{ fontWeight: 700, fontSize: '0.82rem', flex: 1 }}>{phase.title}</span>
                          {phaseTasks.length > 0 && <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{done}/{phaseTasks.length}</span>}
                        </div>
                        {phaseTasks.length === 0 && <p style={styles.empty}>No tasks in this phase.</p>}
                        {phaseTasks.map((t) => (
                          <div key={t.id} style={styles.row}>
                            <input
                              type="checkbox"
                              checked={t.done}
                              disabled={busyTask === t.id}
                              onChange={() => void toggleTask(t)}
                              style={{ accentColor: 'var(--accent)', flexShrink: 0 }}
                              aria-label={`Mark ${t.title}`}
                            />
                            <span style={{ flex: 1, textDecoration: t.done ? 'line-through' : 'none', opacity: t.done ? 0.6 : 1 }}>
                              {t.title}
                            </span>
                            {t.source_crawled ? (
                              <span style={{ ...styles.chip, background: 'var(--success-muted)', color: 'var(--success)' }} title="Resource fetched and verified">CRAWLED</span>
                            ) : (
                              <span style={{ ...styles.chip, background: 'var(--warning-muted)', color: 'var(--warning)' }} title="Real resource from the site; not fetched (see Source Structure)">SOURCE</span>
                            )}
                            {t.difficulty && (
                              <span style={{ ...styles.chip, background: 'var(--info-muted)', color: DIFFICULTY_COLOR[t.difficulty] ?? 'var(--info)' }}>{t.difficulty}</span>
                            )}
                            {t.resource_url && (
                              <a href={t.resource_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem', color: 'var(--accent)', textDecoration: 'none' }} title={t.resource_title ?? t.resource_url}>🔗</a>
                            )}
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>

                <div style={{ display: 'grid', gap: '1rem' }}>
                  {/* Topics */}
                  <div className="card" style={styles.card}>
                    <h3 style={{ fontSize: '0.9rem', margin: 0 }}>🧩 Topics to learn ({active.topics.length})</h3>
                    <p style={styles.sub}>Derived from the discovered resources, adapted to your knowledge</p>
                    {active.topics.length === 0 && <p style={styles.empty}>No topics extracted.</p>}
                    {active.topics.map(topicRow)}
                  </div>

                  {/* Dependencies */}
                  {active.dependencies.length > 0 && (
                    <div className="card" style={styles.card}>
                      <h3 style={{ fontSize: '0.9rem', margin: 0 }}>🔗 Prerequisite order</h3>
                      <p style={styles.sub}>AI-inferred recommendations — never presented as official</p>
                      {active.dependencies.map((d, i) => (
                        <div key={i} style={{ ...styles.row, borderBottom: 'none', padding: '0.25rem 0.15rem' }}>
                          <span style={{ fontSize: '0.75rem' }}>{d.from}</span>
                          <span style={{ color: 'var(--accent)', fontSize: '0.7rem' }}>→</span>
                          <span style={{ fontSize: '0.75rem', flex: 1 }}>{d.to}</span>
                          <span
                            style={{ ...styles.chip, background: d.source === 'platform' ? 'var(--success-muted)' : 'var(--warning-muted)', color: d.source === 'platform' ? 'var(--success)' : 'var(--warning)' }}
                            title={d.note ?? undefined}
                          >
                            {d.source === 'platform' ? 'official' : 'recommended'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Resources */}
                  <div className="card" style={styles.card}>
                    <h3 style={{ fontSize: '0.9rem', margin: 0 }}>📚 Resources ({active.resources.length})</h3>
                    <p style={styles.sub}>All extracted from the platform — each with its crawl status</p>
                    {active.resources.length === 0 && <p style={styles.empty}>No resources.</p>}
                    {active.resources.map((r, i) => (
                      <div key={i} style={{ ...styles.row, alignItems: 'flex-start', flexDirection: 'column', gap: '0.25rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%' }}>
                          {r.url ? (
                            <a href={r.url} target="_blank" rel="noreferrer" style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--accent)', textDecoration: 'none' }}>{r.title || r.url}</a>
                          ) : (
                            <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>{r.title}</span>
                          )}
                          <span style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }}>{r.type}</span>
                          {r.difficulty && <span style={{ ...styles.chip, background: 'var(--info-muted)', color: DIFFICULTY_COLOR[r.difficulty] ?? 'var(--info)' }}>{r.difficulty}</span>}
                          {crawlChip(r.crawl_status)}
                        </div>
                        {(r.topics ?? []).length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                            {(r.topics ?? []).slice(0, 8).map((t) => <span key={t} style={{ fontSize: '0.66rem', background: 'var(--accent-muted)', color: 'var(--accent)', padding: '0.1rem 0.45rem', borderRadius: 999 }}>{t}</span>)}
                            {(r.topics ?? []).length > 8 && <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>+{(r.topics ?? []).length - 8}</span>}
                          </div>
                        )}
                        {(r.prerequisites ?? []).length > 0 && (
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Prereqs: {(r.prerequisites ?? []).join(', ')}</div>
                        )}
                        {r.estimated_time && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>⏱ {r.estimated_time}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {!active && (
        <div className="card" style={styles.card}>
          <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.6rem' }}>🗂 Saved plans</h3>
          {plans.length === 0 ? (
            <p style={styles.empty}>No plans yet — generate one above.</p>
          ) : (
            plans.map((p) => (
              <div key={p.id} style={styles.row}>
                <span style={{ ...styles.chip, background: p.status === 'generated' ? 'var(--success-muted)' : 'var(--warning-muted)', color: p.status === 'generated' ? 'var(--success)' : 'var(--warning)' }}>
                  {p.status === 'discovered' ? 'source only' : p.engine === 'ai' ? 'AI' : 'deterministic'}
                </span>
                {p.source?.paths_discovered ? (
                  <span style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }} title={`${p.source.platform ?? 'platform'}`}>
                    {p.source.paths_discovered} path{p.source.paths_discovered === 1 ? '' : 's'}
                  </span>
                ) : null}
                <button type="button" style={{ flex: 1, textAlign: 'left', background: 'none', border: 'none', padding: 0, fontSize: '0.8rem', color: 'var(--accent)', cursor: 'pointer' }} onClick={() => void openPlan(p.id)}>
                  {p.goal}
                </button>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{fmtDate(p.created_at)}</span>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void removePlan(p.id)}>🗑</button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
