import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Course } from '../services/api';
import { CourseCardsRow } from '../components/courses/CourseCardsRow';
import { AcademicResourcesGrid } from '../components/resources/AcademicResourcesGrid';

export const Courses = () => {
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    endpoints.courses.list().then(setCourses).catch(() => {});
  }, []);

  const inProgress = courses.filter((c) => c.status === 'In progress' || c.status === 'Not started');
  const completed = courses.filter((c) => c.status === 'Completed');

  return (
    <div>
      <Header title="Courses" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Total</div><div className="value">{courses.length}</div></div>
        <div className="stat-tile"><div className="label">Active</div><div className="value">{inProgress.length}</div></div>
        <div className="stat-tile"><div className="label">Completed</div><div className="value">{completed.length}</div></div>
      </div>

      {inProgress.length > 0 && <CourseCardsRow courses={inProgress} title="In Progress" />}
      {completed.length > 0 && <CourseCardsRow courses={completed} title="Completed" />}

      <AcademicResourcesGrid />
    </div>
  );
};
