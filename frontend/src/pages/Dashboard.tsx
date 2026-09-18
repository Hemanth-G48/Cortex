import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Course, Task, Assignment, Exam, Goal } from '../services/api';
import { StudentRadarChart } from '../components/visualization/RadarChart';
import { MiniTodoList, type MiniTodoItem } from '../components/taskmanager/MiniTodoList';
import { SkeletonStatTile, SkeletonTable } from '../components/shared/Skeleton';
import type { KbGraphResponse } from '../services/api';
import { RemindersList } from '../components/taskmanager/RemindersList';
import { AcademicCalendar } from '../components/calendar/AcademicCalendar';
import { BrainDumpWidget } from '../components/BrainDumpWidget';
import { DayProgressWidget } from '../components/schedule/DayProgressWidget';
import { TodayCaptures } from '../components/kb/TodayCaptures';
import { EnrollmentBadge } from '../components/dashboard/EnrollmentBadge';
import { CurriculumSection } from '../components/dashboard/CurriculumSection';
import { NextUpCard } from '../components/kb/NextUpCard';
import { AiInsightsCard } from '../components/kb/AiInsightsCard';

export const Dashboard = () => {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<Course[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [todayOverview, setTodayOverview] = useState<Awaited<ReturnType<typeof endpoints.kb.today.overview>> | null>(null);
  const [radarData, setRadarData] = useState<{ graph: KbGraphResponse | null; stats: Awaited<ReturnType<typeof endpoints.kb.stats>> | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      endpoints.courses.list(),
      endpoints.tasks.list(),
      endpoints.assignments.list(),
      endpoints.exams.list(),
      endpoints.goals.list(),
      endpoints.kb.today.overview().catch(() => null),
      // Defect #2 fix: drive radar axes from live vault graph + stats instead of
      // the static RadarChart.defaultData snapshot.
      Promise.all([
        endpoints.kb.graph.list().catch(() => null),
        endpoints.kb.stats().catch(() => null),
      ]).then(([graph, stats]) => ({ graph, stats })).catch(() => null),
    ]).then(([courses, tasks, assignments, exams, goals, today, radar]) => {
      setCourses(courses);
      setTasks(tasks);
      setAssignments(assignments);
      setExams(exams);
      setGoals(goals);
      setTodayOverview(today);
      setRadarData(radar);
    }).catch(() => setError('Could not load dashboard data — is the backend running?'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Merge tasks + today's captured docs into one pending count (defect #1 fix).
  const pendingTasks = tasks.filter((t) => t.status !== 'Completed').length
    + (todayOverview?.morning?.captured_documents?.length ?? 0);

  // Defect #2 fix: build radar data from live vault graph + stats.
  function buildRadarData(
    graph: KbGraphResponse | null | undefined,
    stats: Awaited<ReturnType<typeof endpoints.kb.stats>> | null | undefined,
  ): { subject: string; score: number; fullMark: number }[] {
    if (!graph || !stats) return [];
    const docCount = graph.total_nodes ?? 0;
    const edgeCount = graph.total_edges ?? 0;
    const conceptCount = stats.concept_count ?? 0;
    const embeddedDocs = stats.embedded_documents ?? 0;
    const tagCount = stats.tag_count ?? 0;
    const dupCount = stats.duplicate_count ?? 0;
    // Scale each dimension to 0..100 from a reasonable max so the radar stays
    // readable without per-user calibration.
    const clamp = (v: number, max: number) => Math.min(100, Math.round((v / max) * 100));
    return [
      { subject: 'Documents', score: clamp(docCount, 50), fullMark: 100 },
      { subject: 'Concepts', score: clamp(conceptCount, 30), fullMark: 100 },
      { subject: 'Connections', score: clamp(edgeCount, 100), fullMark: 100 },
      { subject: 'Embedded', score: clamp(embeddedDocs, 20), fullMark: 100 },
      { subject: 'Tags', score: clamp(tagCount, 40), fullMark: 100 },
      { subject: 'Health', score: dupCount === 0 ? 100 : Math.max(10, 100 - dupCount * 10), fullMark: 100 },
    ];
  }
  const completedAssignments = assignments.filter((a) => a.status === 'Completed').length;
  const upcomingExams = exams.filter((e) => e.status === 'Not started').length;
  const avgProgress = goals.length
    ? Math.round(goals.reduce((s, g) => s + g.progress_percentage, 0) / goals.length)
    : 0;

  // Defect #10 fix: completing a task from the dashboard updates the list.
  // Vault-captured documents (string ids like "doc-3") have no task row yet —
  // they are informational until promoted, so only numeric task ids toggle.
  const completeTask = (t: MiniTodoItem) => {
    if (t.status === 'Completed' || typeof t.id !== 'number') return;
    endpoints.tasks.update(t.id, { status: 'Completed' }).then(() => load());
  };

  return (
    <div>
      <Header title="Dashboard" />
      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}
      <div className="stat-grid">
        {loading ? (
          // Defects #01/#05 fix: skeletons instead of flashing 0s.
          <>
            <SkeletonStatTile /><SkeletonStatTile /><SkeletonStatTile /><SkeletonStatTile /><SkeletonStatTile />
          </>
        ) : (
          <>
            <div className="stat-tile"><div className="label">Courses</div><div className="value">{courses.length}</div></div>
            <div className="stat-tile"><div className="label">Pending Tasks</div><div className="value">{pendingTasks}</div></div>
            <div className="stat-tile"><div className="label">Assignments Done</div><div className="value">{completedAssignments}/{assignments.length}</div></div>
            <div className="stat-tile"><div className="label">Upcoming Exams</div><div className="value">{upcomingExams}</div></div>
            <div className="stat-tile"><div className="label">Goal Progress</div><div className="value">{avgProgress}%</div></div>
          </>
        )}
      </div>

      <div className="page-section" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <BrainDumpWidget />
        <DayProgressWidget />
      </div>

      {/* QuestLog (Idea 95): cached AI productivity insights from real stats */}
      <div className="page-section" style={{ maxWidth: 560 }}>
        <AiInsightsCard />
      </div>

      {/* Phase 8 (Idea 75): single best cross-subject next action with reasons */}
      <div className="page-section" style={{ maxWidth: 560 }}>
        <NextUpCard />
      </div>

      {/* Phase 4 (Idea 35): what the vault captured today, joined with schedule + journal */}
      <div className="page-section" style={{ maxWidth: 560 }}>
        <TodayCaptures />
      </div>

      <div className="page-section" style={{ maxWidth: 420 }}>
        <EnrollmentBadge />
      </div>

      <div className="page-section">
        <h2>Courses</h2>
        <div className="card-grid">
          {courses.map((c) => (
            <div className="card" key={c.id}>
              <Link to={`/courses/${c.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <h3 style={{ marginBottom: '0.5rem' }}>{c.title}</h3>
              <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <span>Assignments: {c.current_assignment}/{c.total_assignments}</span>
                <span>Exams: {c.next_exam ?? 0}/{c.total_exams}</span>
              </div>
              <div style={{ marginTop: '0.5rem' }}>
                <span className={`badge badge-${c.status === 'Completed' ? 'success' : c.status === 'In progress' ? 'warning' : 'info'}`}>{c.status}</span>
              </div>
              </Link>
            </div>
          ))}
        </div>
      </div>

      <div className="page-section">
        <h2>Recent Tasks</h2>
        <div className="card">
          {loading ? (
            SkeletonTable(5)
          ) : (
            <table className="data-table">
              <thead><tr><th>Task</th><th>Subject</th><th>Priority</th><th>Status</th></tr></thead>
              <tbody>
                {tasks.slice(0, 5).map((t) => (
                  // Defect #04 fix: rows link to task management.
                  <tr key={t.id} style={{ cursor: 'pointer' }} onClick={() => navigate('/tasks')}>
                    <td>{t.title}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{t.subject_tag ?? '—'}</td>
                    <td><span className={`priority-${t.priority_tag?.toLowerCase()}`}>{t.priority_tag ?? '—'}</span></td>
                    <td><span className={`badge badge-${t.status === 'Completed' ? 'success' : t.status === 'In progress' ? 'warning' : 'info'}`}>{t.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="dashboard-grid-2col">
        <div className="page-section">
          <h2>Overview</h2>
          <div className="card">
            {/* Defect #2 fix: radar axes derived from live vault graph + stats
                instead of the static RadarChart.defaultData snapshot. */}
            <StudentRadarChart
              data={radarData ? buildRadarData(radarData.graph, radarData.stats) : undefined}
            />
          </div>
        </div>

        <div className="page-section">
          <h2>Quick Tasks</h2>
          <div className="card">
            {/* Vault-prioritized top-5 (defect #11 fix): merge tasks with today's
                captured documents so the list reflects what the Second Brain captured. */}
            <MiniTodoList
              tasks={[
                ...todayOverview?.morning?.captured_documents?.map((d) => ({
                  id: `doc-${d.id}`,
                  title: d.title,
                  status: 'In progress',
                  subject_tag: null,
                  priority_tag: d.quality_score === null ? null : 'High',
                  priority_quadrant: null,
                  due_date: null,
                  user_id: 1,
                  project_id: null,
                })) ?? [],
                ...tasks,
              ].sort((a, b) => {
                // Today's captured docs bubble to the top.
                const aToday = String(a.id).startsWith('doc-') ? 0 : 1;
                const bToday = String(b.id).startsWith('doc-') ? 0 : 1;
                if (aToday !== bToday) return aToday - bToday;
                return (a.title || '').localeCompare(b.title || '');
              }).slice(0, 5)}
              onToggle={completeTask}
            />
          </div>
          <h2 style={{ marginTop: '1.5rem' }}>Reminders</h2>
          <div className="card">
            <RemindersList />
          </div>
        </div>
      </div>

      <div className="page-section">
        <AcademicCalendar tasks={tasks} />
      </div>

      <CurriculumSection />
    </div>
  );
};
