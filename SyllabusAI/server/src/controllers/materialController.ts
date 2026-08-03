import { Request, Response } from 'express';
import path from 'path';
import fs from 'fs';
import { Material, Unit } from '../models';

export const getMaterialsByUnit = async (req: Request, res: Response): Promise<void> => {
  try {
    const unitId = req.params.unitId as string;
    const materials = await Material.findAll({
      where: { unitId, isActive: true },
      order: [['createdAt', 'DESC']],
    });
    res.json({ materials });
  } catch (error) {
    console.error('Error fetching materials:', error);
    res.status(500).json({ message: 'Error fetching materials' });
  }
};

export const getMaterialById = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = req.params.id as string;
    const material = await Material.findByPk(id);

    if (!material || !material.isActive) {
      res.status(404).json({ message: 'Material not found' });
      return;
    }

    await material.increment('viewCount');

    res.json({ material });
  } catch (error) {
    console.error('Error fetching material:', error);
    res.status(500).json({ message: 'Error fetching material' });
  }
};

export const uploadMaterial = async (req: Request, res: Response): Promise<void> => {
  try {
    const unitId = req.params.unitId as string;
    const { title, description } = req.body;

    if (!req.file) {
      res.status(400).json({ message: 'No file uploaded' });
      return;
    }

    if (!title) {
      res.status(400).json({ message: 'Title is required' });
      return;
    }

    const unit = await Unit.findByPk(unitId);
    if (!unit) {
      // Clean up uploaded file
      fs.unlinkSync(req.file.path);
      res.status(404).json({ message: 'Unit not found' });
      return;
    }

    const ext = path.extname(req.file.originalname).slice(1).toLowerCase();
    const allowedTypes = ['pdf', 'ppt', 'pptx', 'doc', 'docx'];
    if (!allowedTypes.includes(ext)) {
      fs.unlinkSync(req.file.path);
      res.status(400).json({ message: 'Invalid file type. Allowed: pdf, ppt, pptx, doc, docx' });
      return;
    }

    const material = await Material.create({
      unitId: parseInt(unitId),
      uploadedById: req.user!.id,
      title,
      description,
      fileType: ext as Material['fileType'],
      fileUrl: req.file.path,
      fileSize: req.file.size,
      originalFileName: req.file.originalname,
    });

    res.status(201).json({ material });
  } catch (error) {
    console.error('Error uploading material:', error);
    res.status(500).json({ message: 'Error uploading material' });
  }
};

export const downloadMaterial = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = req.params.id as string;
    const material = await Material.findByPk(id);

    if (!material || !material.isActive) {
      res.status(404).json({ message: 'Material not found' });
      return;
    }

    if (!fs.existsSync(material.fileUrl)) {
      res.status(404).json({ message: 'File not found on server' });
      return;
    }

    await material.increment('downloadCount');

    res.download(material.fileUrl, material.originalFileName);
  } catch (error) {
    console.error('Error downloading material:', error);
    res.status(500).json({ message: 'Error downloading material' });
  }
};
