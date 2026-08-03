import { Router } from 'express';
import authRoutes from './auth';
import institutionRoutes from './institutionRoutes';
import courseRoutes from './courseRoutes';
import subjectRoutes from './subjectRoutes';
import unitRoutes from './unitRoutes';
import materialRoutes from './materialRoutes';
import aiRoutes from './aiRoutes';

const router = Router();

// Health check
router.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Auth routes
router.use('/auth', authRoutes);

// Institution routes
router.use('/institutions', institutionRoutes);

// Course routes (nested under institutions + standalone)
router.use('/institutions/:institutionId/courses', courseRoutes);
router.use('/courses', courseRoutes);

// Subject routes (nested under courses + standalone)
router.use('/courses/:courseId/subjects', subjectRoutes);
router.use('/subjects', subjectRoutes);

// Unit routes (nested under subjects + standalone)
router.use('/subjects/:subjectId/units', unitRoutes);
router.use('/units', unitRoutes);

// Material routes (nested under units + standalone)
router.use('/units/:unitId/materials', materialRoutes);
router.use('/materials', materialRoutes);

// AI routes
router.use('/ai', aiRoutes);

export default router;
