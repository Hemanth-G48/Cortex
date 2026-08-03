import { Request, Response } from 'express';
import { Unit, Material, Quiz, QuizAttempt, Summary } from '../models';
import { extractTextFromMultipleFiles } from '../services/textExtractor';
import { generateQuiz, generateSummary, generateMultiUnitSummary } from '../services/groqService';
import { Op } from 'sequelize';

export const createQuiz = async (req: Request, res: Response): Promise<void> => {
  try {
    const { unitId, numQuestions = 10, difficulty = 'medium' } = req.body;

    if (!unitId) {
      res.status(400).json({ message: 'unitId is required' });
      return;
    }

    // Get unit with materials
    const unit = await Unit.findByPk(unitId, {
      include: [{ model: Material, as: 'materials', where: { isActive: true }, required: false }],
    });

    if (!unit) {
      res.status(404).json({ message: 'Unit not found' });
      return;
    }

    const materials = (unit as any).materials || [];
    if (materials.length === 0) {
      res.status(400).json({ message: 'No materials available in this unit to generate a quiz' });
      return;
    }

    // Extract text from all materials
    const files = materials.map((m: any) => ({
      filePath: m.fileUrl,
      fileType: m.fileType,
      title: m.title,
    }));

    const content = await extractTextFromMultipleFiles(files);

    if (!content || content.length < 50) {
      res.status(400).json({ message: 'Not enough text content in materials to generate a quiz' });
      return;
    }

    // Generate quiz via Groq
    const questions = await generateQuiz(content, numQuestions, difficulty);

    // Save quiz to database
    const quiz = await Quiz.create({
      unitId,
      questions,
      difficulty: difficulty as 'easy' | 'medium' | 'hard',
    });

    res.status(201).json({ quiz });
  } catch (error) {
    console.error('Error generating quiz:', error);
    res.status(500).json({ message: 'Error generating quiz. Please try again.' });
  }
};

export const submitQuizAttempt = async (req: Request, res: Response): Promise<void> => {
  try {
    const quizId = req.params.quizId as string;
    const { answers } = req.body;

    if (!answers || !Array.isArray(answers)) {
      res.status(400).json({ message: 'answers array is required' });
      return;
    }

    const quiz = await Quiz.findByPk(quizId);
    if (!quiz) {
      res.status(404).json({ message: 'Quiz not found' });
      return;
    }

    // Score the quiz
    const questions = quiz.questions;
    let score = 0;
    const results = questions.map((q, i) => {
      const isCorrect = answers[i] === q.correctAnswer;
      if (isCorrect) score++;
      return {
        question: q.question,
        userAnswer: answers[i],
        correctAnswer: q.correctAnswer,
        isCorrect,
        explanation: q.explanation,
      };
    });

    // Save attempt
    const attempt = await QuizAttempt.create({
      userId: req.user!.id,
      quizId: parseInt(quizId),
      answers,
      score,
      totalQuestions: questions.length,
    });

    res.status(201).json({
      attempt,
      score,
      totalQuestions: questions.length,
      percentage: Math.round((score / questions.length) * 100),
      results,
    });
  } catch (error) {
    console.error('Error submitting quiz attempt:', error);
    res.status(500).json({ message: 'Error submitting quiz attempt' });
  }
};

export const getQuizHistory = async (req: Request, res: Response): Promise<void> => {
  try {
    const attempts = await QuizAttempt.findAll({
      where: { userId: req.user!.id },
      include: [{ model: Quiz, as: 'quiz', include: [{ model: Unit, as: 'unit' }] }],
      order: [['createdAt', 'DESC']],
      limit: 50,
    });

    res.json({ attempts });
  } catch (error) {
    console.error('Error fetching quiz history:', error);
    res.status(500).json({ message: 'Error fetching quiz history' });
  }
};

export const createSummary = async (req: Request, res: Response): Promise<void> => {
  try {
    const { unitIds } = req.body;

    if (!unitIds || !Array.isArray(unitIds) || unitIds.length === 0) {
      res.status(400).json({ message: 'unitIds array is required' });
      return;
    }

    // Check for cached summary
    const sortedIds = [...unitIds].sort((a, b) => a - b);
    const existing = await Summary.findOne({
      where: { unitIds: sortedIds as any },
    });

    if (existing) {
      res.json({ summary: existing, cached: true });
      return;
    }

    // Get all units with their materials
    const units = await Unit.findAll({
      where: { id: { [Op.in]: unitIds } },
      include: [{ model: Material, as: 'materials', where: { isActive: true }, required: false }],
    });

    if (units.length === 0) {
      res.status(404).json({ message: 'No units found' });
      return;
    }

    if (unitIds.length === 1) {
      // Single unit summary
      const unit = units[0];
      const materials = (unit as any).materials || [];

      if (materials.length === 0) {
        res.status(400).json({ message: 'No materials available to summarize' });
        return;
      }

      const files = materials.map((m: any) => ({
        filePath: m.fileUrl,
        fileType: m.fileType,
        title: m.title,
      }));

      const content = await extractTextFromMultipleFiles(files);

      if (!content || content.length < 50) {
        res.status(400).json({ message: 'Not enough text content to generate a summary' });
        return;
      }

      const result = await generateSummary(content);

      const summary = await Summary.create({
        unitIds: sortedIds,
        content: result.content,
        keyPoints: result.keyPoints,
      });

      res.status(201).json({ summary, cached: false });
    } else {
      // Multi-unit summary
      const unitContents: Array<{ unitName: string; content: string }> = [];

      for (const unit of units) {
        const materials = (unit as any).materials || [];
        if (materials.length > 0) {
          const files = materials.map((m: any) => ({
            filePath: m.fileUrl,
            fileType: m.fileType,
            title: m.title,
          }));
          const text = await extractTextFromMultipleFiles(files);
          if (text && text.length > 50) {
            unitContents.push({ unitName: `Unit ${unit.unitNumber}: ${unit.name}`, content: text });
          }
        }
      }

      if (unitContents.length === 0) {
        res.status(400).json({ message: 'No text content available across selected units' });
        return;
      }

      const result = await generateMultiUnitSummary(unitContents);

      const summary = await Summary.create({
        unitIds: sortedIds,
        content: result.content,
        keyPoints: result.keyPoints,
      });

      res.status(201).json({ summary, cached: false });
    }
  } catch (error) {
    console.error('Error generating summary:', error);
    res.status(500).json({ message: 'Error generating summary. Please try again.' });
  }
};
