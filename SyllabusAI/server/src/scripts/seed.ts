import dotenv from 'dotenv';
dotenv.config();

import sequelize from '../config/database';
import { User, Institution, Course, Subject, Unit } from '../models';

const seed = async () => {
  try {
    await sequelize.authenticate();
    console.log('Database connected.');

    // Sync all models
    await sequelize.sync({ alter: true });
    console.log('Tables synced.');

    // Create admin user
    const [admin] = await User.findOrCreate({
      where: { email: 'yash113gadia@gmail.com' },
      defaults: {
        email: 'yash113gadia@gmail.com',
        password: '7597288206',
        firstName: 'Yash',
        lastName: 'Gadia',
        role: 'admin',
      },
    });
    console.log(`Admin user ready: ${admin.email} (role: ${admin.role})`);

    // Create sample institution (approved by admin)
    const [gla] = await Institution.findOrCreate({
      where: { shortName: 'GLA' },
      defaults: {
        name: 'GLA University',
        shortName: 'GLA',
        description: 'GLA University, Mathura',
        isActive: true, // Admin-approved
      },
    });
    console.log(`Institution ready: ${gla.name} (active: ${gla.isActive})`);

    // Create sample course
    const [btech] = await Course.findOrCreate({
      where: { institutionId: gla.id, code: 'BTECH-CSE' },
      defaults: {
        institutionId: gla.id,
        name: 'B.Tech Computer Science & Engineering',
        code: 'BTECH-CSE',
        description: '4-year undergraduate program',
        duration: 8,
      },
    });
    console.log(`Course ready: ${btech.name}`);

    // Create sample subjects
    const subjectsData = [
      { name: 'Data Structures & Algorithms', code: 'CS201', semester: 3, credits: 4 },
      { name: 'Database Management Systems', code: 'CS202', semester: 3, credits: 3 },
      { name: 'Operating Systems', code: 'CS301', semester: 4, credits: 4 },
      { name: 'Computer Networks', code: 'CS302', semester: 4, credits: 3 },
      { name: 'Software Engineering', code: 'CS401', semester: 5, credits: 3 },
    ];

    for (const subData of subjectsData) {
      const [subject] = await Subject.findOrCreate({
        where: { courseId: btech.id, code: subData.code },
        defaults: {
          courseId: btech.id,
          ...subData,
        },
      });

      // Create units for each subject
      const unitCount = 5;
      for (let i = 1; i <= unitCount; i++) {
        await Unit.findOrCreate({
          where: { subjectId: subject.id, unitNumber: i },
          defaults: {
            subjectId: subject.id,
            unitNumber: i,
            name: `Unit ${i}`,
          },
        });
      }

      console.log(`Subject ready: ${subject.name} with ${unitCount} units`);
    }

    console.log('\nSeed completed successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Seed error:', error);
    process.exit(1);
  }
};

seed();
