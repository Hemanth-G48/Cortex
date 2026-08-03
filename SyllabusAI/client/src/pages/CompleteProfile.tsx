import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import authService from '../services/authService';
import institutionService, { type Institution, type Course } from '../services/institutionService';

export function CompleteProfile() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();

  const [firstName, setFirstName] = useState(user?.firstName || '');
  const [lastName, setLastName] = useState(user?.lastName || '');
  const [institutionId, setInstitutionId] = useState<number | undefined>();
  const [courseId, setCourseId] = useState<number | undefined>();
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // If profile is already complete, redirect
    if (user?.institutionId && user?.courseId) {
      navigate('/dashboard', { replace: true });
      return;
    }
    institutionService.getInstitutions()
      .then(setInstitutions)
      .catch(console.error);
  }, [user, navigate]);

  useEffect(() => {
    if (institutionId) {
      setCourseId(undefined);
      institutionService.getCoursesByInstitution(institutionId)
        .then(setCourses)
        .catch(console.error);
    } else {
      setCourses([]);
      setCourseId(undefined);
    }
  }, [institutionId]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (!institutionId || !courseId) {
      setError('Please select your institution and course');
      return;
    }

    setIsLoading(true);
    try {
      const { user: updatedUser } = await authService.completeProfile({
        firstName: firstName || undefined,
        lastName: lastName || undefined,
        institutionId,
        courseId,
      });
      updateUser(updatedUser);
      navigate('/dashboard', { replace: true });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      setError(error.response?.data?.message || 'Failed to save. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12 bg-surface-dark">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-text">Complete your profile</h1>
          <p className="mt-2 text-text-secondary">
            Welcome{user?.firstName ? `, ${user.firstName}` : ''}! Select your college and course to get started.
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-border p-8">
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">First Name</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full px-4 py-2.5 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                  placeholder="John"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Last Name</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full px-4 py-2.5 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                  placeholder="Doe"
                />
              </div>
            </div>

            <div className="p-4 bg-surface-dark rounded-xl space-y-4">
              <p className="text-sm font-medium text-text">Select your college & course <span className="text-red-500">*</span></p>
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">Institution</label>
                <select
                  value={institutionId || ''}
                  onChange={(e) => setInstitutionId(e.target.value ? Number(e.target.value) : undefined)}
                  required
                  className="w-full px-4 py-2.5 border border-border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                >
                  <option value="">Select your college</option>
                  {institutions.map(inst => (
                    <option key={inst.id} value={inst.id}>
                      {inst.name} ({inst.shortName})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">Course</label>
                <select
                  value={courseId || ''}
                  onChange={(e) => setCourseId(e.target.value ? Number(e.target.value) : undefined)}
                  disabled={!institutionId}
                  required
                  className="w-full px-4 py-2.5 border border-border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">{institutionId ? 'Select your course' : 'Select institution first'}</option>
                  {courses.map(course => (
                    <option key={course.id} value={course.id}>
                      {course.name} ({course.code})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !institutionId || !courseId}
              className="w-full py-2.5 bg-primary text-white font-semibold rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Saving...' : 'Continue to Dashboard'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
