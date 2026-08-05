import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { useUnit } from '../hooks/useUnit';
import { useQuiz } from '../hooks/useQuiz';
import { useToast } from '../hooks/useToast';
import { endpoints } from '../services/api';
import type { SummaryGenerateResponse } from '../services/api';
import { MaterialSearch } from '../components/curriculum/MaterialSearch';
import { MaterialUpload } from '../components/curriculum/MaterialUpload';
import { MaterialList } from '../components/curriculum/MaterialList';
import { Quiz } from '../components/quiz/Quiz';
import { QuizHistory } from '../components/quiz/QuizHistory';
import { Summary } from '../components/summary/Summary';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';

const PAGE_SIZE = 20;
const DIFFICULTIES = ['easy', 'medium', 'hard'] as const;

export const Unit = () => {
  const { id } = useParams<{ id: string }>();
  const unitId = Number(id);
  const { toast } = useToast();
  const { unit, subject, materials, total, page, query, loading, error, refresh, setQuery, setPage } = useUnit(unitId);

  const [difficulty, setDifficulty] = useState<(typeof DIFFICULTIES)[number]>('medium');
  const quiz = useQuiz();

  const [summary, setSummary] = useState<SummaryGenerateResponse | null>(null);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);

  // Refresh the quiz history panel after a new attempt is scored.
  useEffect(() => {
    if (quiz.phase === 'result') setHistoryKey((k) => k + 1);
  }, [quiz.phase]);

  const generateQuiz = () => {
    setSummary(null);
    void quiz.generate(unitId, difficulty, 10);
  };

  const generateSummary = async () => {
    setGeneratingSummary(true);
    setSummary(null);
    try {
      const res = await endpoints.summaries.generate([unitId]);
      setSummary(res);
      toast(res.cached ? 'Loaded from cache' : 'Summary generated', res.cached ? 'info' : 'success');
    } catch {
      toast('Could not generate summary', 'error');
    } finally {
      setGeneratingSummary(false);
    }
  };

  if (loading) {
    return (
      <div className="fade-in">
        <Header title="Unit" />
        <SkeletonCard />
      </div>
    );
  }

  if (error || !unit) {
    return (
      <div className="fade-in">
        <Header title="Unit" />
        <EmptyState icon="📚" title="Unit not found" message={error || 'This unit may have been removed.'}
          action={subject ? <Link className="btn btn-primary" to={`/subjects/${subject.id}`}>Back to subject</Link> : undefined} />
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="fade-in">
      <Header title={`Unit ${unit.unit_number} — ${unit.name}`} />

      <nav aria-label="Breadcrumb" style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem', display: 'flex', gap: '0.35rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <Link to="/browse" style={{ color: 'var(--accent)', textDecoration: 'none' }}>Browse</Link>
        <span>/</span>
        {subject && (
          <>
            <Link to={`/subjects/${subject.id}`} style={{ color: 'var(--accent)', textDecoration: 'none' }}>{subject.code}</Link>
            <span>/</span>
          </>
        )}
        <span>Unit {unit.unit_number}</span>
      </nav>

      {unit.description && (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.5rem' }}>{unit.description}</p>
      )}

      {/* AI actions */}
      <div className="page-section">
        <h2>AI Study Tools</h2>
        <div className="card" style={{ display: 'grid', gap: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <label style={{ display: 'grid', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>Difficulty</span>
              <select aria-label="Quiz difficulty" value={difficulty} onChange={(e) => setDifficulty(e.target.value as (typeof DIFFICULTIES)[number])}>
                {DIFFICULTIES.map((d) => (
                  <option key={d} value={d}>{d[0].toUpperCase() + d.slice(1)}</option>
                ))}
              </select>
            </label>
            <button type="button" className="btn btn-primary" onClick={generateQuiz} disabled={quiz.phase === 'generating' || quiz.phase === 'submitting'}>
              {quiz.phase === 'generating' ? 'Generating quiz…' : '🧠 Generate Quiz'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => void generateSummary()} disabled={generatingSummary}>
              {generatingSummary ? 'Generating…' : '✨ Generate Summary'}
            </button>
          </div>

          {quiz.error && <p style={{ fontSize: '0.78rem', color: 'var(--danger)' }}>{quiz.error}</p>}

          {quiz.quiz && (
            <Quiz
              quiz={quiz.quiz}
              onSubmit={quiz.submit}
              onExit={quiz.reset}
              onRetry={() => void quiz.generate(unitId, difficulty, 10)}
            />
          )}

          {summary && (
            <Summary title={`Unit ${unit.unit_number} summary`} content={summary.summary.content} keyPoints={summary.summary.key_points} cached={summary.cached} />
          )}
        </div>
      </div>

      {/* Materials */}
      <div className="page-section">
        <h2>Materials</h2>
        <div style={{ display: 'grid', gap: '1rem', marginBottom: '1rem' }}>
          <MaterialUpload unitId={unitId} subjectId={unit?.subject_id} onUploaded={() => void refresh()} />
          <MaterialSearch value={query} onChange={(q) => { setQuery(q); setPage(1); }} />
        </div>
        <MaterialList items={materials} />
        {totalPages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Prev</button>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Page {page} of {totalPages}</span>
            <button type="button" className="btn btn-ghost btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next →</button>
          </div>
        )}
      </div>

      {/* Quiz history */}
      <div className="page-section">
        <h2>Quiz History</h2>
        <QuizHistory reloadKey={historyKey} />
      </div>
    </div>
  );
};

export default Unit;
