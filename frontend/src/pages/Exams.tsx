import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Exam, Course } from '../services/api';

export const Exams = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    endpoints.exams.list().then(setExams).catch(() => {});
    endpoints.courses.list().then(setCourses).catch(() => {});
  }, []);

  const courseName = (cid: number) => courses.find((c) => c.id === cid)?.title ?? '—';

  return (
    <div>
      <Header title="Exams" />
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Exam</th><th>Course</th><th>Date</th><th>Status</th></tr></thead>
          <tbody>
            {exams.map((e) => (
              <tr key={e.id}>
                <td>{e.title}</td>
                <td style={{ color: 'var(--text-secondary)' }}>{courseName(e.course_id)}</td>
                <td style={{ fontSize: '0.8rem' }}>{e.date}</td>
                <td><span className={`badge badge-${e.status === 'Completed' ? 'success' : 'info'}`}>{e.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
