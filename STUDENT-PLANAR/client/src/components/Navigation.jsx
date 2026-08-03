import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function Navigation({ currentView, setView }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('user');
    navigate('/');
  };
  return (
    <nav className="top-nav">
      <div className="breadcrumbs">
        <span className="icon">📚</span>
        <span className="path">2.0 Ultimate Student Planner</span>
      </div>
      <div className="nav-links" id="main-nav">
        <button 
          className={currentView === 'dashboard' ? 'active' : ''} 
          onClick={() => setView('dashboard')}
        >
          Dashboard
        </button>
        <button 
          className={currentView === 'habits' ? 'active' : ''} 
          onClick={() => setView('habits')}
        >
          Habit Tracker
        </button>
        <button 
          className={currentView === 'courses' ? 'active' : ''} 
          onClick={() => setView('courses')}
        >
          Course Manager
        </button>
        <button 
          className={currentView === 'assignments' ? 'active' : ''} 
          onClick={() => setView('assignments')}
        >
          Assignments
        </button>
        <button 
          className={currentView === 'schedule' ? 'active' : ''} 
          onClick={() => setView('schedule')}
        >
          Daily Schedule
        </button>
        <button 
          className={currentView === 'pomodoro' ? 'active' : ''} 
          onClick={() => setView('pomodoro')}
        >
          Pomodoro + Brain Dump
        </button>
        <button 
          className={currentView === 'reading' ? 'active' : ''} 
          onClick={() => setView('reading')}
        >
          Reading Tracker
        </button>
      </div>
      <div className="nav-right">
        <button className="btn-ghost" onClick={handleLogout} style={{ color: 'var(--accent-red)', borderColor: 'var(--accent-red)' }}>🚪 Logout</button>
      </div>
    </nav>
  );
}
