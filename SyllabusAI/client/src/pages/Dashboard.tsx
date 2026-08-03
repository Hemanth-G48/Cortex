import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import subjectService, { type Subject } from '../services/subjectService';

export function Dashboard() {
  const { user } = useAuth();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.courseId) {
      subjectService.getSubjectsByCourse(user.courseId)
        .then(setSubjects)
        .catch(console.error)
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [user?.courseId]);

  // Group subjects by semester
  const semesters = subjects.reduce((acc, subject) => {
    const sem = subject.semester;
    if (!acc[sem]) acc[sem] = [];
    acc[sem].push(subject);
    return acc;
  }, {} as Record<number, Subject[]>);

  return (
    <div className="min-h-screen bg-surface-dark">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-text">
            Welcome back, {user?.firstName}!
          </h1>
          <div className="flex flex-wrap items-center gap-3 mt-2">
            {user?.institution && (
              <span className="inline-flex items-center px-3 py-1 bg-primary/10 text-primary text-sm font-medium rounded-full">
                {user.institution.shortName}
              </span>
            )}
            {user?.course && (
              <span className="inline-flex items-center px-3 py-1 bg-secondary/10 text-secondary text-sm font-medium rounded-full">
                {user.course.name}
              </span>
            )}
          </div>
        </div>

        {/* No course selected */}
        {!user?.courseId && (
          <div className="bg-white rounded-2xl border border-border p-8 text-center">
            <div className="text-4xl mb-4">🎓</div>
            <h2 className="text-xl font-semibold text-text mb-2">No course selected</h2>
            <p className="text-text-secondary mb-4">
              Update your profile to select your college and course to see your subjects.
            </p>
            <Link to="/browse" className="text-primary font-medium hover:underline">
              Browse all materials instead
            </Link>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div>
          </div>
        )}

        {/* Subjects by Semester */}
        {!loading && Object.keys(semesters).length > 0 && (
          <div className="space-y-8">
            {Object.entries(semesters)
              .sort(([a], [b]) => Number(a) - Number(b))
              .map(([semester, semSubjects]) => (
                <div key={semester}>
                  <h2 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
                    <span className="w-8 h-8 bg-primary/10 text-primary rounded-lg flex items-center justify-center text-sm font-bold">
                      {semester}
                    </span>
                    Semester {semester}
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {semSubjects.map(subject => (
                      <Link
                        key={subject.id}
                        to={`/subjects/${subject.id}`}
                        className="bg-white rounded-xl border border-border p-5 hover:border-primary/30 hover:shadow-md transition-all group no-underline"
                      >
                        <div className="flex justify-between items-start mb-3">
                          <span className="text-xs font-mono text-text-secondary bg-surface-dark px-2 py-0.5 rounded">
                            {subject.code}
                          </span>
                          <span className="text-xs text-text-secondary">
                            {subject.credits} credits
                          </span>
                        </div>
                        <h3 className="text-base font-semibold text-text group-hover:text-primary transition-colors">
                          {subject.name}
                        </h3>
                        {subject.unitCount !== undefined && (
                          <p className="text-sm text-text-secondary mt-2">
                            {subject.unitCount} {subject.unitCount === 1 ? 'unit' : 'units'}
                          </p>
                        )}
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        )}

        {/* Empty state with course but no subjects */}
        {!loading && user?.courseId && subjects.length === 0 && (
          <div className="bg-white rounded-2xl border border-border p-8 text-center">
            <div className="text-4xl mb-4">📖</div>
            <h2 className="text-xl font-semibold text-text mb-2">No subjects yet</h2>
            <p className="text-text-secondary">
              Subjects haven't been added for your course yet. Check back soon!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
