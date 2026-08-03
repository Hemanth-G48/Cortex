import { Router } from 'express';
import { getUnitsBySubject, getUnitById, createUnit } from '../controllers/unitController';
import { adminMiddleware } from '../middleware/auth';

const router = Router({ mergeParams: true });

// GET /subjects/:subjectId/units
router.get('/', getUnitsBySubject);

// POST /subjects/:subjectId/units (admin only)
router.post('/', adminMiddleware, createUnit);

// GET /units/:id
router.get('/:id', getUnitById);

export default router;
