import type { Course } from '../../services/api';
import { CourseCard } from './CourseCard';

interface CourseCardsRowProps {
  courses: Course[];
  title?: string;
}

/** Horizontally scrolling row of course cards */
export const CourseCardsRow = ({ courses, title }: CourseCardsRowProps) => (
  <div className="page-section">
    {title && <h2>{title}</h2>}
    <div className="course-row">
      {courses.map((c) => (
        <CourseCard key={c.id} course={c} />
      ))}
    </div>
  </div>
);
