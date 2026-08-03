import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import subjectService from '../services/subjectService';
import unitService, { type Unit } from '../services/unitService';
import aiService, { type SummaryData } from '../services/aiService';
import { Summary } from '../components/Summary';

export function SubjectPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [subject, setSubject] = useState<any>(null);
  const [units, setUnits] = useState<Unit[]>([]);
  const [loading, setLoading] = useState(true);

  // Multi-unit summary
  const [selectedUnits, setSelectedUnits] = useState<number[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState('');

  useEffect(() => {
    if (!id) return;
    const subjectId = Number(id);

    Promise.all([
      subjectService.getSubjectById(subjectId),
      unitService.getUnitsBySubject(subjectId),
    ])
      .then(([subjectData, unitsData]) => {
        setSubject(subjectData);
        setUnits(unitsData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  const toggleUnit = (unitId: number) => {
    setSelectedUnits(prev =>
      prev.includes(unitId) ? prev.filter(id => id !== unitId) : [...prev, unitId]
    );
  };

  const handleMultiSummary = async () => {
    if (selectedUnits.length === 0) return;
    setGeneratingSummary(true);
    setSummaryError('');
    try {
      const { summary: data } = await aiService.generateSummary(selectedUnits);
      setSummary(data);
    } catch (error: any) {
      setSummaryError(error.response?.data?.message || 'Failed to generate summary');
    } finally {
      setGeneratingSummary(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!subject) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-text-secondary">Subject not found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-dark">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb */}
        <nav className="mb-6 text-sm text-text-secondary">
          <Link to="/dashboard" className="hover:text-primary no-underline">Dashboard</Link>
          <span className="mx-2">/</span>
          <span className="text-text">{subject.name}</span>
        </nav>

        {/* Header */}
        <div className="bg-white rounded-2xl border border-border p-6 mb-8">
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <span className="text-xs font-mono text-text-secondary bg-surface-dark px-2 py-0.5 rounded">
              {subject.code}
            </span>
            <span className="text-xs text-text-secondary">Semester {subject.semester}</span>
            <span className="text-xs text-text-secondary">{subject.credits} credits</span>
          </div>
          <h1 className="text-2xl font-bold text-text">{subject.name}</h1>
          {subject.description && (
            <p className="text-text-secondary mt-2">{subject.description}</p>
          )}
        </div>

        {/* Units */}
        <h2 className="text-lg font-semibold text-text mb-4">Units ({units.length})</h2>

        {units.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {units.map(unit => (
              <div key={unit.id} className="relative">
                {/* Checkbox for multi-unit summary */}
                {user && (
                  <button
                    onClick={() => toggleUnit(unit.id)}
                    className={`absolute top-3 right-3 w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all z-10 cursor-pointer ${
                      selectedUnits.includes(unit.id)
                        ? 'border-primary bg-primary text-white'
                        : 'border-border bg-white hover:border-primary/50'
                    }`}
                  >
                    {selectedUnits.includes(unit.id) && <span className="text-xs">✓</span>}
                  </button>
                )}
                <Link
                  to={`/units/${unit.id}`}
                  className="block bg-white rounded-xl border border-border p-5 hover:border-primary/30 hover:shadow-md transition-all group no-underline"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-primary/10 text-primary rounded-lg flex items-center justify-center font-bold text-sm">
                      {unit.unitNumber}
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-text group-hover:text-primary transition-colors">
                        {unit.name}
                      </h3>
                      {unit.materialCount !== undefined && (
                        <p className="text-xs text-text-secondary">
                          {unit.materialCount} {unit.materialCount === 1 ? 'material' : 'materials'}
                        </p>
                      )}
                    </div>
                  </div>
                  {unit.description && (
                    <p className="text-sm text-text-secondary line-clamp-2">{unit.description}</p>
                  )}
                  <div className="flex gap-2 mt-4">
                    <span className="text-xs px-2 py-1 bg-blue-50 text-blue-600 rounded-md">Materials</span>
                    <span className="text-xs px-2 py-1 bg-purple-50 text-purple-600 rounded-md">Quiz</span>
                    <span className="text-xs px-2 py-1 bg-green-50 text-green-600 rounded-md">Summary</span>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-border p-8 text-center mb-8">
            <div className="text-4xl mb-4">📦</div>
            <h3 className="text-lg font-semibold text-text mb-2">No units yet</h3>
            <p className="text-text-secondary">Units haven't been added for this subject yet.</p>
          </div>
        )}

        {/* Multi-Unit Summary Section */}
        {user && units.length > 0 && (
          <div className="mt-8">
            {summary ? (
              <Summary summary={summary} onClose={() => setSummary(null)} />
            ) : (
              <div className="bg-white rounded-2xl border border-border p-6">
                <h3 className="text-lg font-semibold text-text mb-2">Multi-Unit Summary</h3>
                <p className="text-sm text-text-secondary mb-4">
                  Select units above using the checkboxes, then generate a combined AI summary.
                </p>

                {summaryError && (
                  <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm mb-4">
                    {summaryError}
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <button
                    onClick={handleMultiSummary}
                    disabled={selectedUnits.length === 0 || generatingSummary}
                    className="bg-primary text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {generatingSummary ? (
                      <>
                        <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                        Generating...
                      </>
                    ) : (
                      `Generate Summary (${selectedUnits.length} unit${selectedUnits.length !== 1 ? 's' : ''})`
                    )}
                  </button>
                  {selectedUnits.length > 0 && (
                    <button
                      onClick={() => setSelectedUnits([])}
                      className="text-sm text-text-secondary hover:text-text bg-transparent border-none cursor-pointer"
                    >
                      Clear selection
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
