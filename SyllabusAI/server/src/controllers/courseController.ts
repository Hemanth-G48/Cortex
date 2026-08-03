import { Request, Response } from 'express';
import { Course, Subject } from '../models';

export const getCoursesByInstitution = async (req: Request, res: Response): Promise<void> => {
  try {
    const institutionId = req.params.institutionId as string;
    const courses = await Course.findAll({
      where: { institutionId, isActive: true },
      order: [['name', 'ASC']],
    });
    res.json({ courses });
  } catch (error) {
    console.error('Error fetching courses:', error);
    res.status(500).json({ message: 'Error fetching courses' });
  }
};

export const getCourseById = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = req.params.id as string;
    const course = await Course.findByPk(id, {
      include: [{ model: Subject, as: 'subjects', where: { isActive: true }, required: false }]
    });

    if (!course) {
      res.status(404).json({ message: 'Course not found' });
      return;
    }

    res.json({ course });
  } catch (error) {
    console.error('Error fetching course:', error);
    res.status(500).json({ message: 'Error fetching course' });
  }
};

export const createCourse = async (req: Request, res: Response): Promise<void> => {
  try {
    const institutionId = req.params.institutionId as string;
    const { name, code, description, duration } = req.body;

    const course = await Course.create({
      institutionId: parseInt(institutionId),
      name,
      code,
      description,
      duration
    });

    res.status(201).json({ course });
  } catch (error) {
    console.error('Error creating course:', error);
    res.status(500).json({ message: 'Error creating course' });
  }
};
