import { DataTypes, Model, Optional } from 'sequelize';
import sequelize from '../config/database';

interface SubjectAttributes {
  id: number;
  courseId: number;
  name: string;
  code: string;
  semester: number;
  credits: number;
  description?: string;
  isActive: boolean;
  createdAt?: Date;
  updatedAt?: Date;
}

interface SubjectCreationAttributes extends Optional<SubjectAttributes, 'id' | 'description' | 'isActive'> {}

class Subject extends Model<SubjectAttributes, SubjectCreationAttributes> implements SubjectAttributes {
  public id!: number;
  public courseId!: number;
  public name!: string;
  public code!: string;
  public semester!: number;
  public credits!: number;
  public description?: string;
  public isActive!: boolean;
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

Subject.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    courseId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'courses',
        key: 'id',
      },
    },
    name: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    code: {
      type: DataTypes.STRING(50),
      allowNull: false,
    },
    semester: {
      type: DataTypes.INTEGER,
      allowNull: false,
    },
    credits: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 3,
    },
    description: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    isActive: {
      type: DataTypes.BOOLEAN,
      defaultValue: true,
    },
  },
  {
    sequelize,
    tableName: 'subjects',
    indexes: [
      {
        unique: true,
        fields: ['course_id', 'code'],
      },
    ],
  }
);

export default Subject;
