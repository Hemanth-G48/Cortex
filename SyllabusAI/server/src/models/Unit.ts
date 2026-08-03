import { DataTypes, Model, Optional } from 'sequelize';
import sequelize from '../config/database';

interface UnitAttributes {
  id: number;
  subjectId: number;
  unitNumber: number;
  name: string;
  description?: string;
  isActive: boolean;
  createdAt?: Date;
  updatedAt?: Date;
}

interface UnitCreationAttributes extends Optional<UnitAttributes, 'id' | 'description' | 'isActive'> {}

class Unit extends Model<UnitAttributes, UnitCreationAttributes> implements UnitAttributes {
  public id!: number;
  public subjectId!: number;
  public unitNumber!: number;
  public name!: string;
  public description?: string;
  public isActive!: boolean;
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

Unit.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    subjectId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'subjects',
        key: 'id',
      },
    },
    unitNumber: {
      type: DataTypes.INTEGER,
      allowNull: false,
    },
    name: {
      type: DataTypes.STRING(255),
      allowNull: false,
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
    tableName: 'units',
    indexes: [
      {
        unique: true,
        fields: ['subject_id', 'unit_number'],
      },
    ],
  }
);

export default Unit;
