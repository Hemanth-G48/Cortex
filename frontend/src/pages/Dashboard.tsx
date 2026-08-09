import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Course, Task, Assignment, Exam, Goal } from '../services/api';
import { StudentRadarChart } from '../components/visualization/RadarChart';
import { MiniTodoList } from '../components/taskmanager/MiniTodoList';
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
  const [courses, setCourses] = useState<Course[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);

  useEffect(() => {
    endpoints.courses.list().then(setCourses).catch(() => {});
    endpoints.tasks.list().then(setTasks).catch(() => {});
    endpoints.assignments.list().then(setAssignments).catch(() => {});
    endpoints.exams.list().then(setExams).catch(() => {});
    endpoints.goals.list().then(setGoals).catch(() => {});
  }, []);

  const pendingTasks = tasks.filter((t) => t.status !== 'Completed').length;
  const completedAssignments = assignments.filter((a) => a.status === 'Completed').length;
  const upcomingExams = exams.filter((e) => e.status === 'Not started').length;
  const avgProgress = goals.length
    ? Math.round(goals.reduce((s, g) => s + g.progress_percentage, 0) / goals.length)
    : 0;

  return (
    <div>
      <Header title="Dashboard" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Courses</div><div className="value">{courses.length}</div></div>
        <div className="stat-tile"><div className="label">Pending Tasks</div><div className="value">{pendingTasks}</div></div>
        <div className="stat-tile"><div className="label">Assignments Done</div><div className="value">{completedAssignments}/{assignments.length}</div></div>
        <div className="stat-tile"><div className="label">Upcoming Exams</div><div className="value">{upcomingExams}</div></div>
        <div className="stat-tile"><div className="label">Goal Progress</div><div className="value">{avgProgress}%</div></div>
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
              <h3 style={{ marginBottom: '0.5rem' }}>{c.title}</h3>
              <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <span>Assignments: {c.current_assignment}/{c.total_assignments}</span>
                <span>Exams: {c.next_exam ?? 0}/{c.total_exams}</span>
              </div>
              <div style={{ marginTop: '0.5rem' }}>
                <span className={`badge badge-${c.status === 'Completed' ? 'success' : c.status === 'In progress' ? 'warning' : 'info'}`}>{c.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="page-section">
        <h2>Recent Tasks</h2>
        <div className="card">
          <table className="data-table">
            <thead><tr><th>Task</th><th>Subject</th><th>Priority</th><th>Status</th></tr></thead>
            <tbody>
              {tasks.slice(0, 5).map((t) => (
                <tr key={t.id}>
                  <td>{t.title}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{t.subject_tag ?? '—'}</td>
                  <td><span className={`priority-${t.priority_tag?.toLowerCase()}`}>{t.priority_tag ?? '—'}</span></td>
                  <td><span className={`badge badge-${t.status === 'Completed' ? 'success' : t.status === 'In progress' ? 'warning' : 'info'}`}>{t.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="dashboard-grid-2col">
        <div className="page-section">
          <h2>Overview</h2>
          <div className="card">
            <StudentRadarChart />
          </div>
        </div>

        <div className="page-section">
          <h2>Quick Tasks</h2>
          <div className="card">
            <MiniTodoList tasks={tasks} />
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
