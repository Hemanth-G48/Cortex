import { Router } from 'express';
import { getSubjectsByCourse, getSubjectById, createSubject } from '../controllers/subjectController';
import { adminMiddleware } from '../middleware/auth';

const router = Router({ mergeParams: true });

// Routes: /courses/:courseId/subjects
router.get('/', getSubjectsByCourse);
router.post('/', adminMiddleware, createSubject);

// Routes: /subjects/:id
router.get('/:id', getSubjectById);

export default router;
