import { useRef, useState } from 'react';
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

  return (
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
        <img src={courseThumbnail(course.title)} alt={course.title} />
      </div>
      <div className="course-card-body">
        <h3 className="course-card-title">{course.title}</h3>
        <div className="course-card-stats">
          <span>Assignments: {course.current_assignment}/{course.total_assignments}</span>
          <span>Exams: {course.next_exam ?? 0}/{course.total_exams}</span>
        </div>
        <span className={`badge badge-${course.status === 'Completed' ? 'success' : course.status === 'In progress' ? 'warning' : 'info'}`}>
          {course.status}
        </span>
      </div>
    </div>
  );
};
