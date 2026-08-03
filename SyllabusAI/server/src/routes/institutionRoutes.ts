import { Router } from 'express';
import { getInstitutions, getAllInstitutions, getInstitutionById, createInstitution, updateInstitutionStatus } from '../controllers/institutionController';
import { adminMiddleware } from '../middleware/auth';

const router = Router();

// Public: get active (approved) institutions
router.get('/', getInstitutions);

// Admin: get ALL institutions including pending
router.get('/admin/all', adminMiddleware, getAllInstitutions);

// Public: get institution by ID with courses
router.get('/:id', getInstitutionById);

// Admin: create institution
router.post('/', adminMiddleware, createInstitution);

// Admin: approve/reject institution
router.patch('/:id/status', adminMiddleware, updateInstitutionStatus);

export default router;
