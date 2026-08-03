import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import { getMaterialsByUnit, getMaterialById, uploadMaterial, downloadMaterial } from '../controllers/materialController';
import { authenticate } from '../middleware/auth';

// Configure multer for local file storage
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(__dirname, '../../uploads');
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
    const ext = path.extname(file.originalname);
    cb(null, `${uniqueSuffix}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB limit
  fileFilter: (req, file, cb) => {
    const allowedExtensions = ['.pdf', '.ppt', '.pptx', '.doc', '.docx'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowedExtensions.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type'));
    }
  },
});

const router = Router({ mergeParams: true });

// GET /units/:unitId/materials
router.get('/', getMaterialsByUnit);

// POST /units/:unitId/materials (authenticated)
router.post('/', authenticate, upload.single('file'), uploadMaterial);

// GET /materials/:id
router.get('/:id', getMaterialById);

// GET /materials/:id/download
router.get('/:id/download', downloadMaterial);

export default router;
