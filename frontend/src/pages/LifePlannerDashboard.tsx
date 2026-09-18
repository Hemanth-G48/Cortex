import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../services/api';
import type {
  DailyLogStats, EisenhowerMatrix, EisenhowerTask, Goal,
  LifeArea, LifePlannerEvent, LifePlannerSummary, Reminder, Task,
  WeeklyReviewResponse,
} from '../services/api';
import { useToast } from '../hooks/useToast';
import { DailyLogWidget } from '../components/lifeplanner/DailyLogWidget';
import { MiniCalendar } from '../components/lifeplanner/MiniCalendar';
import { LifeNavigationGrid } from '../components/lifeplanner/LifeNavigationGrid';
import { RadarChartWidget, type LifeDimension } from '../components/lifeplanner/RadarChartWidget';
import { QuickTaskManager } from '../components/lifeplanner/QuickTaskManager';
import { LifeAreasGoals } from '../components/lifeplanner/LifeAreasGoals';
import { EisenhowerMatrixWidget } from '../components/lifeplanner/EisenhowerMatrixWidget';
import { toIso } from '../utils/vaultDates';

const EMPTY_MATRIX: EisenhowerMatrix = {
  urgent_important: [],
  important_not_urgent: [],
  urgent_not_important: [],
  not_important: [],
};

export const LifePlannerDashboard = () => {
  const { toast } = useToast();
  const [summary, setSummary] = useState<LifePlannerSummary | null>(null);
  const [stats, setStats] = useState<DailyLogStats | null>(null);
  const [matrix, setMatrix] = useState<EisenhowerMatrix>(EMPTY_MATRIX);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [areas, setAreas] = useState<LifeArea[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [todos, setTodos] = useState<Task[]>([]);
  const [events, setEvents] = useState<LifePlannerEvent[]>([]);
  // Defect #39: the radar's axes are sourced from the vault's review engine.
  const [weeklyReview, setWeeklyReview] = useState<WeeklyReviewResponse | null>(null);
  const [logBusy, setLogBusy] = useState(false);

  const load = useCallback(() => {
    Promise.all([
      endpoints.lifePlanner.summary().catch(() => null),
      endpoints.dailyLogs.stats().catch(() => null),
      endpoints.eisenhower.matrix().catch(() => EMPTY_MATRIX),
      endpoints.goals.list().catch(() => []),
      endpoints.lifeAreas.list().catch(() => []),
      endpoints.reminders.list().catch(() => []),
      endpoints.tasks.list().catch(() => []),
      endpoints.events.today().catch(() => []),
      endpoints.kb.weeklyReview.overview().catch(() => null),
    ]).then(([s, st, m, g, a, r, t, e, wr]) => {
      setSummary(s);
      setStats(st);
      setMatrix(m);
      setGoals(g);
      setAreas(a);
      setReminders(r);
      setTodos(t);
      setEvents(e);
      setWeeklyReview(wr);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Radar axes are live data only (defect #39): each life area contributes its
  // stored progress (GET /life-areas) and the weekly review contributes the
  // vault mastery score of the topics it flagged weak this week
  // (GET /api/kb/weekly-review → weak_topics[].score, a real 0–100 metric).
  // No client-side label table and no synthetic padding axis.
  const dimensions: LifeDimension[] = [
    ...areas.map((a) => ({ label: a.name, value: a.progress_percent })),
    ...(weeklyReview?.weak_topics ?? []).map((t) => ({ label: t.topic_name, value: t.score })),
  ];

  const handleLogIn = () => {
    setLogBusy(true);
    endpoints.dailyLogs.create({ user_id: 1, date: toIso(new Date()), time_focused: 45, status: 'active' })
      .then(() => {
        toast('Logged in for today (+45 min focused)', 'success');
        load();
      })
      .catch(() => toast('Could not log today', 'error'))
      .finally(() => setLogBusy(false));
  };

  const toggleReminder = (r: Reminder) => {
    endpoints.reminders.update(r.id, { is_completed: !r.is_completed })
      .then(() => { toast(r.is_completed ? 'Reminder reopened' : 'Reminder done', 'success'); load(); })
      .catch(() => toast('Could not update reminder', 'error'));
  };

  const toggleTodo = (t: Task) => {
    const completed = t.status === 'Completed';
    endpoints.tasks.update(t.id, { status: completed ? 'Not started' : 'Completed' })
      .then(() => { toast(completed ? 'Task reopened' : 'Task completed 🎉', 'success'); load(); })
      .catch(() => toast('Could not update task', 'error'));
  };

  const toggleEvent = (e: LifePlannerEvent) => {
    endpoints.events.update(e.id, { is_completed: !e.is_completed })
      .then(() => { toast(e.is_completed ? 'Event reopened' : 'Event done', 'success'); load(); })
      .catch(() => toast('Could not update event', 'error'));
  };

  const achieveGoal = (g: Goal) => {
    if (g.is_completed) return;
    endpoints.goals.complete(g.id)
      .then(() => { toast(`Achieved: ${g.title} 🏆`, 'success'); load(); })
      .catch(() => toast('Could not mark goal achieved', 'error'));
  };

  // Defect #66: the Eisenhower quick-complete also writes the completion into
  // today's vault daily note (POST /api/kb/daily-notes/complete-task),
  // best-effort so a vault without a reachable daily-life folder still works.
  const completeMatrixTask = (t: EisenhowerTask) => {
    endpoints.eisenhower.completeTask(t.id)
      .then(() => {
        endpoints.kb.dailyNotes
          .completeTask({ title: t.title, task_id: t.id, source: 'eisenhower' })
          .catch(() => {});
        toast(`Done: ${t.title}`, 'success');
        load();
      })
      .catch(() => toast('Could not complete task', 'error'));
  };

  return (
    <div data-theme="life-planner" className="fade-in">
      <header className="header">
        <h1>🌱 Life Planner</h1>
      </header>

      <div className="lp-layout">
        <aside className="lp-sidebar">
          {summary && stats && (
            <DailyLogWidget summary={summary} stats={stats} onLogIn={handleLogIn} busy={logBusy} />
          )}
          <MiniCalendar />
        </aside>

        <div className="lp-main">
          <LifeNavigationGrid />

          <div className="card" style={{ padding: '1rem 1.25rem' }}>
            <RadarChartWidget dimensions={dimensions} />
          </div>

          <QuickTaskManager
            reminders={reminders}
            todos={todos}
            events={events}
            onToggleReminder={toggleReminder}
            onToggleTodo={toggleTodo}
            onToggleEvent={toggleEvent}
          />

          <LifeAreasGoals areas={areas} goals={goals} onAchieve={achieveGoal} />

          <EisenhowerMatrixWidget matrix={matrix} onComplete={completeMatrixTask} />
        </div>
      </div>
    </div>
  );
};
