import { Request, Response } from 'express';
import { Institution, Course } from '../models';

export const getInstitutions = async (req: Request, res: Response): Promise<void> => {
  try {
    const institutions = await Institution.findAll({
      where: { isActive: true },
      order: [['name', 'ASC']],
    });
    res.json({ institutions });
  } catch (error) {
    console.error('Error fetching institutions:', error);
    res.status(500).json({ message: 'Error fetching institutions' });
  }
};

export const getAllInstitutions = async (req: Request, res: Response): Promise<void> => {
  try {
    const institutions = await Institution.findAll({
      order: [['createdAt', 'DESC']],
    });
    res.json({ institutions });
  } catch (error) {
    console.error('Error fetching all institutions:', error);
    res.status(500).json({ message: 'Error fetching institutions' });
  }
};

export const getInstitutionById = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = req.params.id as string;
    const institution = await Institution.findByPk(id, {
      include: [{ model: Course, as: 'courses', where: { isActive: true }, required: false }]
    });

    if (!institution) {
      res.status(404).json({ message: 'Institution not found' });
      return;
    }

    res.json({ institution });
  } catch (error) {
    console.error('Error fetching institution:', error);
    res.status(500).json({ message: 'Error fetching institution' });
  }
};

export const createInstitution = async (req: Request, res: Response): Promise<void> => {
  try {
    const { name, shortName, description } = req.body;

    if (!name || !shortName) {
      res.status(400).json({ message: 'Name and short name are required' });
      return;
    }

    const institution = await Institution.create({ name, shortName, description });
    res.status(201).json({ institution });
  } catch (error) {
    console.error('Error creating institution:', error);
    res.status(500).json({ message: 'Error creating institution' });
  }
};

export const updateInstitutionStatus = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = req.params.id as string;
    const { isActive } = req.body;

    const institution = await Institution.findByPk(id);
    if (!institution) {
      res.status(404).json({ message: 'Institution not found' });
      return;
    }

    await institution.update({ isActive });

    res.json({
      message: isActive ? 'Institution approved' : 'Institution deactivated',
      institution,
    });
  } catch (error) {
    console.error('Error updating institution status:', error);
    res.status(500).json({ message: 'Error updating institution status' });
  }
};
