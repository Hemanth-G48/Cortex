const mongoose = require('mongoose');

// Students
const studentSchema = new mongoose.Schema({
  name: { type: String, required: true, unique: true },
  fullName: { type: String },
  password: { type: String, required: true },
  role: { type: String, default: 'student' }
});
const Student = mongoose.model('Student', studentSchema);

// Teachers
const teacherSchema = new mongoose.Schema({
  name: { type: String, required: true, unique: true },
  fullName: { type: String },
  password: { type: String, required: true },
  role: { type: String, default: 'teacher' }
});
const Teacher = mongoose.model('Teacher', teacherSchema);

// Habits
const habitSchema = new mongoose.Schema({
  studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'Student', required: true },
  name: { type: String, required: true },
  dates: { type: [Boolean], default: [false, false, false, false, false, false, false] }
});
const Habit = mongoose.model('Habit', habitSchema);

// Courses
const courseSchema = new mongoose.Schema({
  studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'Student', required: true },
  name: { type: String, required: true },
  icon: { type: String, default: '📖' },
  color: { type: String, default: '#4d90ce' },
  progress: { type: Number, default: 0 }
});
const Course = mongoose.model('Course', courseSchema);

// Assignments
const assignmentSchema = new mongoose.Schema({
  studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'Student', required: true },
  title: { type: String, required: true },
  course: { type: String },
  date: { type: String },
  type: { type: String },
  typeColor: { type: String, default: 'blue' },
  status: { type: String, enum: ['not-started', 'progress', 'done'], default: 'not-started' },
  time: { type: String },
  fileUrl: { type: String, default: '' }
});
const Assignment = mongoose.model('Assignment', assignmentSchema);

// Schedule
const scheduleSchema = new mongoose.Schema({
  studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'Student', required: true },
  date: { type: String, required: true },
  time: String,
  activity: String,
  category: String,
  catClass: String,
  location: String,
  energy: String,
  eClass: String,
  notes: String,
  done: { type: Boolean, default: false }
});
const Schedule = mongoose.model('Schedule', scheduleSchema);

// Todos
const todoSchema = new mongoose.Schema({
  studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'Student', required: true },
  text: String,
  done: { type: Boolean, default: false }
});
const Todo = mongoose.model('Todo', todoSchema);

// Brain Dump
const brainDumpSchema = new mongoose.Schema({
  studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'Student', required: true },
  text: { type: String, default: '' },
  updatedAt: { type: Date, default: Date.now }
});
const BrainDump = mongoose.model('BrainDump', brainDumpSchema);

// Books (Reading Tracker)
const bookSchema = new mongoose.Schema({
  studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'Student', required: true },
  title: { type: String, required: true },
  author: { type: String, default: '' },
  category: { type: String, enum: ['reading', 'finished', 'want'], default: 'reading' },
  coverUrl: { type: String, default: '' },
  fileUrl: { type: String, default: '' }
});
const Book = mongoose.model('Book', bookSchema);

module.exports = { Student, Teacher, Habit, Course, Assignment, Schedule, Todo, BrainDump, Book };
