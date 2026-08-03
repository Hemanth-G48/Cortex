import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import aiService, { type Quiz as QuizType, type QuizResult } from '../services/aiService';

interface QuizProps {
  quiz: QuizType;
  onClose: () => void;
}

export function Quiz({ quiz, onClose }: QuizProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<(number | null)[]>(new Array(quiz.questions.length).fill(null));
  const [submitted, setSubmitted] = useState(false);
  const [results, setResults] = useState<QuizResult[] | null>(null);
  const [score, setScore] = useState(0);
  const [percentage, setPercentage] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const question = quiz.questions[currentIndex];
  const allAnswered = answers.every(a => a !== null);

  const selectAnswer = (optionIndex: number) => {
    if (submitted) return;
    const newAnswers = [...answers];
    newAnswers[currentIndex] = optionIndex;
    setAnswers(newAnswers);
  };

  const handleSubmit = async () => {
    if (!allAnswered) return;
    setSubmitting(true);
    try {
      const result = await aiService.submitQuizAttempt(quiz.id, answers as number[]);
      setResults(result.results);
      setScore(result.score);
      setPercentage(result.percentage);
      setSubmitted(true);
      setCurrentIndex(0);
    } catch (error) {
      console.error('Submit failed:', error);
    } finally {
      setSubmitting(false);
    }
  };

  // Results screen
  if (submitted && results) {
    return (
      <div className="bg-white rounded-2xl border border-border p-6">
        <div className="text-center mb-8">
          <div className={`text-6xl font-bold mb-2 ${percentage >= 70 ? 'text-green-500' : percentage >= 40 ? 'text-amber-500' : 'text-red-500'}`}>
            {percentage}%
          </div>
          <p className="text-text-secondary">
            You got {score} out of {results.length} correct
          </p>
        </div>

        <div className="space-y-4 max-h-96 overflow-y-auto">
          {results.map((result, i) => (
            <div
              key={i}
              className={`p-4 rounded-xl border ${result.isCorrect ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}
            >
              <div className="flex items-start gap-3">
                <span className={`text-lg ${result.isCorrect ? 'text-green-500' : 'text-red-500'}`}>
                  {result.isCorrect ? '✓' : '✗'}
                </span>
                <div>
                  <p className="font-medium text-text text-sm">{result.question}</p>
                  {!result.isCorrect && (
                    <p className="text-xs text-red-600 mt-1">
                      Your answer: {quiz.questions[i].options[result.userAnswer]}
                    </p>
                  )}
                  <p className="text-xs text-green-700 mt-1">
                    Correct: {quiz.questions[i].options[result.correctAnswer]}
                  </p>
                  <p className="text-xs text-text-secondary mt-2 italic">{result.explanation}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={onClose}
          className="mt-6 w-full py-2.5 bg-primary text-white font-semibold rounded-lg hover:bg-primary-dark transition-colors"
        >
          Done
        </button>
      </div>
    );
  }

  // Quiz screen
  return (
    <div className="bg-white rounded-2xl border border-border p-6">
      {/* Progress */}
      <div className="flex items-center justify-between mb-6">
        <span className="text-sm text-text-secondary">
          Question {currentIndex + 1} of {quiz.questions.length}
        </span>
        <span className="text-sm text-text-secondary">
          {answers.filter(a => a !== null).length} answered
        </span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2 mb-6">
        <div
          className="bg-primary rounded-full h-2 transition-all"
          style={{ width: `${((currentIndex + 1) / quiz.questions.length) * 100}%` }}
        />
      </div>

      {/* Question */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          <h3 className="text-lg font-semibold text-text mb-4">{question.question}</h3>
          <div className="space-y-3">
            {question.options.map((option, i) => (
              <button
                key={i}
                onClick={() => selectAnswer(i)}
                className={`w-full text-left p-4 rounded-xl border transition-all ${
                  answers[currentIndex] === i
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'border-border hover:border-primary/30 text-text'
                }`}
              >
                <span className="font-medium mr-3">{String.fromCharCode(65 + i)}.</span>
                {option}
              </button>
            ))}
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6">
        <button
          onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
          disabled={currentIndex === 0}
          className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text transition-colors disabled:opacity-40 bg-transparent border-none cursor-pointer"
        >
          Previous
        </button>

        {currentIndex < quiz.questions.length - 1 ? (
          <button
            onClick={() => setCurrentIndex(currentIndex + 1)}
            className="px-6 py-2 text-sm font-medium bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!allAnswered || submitting}
            className="px-6 py-2 text-sm font-medium bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {submitting ? 'Submitting...' : 'Submit Quiz'}
          </button>
        )}
      </div>

      {/* Quick navigation dots */}
      <div className="flex flex-wrap gap-2 mt-4 justify-center">
        {quiz.questions.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrentIndex(i)}
            className={`w-8 h-8 rounded-full text-xs font-medium transition-all border-none cursor-pointer ${
              i === currentIndex
                ? 'bg-primary text-white'
                : answers[i] !== null
                ? 'bg-primary/20 text-primary'
                : 'bg-gray-100 text-text-secondary'
            }`}
          >
            {i + 1}
          </button>
        ))}
      </div>
    </div>
  );
}
