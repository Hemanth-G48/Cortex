const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const { Student, Teacher, Habit, Course, Assignment, Schedule, Todo, BrainDump, Book } = require('../models');

router.post('/signup', async (req, res) => {
  try {
    const { name, fullName, password, role, secretKey } = req.body;
    if (!name || !password) return res.status(400).json({ error: 'Name and Password required' });
    
    if (role === 'teacher' && secretKey !== process.env.TEACHER_SECRET_KEY) {
      return res.status(403).json({ error: 'Invalid Teacher Secret Key' });
    }
    
    // Choose which Model/Collection purely structurally based on the Role
    const Model = role === 'teacher' ? Teacher : Student;
    const existing = await Model.findOne({ name });
    if (existing) return res.status(400).json({ error: 'Username already exists in the ' + role + ' database.' });

    const hashedPassword = await bcrypt.hash(password, 10);
    const user = new Model({ name, fullName, password: hashedPassword, role });
    await user.save();
    res.json(user);
  } catch (err) { res.status(500).json({ error: err.message }); }
});

router.post('/login', async (req, res) => {
  try {
    const { name, password, role } = req.body;
    const Model = role === 'teacher' ? Teacher : Student;
    
    let user = await Model.findOne({ name, role });
    if (!user) return res.status(404).json({ error: 'User not found in ' + role + ' database.' });
    
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.status(400).json({ error: 'Invalid password' });
    
    res.json(user);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/students', async (req, res) => {
  try {
    const students = await Student.find();
    res.json(students);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Generic CRUD Generator
const makeCrud = (Model, routeName) => {
  // Get all for a student
  router.get(`/${routeName}/:studentId`, async (req, res) => {
    try {
      const data = await Model.find({ studentId: req.params.studentId });
      res.json(data);
    } catch (err) { res.status(500).json({ error: err.message }); }
  });

  // Create
  router.post(`/${routeName}`, async (req, res) => {
    try {
      const newItem = new Model(req.body);
      await newItem.save();
      res.json(newItem);
    } catch (err) { res.status(500).json({ error: err.message }); }
  });

  // Update
  router.put(`/${routeName}/:id`, async (req, res) => {
    try {
      const updated = await Model.findByIdAndUpdate(req.params.id, req.body, { returnDocument: 'after' });
      res.json(updated);
    } catch (err) { res.status(500).json({ error: err.message }); }
  });

  // Delete
  router.delete(`/${routeName}/:id`, async (req, res) => {
    try {
      await Model.findByIdAndDelete(req.params.id);
      res.json({ success: true });
    } catch (err) { res.status(500).json({ error: err.message }); }
  });
};

makeCrud(Habit, 'habits');
makeCrud(Course, 'courses');
makeCrud(Assignment, 'assignments');
makeCrud(Schedule, 'schedules');
makeCrud(Todo, 'todos');
makeCrud(BrainDump, 'braindumps');
makeCrud(Book, 'books');

const multer = require('multer');
const path = require('path');

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, path.join(__dirname, '../uploads'));
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + '-' + file.originalname.replace(/\s+/g, '-'));
  }
});

const upload = multer({ storage });

router.post('/upload-book', upload.single('bookFile'), async (req, res) => {
  try {
    const { studentId, title, author, category, coverUrl } = req.body;
    const fileUrl = req.file ? `/uploads/${req.file.filename}` : '';
    
    const newBook = new Book({
      studentId, title, author, category, coverUrl, fileUrl
    });
    const saved = await newBook.save();
    res.json(saved);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/upload-assignment', upload.single('assignmentFile'), async (req, res) => {
  try {
    const { studentId, title, course, date, type, typeColor, status, time } = req.body;
    const fileUrl = req.file ? `/uploads/${req.file.filename}` : '';
    
    const newAssignment = new Assignment({
      studentId,
      title: title || (req.file ? req.file.originalname.split('.').slice(0, -1).join('.') : 'Untitled Assignment'),
      course: course || 'Teacher Assigned',
      date: date || 'TBD',
      type: type || 'Homework',
      typeColor: typeColor || 'purple',
      status: status || 'not-started',
      time: time || 'Urgent',
      fileUrl
    });
    
    const saved = await newAssignment.save();
    res.json(saved);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
