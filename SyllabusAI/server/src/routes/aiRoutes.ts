import { Router } from 'express';
import { createQuiz, submitQuizAttempt, getQuizHistory, createSummary } from '../controllers/aiController';
import { authenticate } from '../middleware/auth';

const router = Router();

// All AI routes require authentication
router.use(authenticate);

// Quiz endpoints
router.post('/quiz', createQuiz);
router.post('/quiz/:quizId/attempt', submitQuizAttempt);
router.get('/quiz/history', getQuizHistory);

// Summary endpoints
router.post('/summarize', createSummary);

export default router;
