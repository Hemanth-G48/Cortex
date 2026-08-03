import { Request, Response } from 'express';
import { Unit, Material } from '../models';

export const getUnitsBySubject = async (req: Request, res: Response): Promise<void> => {
  try {
    const subjectId = req.params.subjectId as string;
    const units = await Unit.findAll({
      where: { subjectId, isActive: true },
      order: [['unitNumber', 'ASC']],
      include: [{ model: Material, as: 'materials', where: { isActive: true }, required: false }],
    });

    const unitsWithCount = units.map(unit => ({
      ...unit.toJSON(),
      materialCount: (unit as any).materials?.length || 0,
    }));

    res.json({ units: unitsWithCount });
  } catch (error) {
    console.error('Error fetching units:', error);
    res.status(500).json({ message: 'Error fetching units' });
  }
};

export const getUnitById = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = req.params.id as string;
    const unit = await Unit.findByPk(id, {
      include: [{ model: Material, as: 'materials', where: { isActive: true }, required: false }],
    });

    if (!unit) {
      res.status(404).json({ message: 'Unit not found' });
      return;
    }

    res.json({ unit });
  } catch (error) {
    console.error('Error fetching unit:', error);
    res.status(500).json({ message: 'Error fetching unit' });
  }
};

export const createUnit = async (req: Request, res: Response): Promise<void> => {
  try {
    const subjectId = req.params.subjectId as string;
    const { unitNumber, name, description } = req.body;

    if (!unitNumber || !name) {
      res.status(400).json({ message: 'Unit number and name are required' });
      return;
    }

    const unit = await Unit.create({
      subjectId: parseInt(subjectId),
      unitNumber,
      name,
      description,
    });

    res.status(201).json({ unit });
  } catch (error) {
    console.error('Error creating unit:', error);
    res.status(500).json({ message: 'Error creating unit' });
  }
};
