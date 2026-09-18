import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { courseThumbnail } from '../../utils/placeholders';
import type { Course } from '../../services/api';

interface CourseCardProps {
  course: Course;
}

/** Course card with SVG thumbnail and mouse‑track 3D tilt */
export const CourseCard = ({ course }: CourseCardProps) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ rx: 0, ry: 0 });

  const handleMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setTilt({ rx: (y - 0.5) * -12, ry: (x - 0.5) * 12 });
  };

  const handleLeave = () => setTilt({ rx: 0, ry: 0 });

  const isSecondBrain =
    course.source_type === 'kb_tag' || course.source_type === 'kb_folder' || !!course.kb_tag_id;
  const sourceLabel = course.source_type === 'classroom' ? 'Google Classroom' : isSecondBrain ? 'Second Brain' : 'Manual';

  // For Second Brain subjects the meaningful number is the linked-note count
  // (``total_assignments`` mirrors it for legacy UI, so fall back on it).
  const kbNoteCount = course.kb_document_count ?? (isSecondBrain ? course.total_assignments : null);

  return (
    <Link
      to={`/courses/${course.id}`}
      className="course-card-link"
      style={{ textDecoration: 'none', color: 'inherit' }}
    >
      <div
        ref={cardRef}
        className="course-card"
        onMouseMove={handleMove}
        onMouseLeave={handleLeave}
        style={{
          transform: `perspective(600px) rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg)`,
        }}
      >
        <div className="course-card-thumb">
          {/* Folder-derived subjects can carry an accent color from their
              index.md frontmatter — rendered as a top strip on the card. */}
          {course.color && (
            <div className="course-card-accent" style={{ background: course.color }} />
          )}
          <img src={course.image_url ?? courseThumbnail(course.title)} alt={course.title} />
        </div>
        <div className="course-card-body">
          <h3 className="course-card-title">
            {course.color && <span className="course-color-dot" style={{ background: course.color }} />}
            {course.title}
          </h3>
          {course.description && <p className="course-card-desc">{course.description}</p>}
          <div className="course-card-stats">
            {kbNoteCount != null ? (
              <span>📄 {kbNoteCount} note{kbNoteCount === 1 ? '' : 's'}</span>
            ) : (
              <>
                <span>Assignments: {course.current_assignment}/{course.total_assignments}</span>
                <span>Exams: {course.next_exam ?? 0}/{course.total_exams}</span>
              </>
            )}
          </div>
          <div className="course-card-badges">
            <span className={`badge badge-${course.status === 'Completed' ? 'success' : course.status === 'In progress' ? 'warning' : 'info'}`}>
              {course.status}
            </span>
            <span className={`badge ${isSecondBrain ? 'badge-info' : course.source_type === 'classroom' ? 'badge-success' : 'badge-muted'}`}>
              {sourceLabel}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
};
