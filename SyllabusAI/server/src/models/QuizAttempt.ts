import { DataTypes, Model, Optional } from 'sequelize';
import sequelize from '../config/database';

interface QuizAttemptAttributes {
  id: number;
  userId: number;
  quizId: number;
  answers: number[]; // user's selected option indices
  score: number;
  totalQuestions: number;
  createdAt?: Date;
  updatedAt?: Date;
}

interface QuizAttemptCreationAttributes extends Optional<QuizAttemptAttributes, 'id'> {}

class QuizAttempt extends Model<QuizAttemptAttributes, QuizAttemptCreationAttributes> implements QuizAttemptAttributes {
  public id!: number;
  public userId!: number;
  public quizId!: number;
  public answers!: number[];
  public score!: number;
  public totalQuestions!: number;
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

QuizAttempt.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    userId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'users',
        key: 'id',
      },
    },
    quizId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'quizzes',
        key: 'id',
      },
    },
    answers: {
      type: DataTypes.JSONB,
      allowNull: false,
    },
    score: {
      type: DataTypes.INTEGER,
      allowNull: false,
    },
    totalQuestions: {
      type: DataTypes.INTEGER,
      allowNull: false,
    },
  },
  {
    sequelize,
    tableName: 'quiz_attempts',
  }
);

export default QuizAttempt;
