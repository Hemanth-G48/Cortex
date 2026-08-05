import { Header } from '../layout/Header';

export const TeacherHeader = () => (
  <div className="page-section">
    <Header title="Teacher Dashboard" />
    <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
      Manage your students, broadcast courses, assignments, todos, books, and schedule items to one or all students.
    </p>
  </div>
);
