import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navigation from './components/Navigation';
import Dashboard from './views/student/Dashboard';
import HabitTracker from './views/student/HabitTracker';
import CourseManager from './views/student/CourseManager';
import AssignmentTracker from './views/student/AssignmentTracker';
import DailySchedule from './views/student/DailySchedule';
import PomodoroView from './views/student/PomodoroView';
import ReadingTracker from './views/student/ReadingTracker';

export default function StudentApp() {
  const [currentView, setCurrentView] = useState('dashboard');
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user'));

  useEffect(() => {
    if (!user || user.role !== 'student') {
      navigate('/');
    }
  }, [user, navigate]);

  if (!user) return null;

  const titles = {
    'dashboard': `Welcome, ${user.name}`,
    'habits': 'Habit Tracker',
    'courses': 'Course Manager',
    'assignments': 'Assignments',
    'schedule': 'Daily Schedule',
    'pomodoro': 'Pomodoro + Brain Dump',
    'reading': 'Reading Tracker'
  };

  return (
    <div id="app">
      <Navigation currentView={currentView} setView={setCurrentView} />

      <main className="content">
        <div className="cover-image-container">
          <img id="cover-image" src="/cyberpunk_header.png" alt="Cyberpunk Cover" style={{ filter: 'contrast(1.2)' }} />
          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, var(--bg-color), transparent 80%)' }}></div>
        </div>
        
        <div className="page-header" id="dynamic-header">
           <h1 className="page-title">{titles[currentView]}</h1>
        </div>

        <div id="views-container">
          {currentView === 'dashboard' && <Dashboard studentId={user._id} />}
          {currentView === 'habits' && <HabitTracker studentId={user._id} />}
          {currentView === 'courses' && <CourseManager studentId={user._id} />}
          {currentView === 'assignments' && <AssignmentTracker studentId={user._id} />}
          {currentView === 'schedule' && <DailySchedule studentId={user._id} />}
          {currentView === 'pomodoro' && <PomodoroView studentId={user._id} />}
          {currentView === 'reading' && <ReadingTracker studentId={user._id} />}
        </div>
      </main>
    </div>
  );
}
