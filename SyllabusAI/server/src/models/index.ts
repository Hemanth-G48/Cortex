import User from './User';
import Institution from './Institution';
import Course from './Course';
import Subject from './Subject';
import Unit from './Unit';
import Material from './Material';
import Quiz from './Quiz';
import QuizAttempt from './QuizAttempt';
import Summary from './Summary';

// User -> Institution (Many-to-One)
User.belongsTo(Institution, { foreignKey: 'institutionId', as: 'institution' });
Institution.hasMany(User, { foreignKey: 'institutionId', as: 'users' });

// User -> Course (Many-to-One)
User.belongsTo(Course, { foreignKey: 'courseId', as: 'course' });
Course.hasMany(User, { foreignKey: 'courseId', as: 'users' });

// Institution -> Courses (One-to-Many)
Institution.hasMany(Course, { foreignKey: 'institutionId', as: 'courses' });
Course.belongsTo(Institution, { foreignKey: 'institutionId', as: 'institution' });

// Course -> Subjects (One-to-Many)
Course.hasMany(Subject, { foreignKey: 'courseId', as: 'subjects' });
Subject.belongsTo(Course, { foreignKey: 'courseId', as: 'course' });

// Subject -> Units (One-to-Many)
Subject.hasMany(Unit, { foreignKey: 'subjectId', as: 'units' });
Unit.belongsTo(Subject, { foreignKey: 'subjectId', as: 'subject' });

// Unit -> Materials (One-to-Many)
Unit.hasMany(Material, { foreignKey: 'unitId', as: 'materials' });
Material.belongsTo(Unit, { foreignKey: 'unitId', as: 'unit' });

// User -> Materials (One-to-Many) - uploaded by
User.hasMany(Material, { foreignKey: 'uploadedById', as: 'uploadedMaterials' });
Material.belongsTo(User, { foreignKey: 'uploadedById', as: 'uploadedBy' });

// Unit -> Quizzes (One-to-Many)
Unit.hasMany(Quiz, { foreignKey: 'unitId', as: 'quizzes' });
Quiz.belongsTo(Unit, { foreignKey: 'unitId', as: 'unit' });

// Quiz -> QuizAttempts (One-to-Many)
Quiz.hasMany(QuizAttempt, { foreignKey: 'quizId', as: 'attempts' });
QuizAttempt.belongsTo(Quiz, { foreignKey: 'quizId', as: 'quiz' });

// User -> QuizAttempts (One-to-Many)
User.hasMany(QuizAttempt, { foreignKey: 'userId', as: 'quizAttempts' });
QuizAttempt.belongsTo(User, { foreignKey: 'userId', as: 'user' });

export {
  User,
  Institution,
  Course,
  Subject,
  Unit,
  Material,
  Quiz,
  QuizAttempt,
  Summary,
};
