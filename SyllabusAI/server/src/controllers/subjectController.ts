import { Request, Response } from 'express';
import { Subject, Unit } from '../models';

export const getSubjectsByCourse = async (req: Request, res: Response): Promise<void> => {
  try {
    const courseId = req.params.courseId as string;
    const subjects = await Subject.findAll({
      where: { courseId, isActive: true },
      order: [['semester', 'ASC'], ['name', 'ASC']],
      include: [{ model: Unit, as: 'units', where: { isActive: true }, required: false }],
    });

    const subjectsWithCount = subjects.map(subject => ({
      ...subject.toJSON(),
      unitCount: (subject as any).units?.length || 0,
    }));

    res.json({ subjects: subjectsWithCount });
  } catch (error) {
    console.error('Error fetching subjects:', error);
    res.status(500).json({ message: 'Error fetching subjects' });
  }
};

export const getSubjectById = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = req.params.id as string;
    const subject = await Subject.findByPk(id, {
      include: [{ model: Unit, as: 'units', where: { isActive: true }, required: false }],
    });

    if (!subject) {
      res.status(404).json({ message: 'Subject not found' });
      return;
    }

    res.json({ subject });
  } catch (error) {
    console.error('Error fetching subject:', error);
    res.status(500).json({ message: 'Error fetching subject' });
  }
};

export const createSubject = async (req: Request, res: Response): Promise<void> => {
  try {
    const courseId = req.params.courseId as string;
    const { name, code, semester, credits, description } = req.body;

    const subject = await Subject.create({
      courseId: parseInt(courseId),
      name,
      code,
      semester,
      credits,
      description
    });

    res.status(201).json({ subject });
  } catch (error) {
    console.error('Error creating subject:', error);
    res.status(500).json({ message: 'Error creating subject' });
  }
};
