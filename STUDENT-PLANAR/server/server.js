const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

const { Teacher } = require('./models');

// Strict standard MongoDB connection
const dbUri = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/student_planner_db';
mongoose.connect(dbUri, {
}).then(async () => {
  console.log('MongoDB local connected successfully!');
  console.log(`🧭 Connect MongoDB Compass using: ${dbUri}`);
  
  // Force MongoDB to instantly "create" that database visibly in Compass
  // by ensuring at least one document exists.
  const adminCount = await Teacher.countDocuments({ name: 'AdminTeacher' });
  if (adminCount === 0) {
    const bcrypt = require('bcryptjs');
    const hash = await bcrypt.hash('admin123', 10);
    await Teacher.create({ name: 'AdminTeacher', fullName: 'Default Administrator', password: hash, role: 'teacher' });
    console.log('✅ Base database initialized! Default Teacher created: User: AdminTeacher | Pass: admin123');
  }
}).catch((err) => {
    console.error('CRITICAL: Local MongoDB is not running! Please start your MongoDB service.');
    process.exit(1);
  });

// Routes
app.use('/api', require('./routes/api'));

app.listen(PORT, () => {
  console.log(`Backend Server running on port ${PORT}`);
});
