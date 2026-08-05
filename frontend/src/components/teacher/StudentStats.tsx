import type { TeacherStudentStats } from '../../services/api';

interface StudentStatsProps {
  stats: TeacherStudentStats;
}

export const StudentStats = ({ stats }: StudentStatsProps) => (
  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.75rem' }}>
    <span className="badge badge-info">{stats.courses} courses</span>
    <span className="badge badge-info">{stats.assignments} assignments</span>
    <span className="badge badge-info">{stats.todos} todos</span>
    <span className="badge badge-info">{stats.books} books</span>
    {stats.braindump && <span className="badge" style={{ background: 'var(--success-muted)', color: 'var(--success)' }}>brain dump</span>}
  </div>
);
