import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '../hooks/useToast';
import {
  HabitHeatmapCard,
  HabitStreakCard,
  HeatmapCarousel,
  ProjectCard,
  ProjectDetail,
  TaskCard,
  VaultHeader,
  ProjectModal,
  TaskCreateModal,
  VaultTabs,
  WeekProgressStrip,
  WeeklyCalendarRow,
  PerformanceWidget,
  HabitStatistics,
  QuickActionLink,
} from '../components/vault';
import { toIso, type LogEntry } from '../utils/vaultDates';
import { today as fToday, unrelated as fUnrelated, thisWeek as fThisWeek, inbox as fInbox, completed as fCompleted } from '../utils/vaultFilters';
import { endpoints, type Habit, type Task, type Project, type ProjectSummary, type VaultCalendar, type VaultSummary, type HabitStats } from '../services/api';
import { getGridCols, setGridCols } from '../utils/vaultGrid';
import { onHabitChange } from './HabitTracker';

/** habitId -> heatmap days (LogEntry[]), loaded in parallel for Row 1. */
type HeatmapStore = Record<number, LogEntry[]>;

const TAB_KEY = 'slos-vault-active-tab';
const VALID_TABS = ['Today', 'Unrelated Tasks', "This Week's Progress", 'Inbox', 'Completed'];

/**
 * Vault Dashboard shell (Phase 48).
 * Composes the header + sidebar + 4-row content area; data loads in parallel.
 * Rows are filled in by Phases 49-52.
 */
export const VaultDashboard = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const [gridCols, setGridColsState] = useState(getGridCols()); // Change Grid (1/2/3/4)
  const [firstHabitStats, setFirstHabitStats] = useState<HabitStats | null>(null);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [drillProject, setDrillProject] = useState<Project | null>(null);
  const [summary, setSummary] = useState<VaultSummary | null>(null);
  const [habits, setHabits] = useState<Habit[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [calendar, setCalendar] = useState<VaultCalendar | null>(null);
  const [projectSummaries, setProjectSummaries] = useState<Record<number, ProjectSummary>>({});
  const [heatmaps, setHeatmaps] = useState<HeatmapStore>({});
  const [tabTasks, setTabTasks] = useState<Task[]>([]);
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  // Defects #53/#97 fix: tab persisted via URL param with localStorage fallback.
  const [activeTab, setActiveTab] = useState(() => {
    const fromUrl = searchParams.get('tab');
    if (fromUrl && VALID_TABS.includes(fromUrl)) return fromUrl;
    const stored = localStorage.getItem(TAB_KEY);
    return stored && VALID_TABS.includes(stored) ? stored : 'Today';
  });
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Persist tab changes to URL + localStorage.
  const changeTab = useCallback((tab: string) => {
    setActiveTab(tab);
    try { localStorage.setItem(TAB_KEY, tab); } catch { /* storage unavailable */ }
  }, []);

  /** Map project_id -> name for task cards. */
  const projectNames: Record<number, string> = Object.fromEntries(
    projects.map((p) => [p.id, p.name]),
  );

  /** Client filter for the active tab (primary), server endpoint as fallback. */
  const applyTab = useCallback((tab: string, tasks: Task[]) => {
    switch (tab) {
      case 'Today': return fToday(tasks);
      case 'Unrelated Tasks': return fUnrelated(tasks);
      case "This Week's Progress": return fThisWeek(tasks);
      case 'Inbox': return fInbox(tasks);
      default: return fCompleted(tasks);
    }
  }, []);

  const loadTab = useCallback((tab: string) => {
    // Primary: filter the full task list client-side.
    if (allTasks.length > 0) {
      setTabTasks(applyTab(tab, allTasks));
      return;
    }
    // Fallback: server tab endpoint.
    const key = tab === 'Today' ? 'today'
      : tab === 'Unrelated Tasks' ? 'unrelated'
      : tab === "This Week's Progress" ? 'this_week'
      : tab === 'Inbox' ? 'inbox'
      : 'completed';
    endpoints.vault.tasks(key).then(setTabTasks).catch(() => setTabTasks([]));
  }, [allTasks, applyTab]);

  const onCompleteTask = (taskId: number) => {
    endpoints.tasks.update(taskId, { status: 'Completed' })
      .then(() => {
        toast('Task marked as completed', 'success');
        loadTab(activeTab);
        endpoints.vault.calendar().then(setCalendar);
      })
      .catch(() => toast('Could not complete task', 'error'));
  };

  /** Refresh everything after a task create/edit, then close any open modal. */
  const refreshTasks = () => {
    endpoints.tasks.list().then((ts) => {
      setAllTasks(ts);
      setTabTasks(applyTab(activeTab, ts));
    });
    setEditingTask(null);
    setShowCreate(false);
  };

  /** Reload project summaries after create/edit. */
  const refreshProjectSummaries = () => {
    endpoints.projects.list().then((ps) => {
      setProjects(ps);
      endpoints.projects.summaries()
        .then((batch) => {
          const mapped: Record<number, ProjectSummary> = {};
          for (const [id, s] of Object.entries(batch)) mapped[Number(id)] = s;
          setProjectSummaries(mapped);
        })
        .catch(() => {});
    });
    setEditingProject(null);
  };

  /** Reload a single habit's heatmap days (Row 1 + Row 2 share this). */
  const reloadHabit = useCallback((habitId: number) =>
    endpoints.habits.heatmap(habitId).then((hm) => {
      setHeatmaps((prev) => ({ ...prev, [habitId]: hm.days }));
    }), []);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      endpoints.vault.summary(),
      endpoints.habits.list(),
      endpoints.tasks.list(),
      endpoints.projects.list(),
      endpoints.vault.calendar(),
    ])
      .then(([summaryData, habitsData, allTasksData, projectsData, calendarData]) => {
        setSummary(summaryData);
        setHabits(habitsData);
        setAllTasks(allTasksData);
        setProjects(projectsData);
        setCalendar(calendarData);
        // Load the first habit's stats for the Performance widget streak graph (UX #5).
        if (habitsData[0]) {
          endpoints.habits.stats(habitsData[0].id).then(setFirstHabitStats).catch(() => {});
        }
        // Defect #51 fix: one batched heatmap call instead of one per habit.
        // Defect #52 fix: one batched project-summaries call instead of one per project.
        return Promise.all([
          endpoints.habits.heatmaps()
            .then((batch) => {
              const store: HeatmapStore = {};
              for (const [id, hm] of Object.entries(batch)) store[Number(id)] = hm.days;
              setHeatmaps(store);
            })
            .catch(() => {}),
          endpoints.projects.summaries()
            .then((batch) => {
              const mapped: Record<number, ProjectSummary> = {};
              for (const [id, s] of Object.entries(batch)) mapped[Number(id)] = s;
              setProjectSummaries(mapped);
            })
            .catch(() => {}),
        ]);
      })
      .catch(() => setError('Could not load vault data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Defects #12/#77 fix: refresh when habits change on other pages.
  useEffect(() => onHabitChange(() => {
    endpoints.habits.list().then((hs) => {
      setHabits(hs);
      endpoints.habits.heatmaps().then((batch) => {
        const store: HeatmapStore = {};
        for (const [id, hm] of Object.entries(batch)) store[Number(id)] = hm.days;
        setHeatmaps(store);
      }).catch(() => {});
    }).catch(() => {});
  }), []);

  useEffect(() => { loadTab(activeTab); }, [activeTab, loadTab]);

  const onLogToday = (habitId: number) => {
    endpoints.habits.logToday(habitId)
      .then(() => {
        toast('Habit logged today', 'success');
        reloadHabit(habitId);
        // Defect #77 fix: keep HabitTracker in sync with this log.
        window.dispatchEvent(new CustomEvent('habits:changed'));
      })
      .catch(() => toast('Could not log habit', 'error'));
  };

  const onToggleToday = (habitId: number) => {
    // Flip today's log: fetch the log list (has ids), then delete today's if present.
    endpoints.habits.logs(habitId).then((logs) => {
      const todayIso = toIso(new Date());
      const log = logs.find((l) => l.date === todayIso);
      if (log) endpoints.habits.deleteLog(log.id)
        .then(() => { toast('Today\'s log removed', 'info'); reloadHabit(habitId); })
        .catch(() => toast('Could not undo habit', 'error'));
      else toast('Nothing to undo for today', 'info');
    }).catch(() => toast('Could not load logs', 'error'));
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--vault-bg-main)',
        color: 'var(--vault-text-primary)',
        ['--vault-cols' as string]: gridCols,
      }}
    >
      <VaultHeader />

      <div style={{ display: 'flex', gap: 16, padding: 16 }}>
        {/* Sidebar */}
        <aside style={{ width: 220, flexShrink: 0 }}>
          <div className="vault-section">
            <div className="vault-heading" style={{ marginBottom: 8 }}>Quick Actions</div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
              <QuickActionLink label="Add New Task" onClick={() => setShowCreate(true)} />
              <QuickActionLink label="Add New Project" onClick={() => navigate('/projects')} />
              <QuickActionLink label="Add New Habit" onClick={() => navigate('/habits')} />
              <QuickActionLink label="New Habit Goal" onClick={() => navigate('/goals')} />
              <QuickActionLink
                label={`Change Grid (${gridCols})`}
                icon="▦"
                onClick={() => {
                  const next = (gridCols % 4) + 1;
                  setGridColsState(next);
                  setGridCols(next);
                  toast(`Grid set to ${next} columns`, 'info');
                }}
              />
              <QuickActionLink label="Database" icon="🗄" onClick={() => navigate('/vault-database')} />
            </div>
          </div>
          {summary && (
            <HabitStatistics
              stats={summary.current_week_streaks.map((s) => ({
                habit: s.habit,
                records_this_month: s.streak,
                days_missed: 0,
                is_new_record: false,
              }))}
            />
          )}
        </aside>

        {/* Main content */}
        <main style={{ flex: 1, minWidth: 0 }}>
          {loading && <div className="vault-muted">Loading…</div>}
          {error && <div style={{ color: 'var(--habit-red)' }}>{error}</div>}
          {!loading && !error && (
            <>
              {summary && (
                <PerformanceWidget
                  date={new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
                  overdueTasks={summary.overdue_tasks}
                  overdueLastWeek={summary.overdue_last_week ?? 0}
                  streakGraph={firstHabitStats?.streak_graph ?? []}
                />
              )}

              {/* Row 1: Habit Streak & Goal Tracking (Phase 49) */}
              <section className="vault-section" style={{ marginTop: 16 }}>
                <div className="vault-heading" style={{ marginBottom: 10 }}>Habits</div>
                <div className="vault-grid vault-grid-fixed">
                  {habits.length === 0 && <div className="vault-muted">No habits yet — add one to start tracking.</div>}
                  {habits.slice(0, 4).map((h) => (
                    <HabitStreakCard
                      key={h.id}
                      habit={h}
                      logs={heatmaps[h.id] ?? []}
                      onLog={onLogToday}
                      onToggleToday={onToggleToday}
                    />
                  ))}
                </div>
              </section>

              {/* Row 2: Daily-Habit Tracking (Phase 50) */}
              <section className="vault-section">
                <div className="vault-heading" style={{ marginBottom: 10 }}>Daily Habit Tracking</div>
                {habits.length === 0 ? (
                  <div className="vault-muted">No habits to track yet.</div>
                ) : (
                  <HeatmapCarousel label="Habit heatmaps">
                    {habits.slice(0, 4).map((h) => (
                      <div key={h.id} className="heatmap-carousel-item" style={{ width: 280 }}>
                        <HabitHeatmapCard habit={h} days={heatmaps[h.id] ?? []} onComplete={onLogToday} />
                      </div>
                    ))}
                  </HeatmapCarousel>
                )}
              </section>

              {/* Row 3: Task section with vault tabs (Phase 51) */}
              <section className="vault-section">
                <div className="vault-heading" style={{ marginBottom: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>Tasks</span>
                  {/* Defect #54 fix: prominent create button right at the section heading. */}
                  <QuickActionLink label="＋ New Task" onClick={() => setShowCreate(true)} />
                </div>
                <VaultTabs
                  tabs={['Today', 'Unrelated Tasks', "This Week's Progress", 'Inbox', 'Completed']}
                  active={activeTab}
                  onChange={changeTab}
                />
                {activeTab === "This Week's Progress" && (
                  <div style={{ marginTop: 12 }}>
                    <WeekProgressStrip tasks={allTasks} />
                  </div>
                )}
                <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {tabTasks.length === 0 && <div className="vault-muted">No tasks in this view.</div>}
                  {tabTasks.map((t) => (
                    <TaskCard
                      key={t.id}
                      task={t}
                      projectName={t.project_id != null ? projectNames[t.project_id] : undefined}
                      onComplete={onCompleteTask}
                      onEdit={setEditingTask}
                    />
                  ))}
                </div>
              </section>

              {/* Row 4: Project Manager + Weekly Calendar (Phase 52) */}
              <section className="vault-section">
                <div className="vault-heading" style={{ marginBottom: 10 }}>Project Manager</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 16, alignItems: 'start' }}>
                  <div className="vault-grid">
                    {projects.length === 0 && <div className="vault-muted">No projects yet.</div>}
                    {projects.map((p) => (
                      <ProjectCard
                        key={p.id}
                        project={p}
                        summary={projectSummaries[p.id] ?? { total_tasks: 0, incomplete_tasks: 0, days_to_go: null, deadline_status: 'No deadline' }}
                        onEdit={(proj) => setEditingProject(proj)}
                        onDrill={(proj) => setDrillProject(proj)}
                      />
                    ))}
                  </div>
                  {calendar && (
                    <WeeklyCalendarRow
                      days={calendar.days.map((d) => ({ date: d.date, label: d.label, tasks: d.tasks }))}
                      onComplete={onCompleteTask}
                      onOpen={(dayOfWeek) => navigate(`/schedule?day_of_week=${dayOfWeek}`)}
                    />
                  )}
                </div>
              </section>
            </>
          )}
        </main>
      </div>

      {/* Task create/edit modal (Phases 58 & 64) */}
      {(editingTask || showCreate) && (
        <TaskCreateModal
          projects={projects}
          task={editingTask}
          onClose={() => { setEditingTask(null); setShowCreate(false); }}
          onSaved={refreshTasks}
        />
      )}

      {/* Project create/edit modal (Phases 66 & 69) */}
      {(editingProject !== null) && (
        <ProjectModal
          project={editingProject}
          onClose={() => setEditingProject(null)}
          onSaved={refreshProjectSummaries}
        />
      )}

      {/* Project drill-down (Phase 70) */}
      {(drillProject !== null) && (
        <ProjectDetail
          projectId={drillProject.id}
          onClose={() => setDrillProject(null)}
        />
      )}
    </div>
  );
};
