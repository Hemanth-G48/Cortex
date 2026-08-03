import { Router } from 'express';
import { getCoursesByInstitution, getCourseById, createCourse } from '../controllers/courseController';
import { adminMiddleware } from '../middleware/auth';

const router = Router({ mergeParams: true }); // Enable access to params from parent router

// Routes: /institutions/:institutionId/courses
router.get('/', getCoursesByInstitution);
router.post('/', adminMiddleware, createCourse);

// Routes: /courses/:id
router.get('/:id', getCourseById);

export default router;
