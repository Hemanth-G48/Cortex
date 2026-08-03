import { DataTypes, Model, Optional } from 'sequelize';
import sequelize from '../config/database';

interface SummaryAttributes {
  id: number;
  unitIds: number[];
  content: string;
  keyPoints: string[];
  createdAt?: Date;
  updatedAt?: Date;
}

interface SummaryCreationAttributes extends Optional<SummaryAttributes, 'id'> {}

class Summary extends Model<SummaryAttributes, SummaryCreationAttributes> implements SummaryAttributes {
  public id!: number;
  public unitIds!: number[];
  public content!: string;
  public keyPoints!: string[];
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

Summary.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    unitIds: {
      type: DataTypes.JSONB,
      allowNull: false,
    },
    content: {
      type: DataTypes.TEXT,
      allowNull: false,
    },
    keyPoints: {
      type: DataTypes.JSONB,
      allowNull: false,
    },
  },
  {
    sequelize,
    tableName: 'summaries',
  }
);

export default Summary;
