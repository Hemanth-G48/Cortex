import type { Course } from '../../services/api';
import { CourseCard } from './CourseCard';

interface CourseCardsGridProps {
  courses: Course[];
  title: string;
  emoji?: string;
  /** Shown when the group is empty so the user knows why and what to do. */
  emptyHint?: string;
}

/**
 * Fully-visible responsive grid of course cards — no horizontal scrolling.
 *
 * Every subject in the group is laid out on the page at once (wrapping grid),
 * so a user can see all of their Second Brain subjects without sliding a row.
 */
export const CourseCardsGrid = ({ courses, title, emoji, emptyHint }: CourseCardsGridProps) => (
  <div className="course-source-group" data-testid={`course-group-${title.toLowerCase().replace(/\s+/g, '-')}`}>
    <div className="course-group-header">
      <h2>
        {emoji && <span className="emoji">{emoji}</span>}
        {title}
      </h2>
      <span className="badge badge-muted">
        {courses.length} course{courses.length === 1 ? '' : 's'}
      </span>
    </div>
    {courses.length === 0 ? (
      emptyHint ? <div className="notice notice-info">{emptyHint}</div> : null
    ) : (
      <div className="course-grid">
        {courses.map((c) => (
          <CourseCard key={c.id} course={c} />
        ))}
      </div>
    )}
  </div>
);
