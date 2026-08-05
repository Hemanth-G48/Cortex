import { useCallback, useState } from 'react';
import { endpoints } from '../services/api';
import type { Quiz, QuizAttemptResult } from '../services/api';

export type QuizPhase = 'idle' | 'generating' | 'answering' | 'submitting' | 'result';

interface UseQuizReturn {
  phase: QuizPhase;
  quiz: Quiz | null;
  result: QuizAttemptResult | null;
  error: string;
  generate: (unitId: number, difficulty: string, numQuestions?: number) => Promise<void>;
  submit: (answers: (number | null)[]) => Promise<QuizAttemptResult | null>;
  reset: () => void;
}

/** Orchestrates quiz generation → answering → scoring (plan Phase 67). */
export const useQuiz = (): UseQuizReturn => {
  const [phase, setPhase] = useState<QuizPhase>('idle');
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [result, setResult] = useState<QuizAttemptResult | null>(null);
  const [error, setError] = useState('');

  const generate = useCallback(async (unitId: number, difficulty: string, numQuestions = 10) => {
    setPhase('generating');
    setError('');
    setResult(null);
    try {
      const q = await endpoints.quizzes.generate(unitId, numQuestions, difficulty);
      setQuiz(q);
      setPhase('answering');
    } catch (e) {
      setError(e instanceof Error ? e.message.replace('API ', '') : 'Could not generate quiz');
      setPhase('idle');
    }
  }, []);

  const submit = useCallback(async (answers: (number | null)[]): Promise<QuizAttemptResult | null> => {
    if (!quiz) return null;
    setPhase('submitting');
    setError('');
    try {
      const r = await endpoints.quizzes.attempt(quiz.id, answers);
      setResult(r);
      setPhase('result');
      return r;
    } catch (e) {
      setError(e instanceof Error ? e.message.replace('API ', '') : 'Could not submit quiz');
      setPhase('answering');
      return null;
    }
  }, [quiz]);

  const reset = useCallback(() => {
    setPhase('idle');
    setQuiz(null);
    setResult(null);
    setError('');
  }, []);

  return { phase, quiz, result, error, generate, submit, reset };
};
