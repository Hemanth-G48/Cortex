import api from './api';

export interface QuizQuestion {
  question: string;
  options: string[];
  correctAnswer: number;
  explanation: string;
}

export interface Quiz {
  id: number;
  unitId: number;
  questions: QuizQuestion[];
  difficulty: string;
  createdAt: string;
}

export interface QuizResult {
  question: string;
  userAnswer: number;
  correctAnswer: number;
  isCorrect: boolean;
  explanation: string;
}

export interface QuizAttemptResponse {
  attempt: any;
  score: number;
  totalQuestions: number;
  percentage: number;
  results: QuizResult[];
}

export interface SummaryData {
  id: number;
  unitIds: number[];
  content: string;
  keyPoints: string[];
  createdAt: string;
}

const aiService = {
  async generateQuiz(unitId: number, numQuestions = 10, difficulty = 'medium'): Promise<Quiz> {
    const response = await api.post<{ quiz: Quiz }>('/ai/quiz', { unitId, numQuestions, difficulty });
    return response.data.quiz;
  },

  async submitQuizAttempt(quizId: number, answers: number[]): Promise<QuizAttemptResponse> {
    const response = await api.post<QuizAttemptResponse>(`/ai/quiz/${quizId}/attempt`, { answers });
    return response.data;
  },

  async getQuizHistory(): Promise<any[]> {
    const response = await api.get<{ attempts: any[] }>('/ai/quiz/history');
    return response.data.attempts;
  },

  async generateSummary(unitIds: number[]): Promise<{ summary: SummaryData; cached: boolean }> {
    const response = await api.post<{ summary: SummaryData; cached: boolean }>('/ai/summarize', { unitIds });
    return response.data;
  },
};

export default aiService;
