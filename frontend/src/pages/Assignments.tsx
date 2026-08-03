import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Assignment, Course } from '../services/api';

export const Assignments = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    endpoints.assignments.list().then(setAssignments).catch(() => {});
    endpoints.courses.list().then(setCourses).catch(() => {});
  }, []);

  const courseName = (cid: number) => courses.find((c) => c.id === cid)?.title ?? '—';

  return (
    <div>
      <Header title="Assignments" />
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Title</th><th>Course</th><th>Due</th><th>Status</th></tr></thead>
          <tbody>
            {assignments.map((a) => (
              <tr key={a.id}>
                <td>{a.title}</td>
                <td style={{ color: 'var(--text-secondary)' }}>{courseName(a.course_id)}</td>
                <td style={{ fontSize: '0.8rem' }}>{a.due_date}</td>
                <td><span className={`badge badge-${a.status === 'Completed' ? 'success' : a.status === 'In progress' ? 'warning' : 'info'}`}>{a.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
