import { DataTypes, Model, Optional } from 'sequelize';
import sequelize from '../config/database';

export interface QuizQuestion {
  question: string;
  options: string[];
  correctAnswer: number; // index into options
  explanation: string;
}

interface QuizAttributes {
  id: number;
  unitId: number;
  questions: QuizQuestion[];
  difficulty: 'easy' | 'medium' | 'hard';
  createdAt?: Date;
  updatedAt?: Date;
}

interface QuizCreationAttributes extends Optional<QuizAttributes, 'id' | 'difficulty'> {}

class Quiz extends Model<QuizAttributes, QuizCreationAttributes> implements QuizAttributes {
  public id!: number;
  public unitId!: number;
  public questions!: QuizQuestion[];
  public difficulty!: 'easy' | 'medium' | 'hard';
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

Quiz.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    unitId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'units',
        key: 'id',
      },
    },
    questions: {
      type: DataTypes.JSONB,
      allowNull: false,
    },
    difficulty: {
      type: DataTypes.ENUM('easy', 'medium', 'hard'),
      defaultValue: 'medium',
    },
  },
  {
    sequelize,
    tableName: 'quizzes',
  }
);

export default Quiz;
