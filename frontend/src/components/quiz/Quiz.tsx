import { useState } from 'react';
import type { Quiz as QuizModel, QuizAttemptResult } from '../../services/api';

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

interface QuizProps {
  quiz: QuizModel;
  onSubmit: (answers: (number | null)[]) => Promise<QuizAttemptResult | null>;
  onExit: () => void;
  onRetry?: () => void;
}

/** Full quiz flow: question navigation, selection, results with explanations (plan Phase 66). */
export const Quiz = ({ quiz, onSubmit, onExit, onRetry }: QuizProps) => {
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<(number | null)[]>(() => quiz.questions.map(() => null));
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<QuizAttemptResult | null>(null);

  const questions = quiz.questions;
  const total = questions.length;
  const answered = answers.filter((a) => a !== null).length;
  const allAnswered = answered === total;

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await onSubmit(answers);
      if (r) setResult(r);
    } finally {
      setSubmitting(false);
    }
  };

  const retry = () => {
    setAnswers(questions.map(() => null));
    setResult(null);
    setIndex(0);
  };

  // ── Results view ──
  if (result) {
    const pct = result.percentage;
    const color = pct >= 80 ? 'var(--success)' : pct >= 50 ? 'var(--warning)' : 'var(--danger)';
    const verdict = pct >= 80 ? 'Excellent!' : pct >= 50 ? 'Good effort' : 'Keep practicing';
    return (
      <div className="card" style={{ borderColor: color }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', color }}>{verdict}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              You scored {result.score} / {result.total}
            </div>
          </div>
          <div
            role="img"
            aria-label={`Score ${Math.round(pct)} percent`}
            style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '1.05rem',
              color,
              background: `${color}1a`,
              border: `3px solid ${color}`,
            }}
          >
            {Math.round(pct)}%
          </div>
        </div>

        <div style={{ marginTop: '1.25rem', display: 'grid', gap: '0.6rem' }}>
          {questions.map((q, qi) => {
            const item = result.results.find((r) => r.question_index === qi);
            const ok = item?.correct ?? false;
            return (
              <div
                key={qi}
                style={{
                  border: `1px solid ${ok ? 'var(--success)' : 'var(--danger)'}`,
                  borderRadius: 'var(--radius)',
                  padding: '0.7rem 0.9rem',
                  background: ok ? 'var(--success-muted, transparent)' : 'var(--danger-muted, transparent)',
                }}
              >
                <div style={{ fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                  {ok ? '✅' : '❌'} Q{qi + 1}. {q.question}
                </div>
                {!ok && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Correct answer: <strong>{LETTERS[item?.correct_index ?? q.correct_index]} — {q.options[item?.correct_index ?? q.correct_index]}</strong>
                  </div>
                )}
                {q.explanation && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{q.explanation}</div>
                )}
              </div>
            );
          })}
        </div>

        {!!result.xp_awarded && (
          <div
            role="status"
            aria-label={`Earned ${result.xp_awarded} XP`}
            style={{
              marginTop: '1rem',
              padding: '0.6rem 0.9rem',
              borderRadius: 'var(--radius)',
              background: 'var(--success-muted, rgba(52,211,153,0.12))',
              border: '1px solid var(--success)',
              fontSize: '0.85rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            ⚡ +{result.xp_awarded} XP earned for passing!
          </div>
        )}

        <div className="modal-actions" style={{ marginTop: '1.25rem' }}>
          <button type="button" className="btn btn-ghost" onClick={onExit}>Close</button>
          <button type="button" className="btn btn-primary" onClick={retry}>↺ Retake</button>
          {onRetry && (
            <button type="button" className="btn btn-ghost" onClick={onRetry}>✨ New questions</button>
          )}
        </div>
      </div>
    );
  }

  // ── Question view ──
  const q = questions[index];
  return (
    <div className="card">
      {/* Progress */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Question {index + 1} of {total}</span>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{answered} / {total} answered</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, overflow: 'hidden', background: 'var(--bg-hover)', marginBottom: '1.25rem' }}>
        <div style={{ height: '100%', width: `${((index + 1) / total) * 100}%`, background: 'var(--accent)', borderRadius: 3, transition: 'width 0.3s ease' }} />
      </div>

      <h3 style={{ fontSize: '1rem', fontWeight: 700, lineHeight: 1.5, marginBottom: '1.25rem' }}>{q.question}</h3>

      <div
        role="radiogroup"
        aria-label="Answer options"
        onKeyDown={(e) => {
          // Arrow keys move the selection (a11y Phase 93); Enter/Space handled natively.
          if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
            e.preventDefault();
            setAnswers((prev) => prev.map((a, i) => (i === index ? Math.min(q.options.length - 1, (a ?? -1) + 1) : a)));
          } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
            e.preventDefault();
            setAnswers((prev) => prev.map((a, i) => (i === index ? Math.max(0, (a ?? q.options.length) - 1) : a)));
          }
        }}
        style={{ display: 'grid', gap: '0.55rem' }}
      >
        {q.options.map((opt, oi) => {
          const selected = answers[index] === oi;
          return (
            <button
              key={oi}
              type="button"
              role="radio"
              aria-checked={selected}
              aria-label={`Option ${LETTERS[oi] ?? oi + 1}: ${opt}`}
              onClick={() => setAnswers((prev) => prev.map((a, i) => (i === index ? oi : a)))}
              style={{
                textAlign: 'left',
                padding: '0.7rem 0.9rem',
                borderRadius: 'var(--radius)',
                border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
                background: selected ? 'var(--accent-muted, transparent)' : 'var(--bg-hover)',
                cursor: 'pointer',
                color: 'var(--text-primary)',
                fontSize: '0.88rem',
                display: 'flex',
                gap: '0.6rem',
                alignItems: 'flex-start',
                transition: 'border-color 0.15s ease, background 0.15s ease',
              }}
            >
              <span style={{ fontWeight: 800, color: selected ? 'var(--accent)' : 'var(--text-muted)' }}>
                {LETTERS[oi] ?? oi + 1}
              </span>
              <span>{opt}</span>
            </button>
          );
        })}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.6rem', marginTop: '1.25rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '0.6rem' }}>
          <button type="button" className="btn btn-ghost" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
            ← Prev
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => setIndex((i) => Math.min(total - 1, i + 1))}
            disabled={index === total - 1}
          >
            Next →
          </button>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => void submit()} disabled={!allAnswered || submitting}>
          {submitting ? 'Submitting…' : `Submit Quiz`}
        </button>
      </div>
      {!allAnswered && (
        <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          Answer all {total} questions to submit.
        </p>
      )}
    </div>
  );
};
