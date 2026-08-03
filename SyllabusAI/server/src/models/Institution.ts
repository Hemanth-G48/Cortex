import { DataTypes, Model, Optional } from 'sequelize';
import sequelize from '../config/database';

interface InstitutionAttributes {
  id: number;
  name: string;
  shortName: string;
  description?: string;
  isActive: boolean;
  createdAt?: Date;
  updatedAt?: Date;
}

interface InstitutionCreationAttributes extends Optional<InstitutionAttributes, 'id' | 'description' | 'isActive'> {}

class Institution extends Model<InstitutionAttributes, InstitutionCreationAttributes> implements InstitutionAttributes {
  public id!: number;
  public name!: string;
  public shortName!: string;
  public description?: string;
  public isActive!: boolean;
  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}

Institution.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    name: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    shortName: {
      type: DataTypes.STRING(50),
      allowNull: false,
      unique: true,
    },
    description: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    isActive: {
      type: DataTypes.BOOLEAN,
      defaultValue: false, // Requires admin approval before going live
    },
  },
  {
    sequelize,
    tableName: 'institutions',
  }
);

export default Institution;
