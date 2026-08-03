import { Router } from 'express';
import {
  register,
  login,
  googleAuth,
  getProfile,
  updateProfile,
  completeProfile,
  changePassword,
} from '../controllers/authController';
import { authenticate } from '../middleware/auth';

const router = Router();

// Public routes
router.post('/register', register);
router.post('/login', login);
router.post('/google', googleAuth);

// Protected routes
router.get('/profile', authenticate, getProfile);
router.put('/profile', authenticate, updateProfile);
router.put('/complete-profile', authenticate, completeProfile);
router.put('/change-password', authenticate, changePassword);

export default router;
