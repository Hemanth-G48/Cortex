import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import institutionService, { type Institution, type Course } from '../services/institutionService';
import subjectService, { type Subject } from '../services/subjectService';

export function Browse() {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedInstitution, setSelectedInstitution] = useState<number | ''>('');
  const [selectedCourse, setSelectedCourse] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    institutionService.getInstitutions().then(setInstitutions).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedInstitution) {
      institutionService.getCoursesByInstitution(selectedInstitution as number)
        .then(setCourses)
        .catch(console.error);
    } else {
      setCourses([]);
    }
    setSelectedCourse('');
    setSubjects([]);
  }, [selectedInstitution]);

  useEffect(() => {
    if (selectedCourse) {
      setLoading(true);
      subjectService.getSubjectsByCourse(selectedCourse as number)
        .then(setSubjects)
        .catch(console.error)
        .finally(() => setLoading(false));
    } else {
      setSubjects([]);
    }
  }, [selectedCourse]);

  return (
    <div className="min-h-screen bg-surface-dark">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-text">Browse Materials</h1>
          <p className="text-text-secondary mt-1">
            Find study materials by selecting your institution and course
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-2xl border border-border p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text mb-1.5">Institution</label>
              <select
                value={selectedInstitution}
                onChange={(e) => setSelectedInstitution(e.target.value ? Number(e.target.value) : '')}
                className="w-full px-4 py-2.5 border border-border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              >
                <option value="">All Institutions</option>
                {institutions.map(inst => (
                  <option key={inst.id} value={inst.id}>
                    {inst.name} ({inst.shortName})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text mb-1.5">Course</label>
              <select
                value={selectedCourse}
                onChange={(e) => setSelectedCourse(e.target.value ? Number(e.target.value) : '')}
                disabled={!selectedInstitution}
                className="w-full px-4 py-2.5 border border-border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors disabled:opacity-50"
              >
                <option value="">{selectedInstitution ? 'Select a course' : 'Select institution first'}</option>
                {courses.map(course => (
                  <option key={course.id} value={course.id}>
                    {course.name} ({course.code})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div>
          </div>
        )}

        {/* Subjects */}
        {!loading && subjects.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {subjects.map(subject => (
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
                    Sem {subject.semester} | {subject.credits} cr
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
        )}

        {/* Empty states */}
        {!loading && !selectedCourse && (
          <div className="bg-white rounded-2xl border border-border p-12 text-center">
            <div className="text-5xl mb-4">🔍</div>
            <h2 className="text-xl font-semibold text-text mb-2">Select filters to browse</h2>
            <p className="text-text-secondary">
              Choose an institution and course to see available subjects and materials.
            </p>
          </div>
        )}

        {!loading && selectedCourse && subjects.length === 0 && (
          <div className="bg-white rounded-2xl border border-border p-12 text-center">
            <div className="text-5xl mb-4">📭</div>
            <h2 className="text-xl font-semibold text-text mb-2">No subjects found</h2>
            <p className="text-text-secondary">
              No subjects have been added for this course yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
