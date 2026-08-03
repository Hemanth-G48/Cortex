import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

export default function PomodoroView({ studentId }) {
  const [timeLeft, setTimeLeft] = useState(25 * 60);
  const [isRunning, setIsRunning] = useState(false);
  const [mode, setMode] = useState('pomodoro'); // pomodoro, short, long
  const [brainDump, setBrainDump] = useState('');
  const [dbEntryId, setDbEntryId] = useState(null);

  useEffect(() => {
    let timer = null;
    if (isRunning && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft(prev => prev - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      setIsRunning(false);
      alert('Time is up!');
    }
    return () => clearInterval(timer);
  }, [isRunning, timeLeft]);

  useEffect(() => {
    axios.get(`http://localhost:5000/api/braindumps/${studentId}`)
      .then(res => {
        if (res.data.length > 0) {
          const latestDbEntry = res.data[res.data.length - 1];
          setBrainDump(latestDbEntry.text);
          setDbEntryId(latestDbEntry._id);
        }
      })
      .catch(err => console.error(err));
  }, [studentId]);

  const saveTimeout = useRef(null);

  const saveBrainDump = (text) => {
    setBrainDump(text);
    
    if (saveTimeout.current) clearTimeout(saveTimeout.current);
    
    saveTimeout.current = setTimeout(async () => {
      try {
        if (dbEntryId) {
          await axios.put(`http://localhost:5000/api/braindumps/${dbEntryId}`, { text, updatedAt: new Date() });
        } else {
          const res = await axios.post(`http://localhost:5000/api/braindumps`, { studentId, text });
          setDbEntryId(res.data._id);
        }
      } catch (err) { console.error('Brain dump save failed:', err); }
    }, 1000);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    setIsRunning(false);
    if (newMode === 'pomodoro') setTimeLeft(25 * 60);
    else if (newMode === 'short') setTimeLeft(5 * 60);
    else if (newMode === 'long') setTimeLeft(15 * 60);
  };

  return (
    <div className="pomodoro-container" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', height: '100%', padding: '1rem' }}>
      {/* Left: Pomodoro Timer */}
      <div className="timer-section" style={{ 
        position: 'relative', 
        borderRadius: '24px', 
        overflow: 'hidden', 
        backgroundImage: 'url("/pomodoro_bg.png")', 
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
      }}>
        <div style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.4)' }}></div>
        
        <div style={{ zIndex: 1, textAlign: 'center' }}>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.5rem', marginBottom: '1.5rem', fontStyle: 'italic', opacity: 0.9 }}>Pomodoro Timer</h2>
          
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '2rem' }}>
            {['pomodoro', 'short', 'long'].map(m => (
              <button 
                key={m}
                onClick={() => handleModeChange(m)}
                style={{
                  padding: '8px 16px',
                  borderRadius: '20px',
                  border: 'none',
                  backgroundColor: mode === m ? 'white' : 'rgba(255,255,255,0.2)',
                  color: mode === m ? 'black' : 'white',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  transition: '0.3s'
                }}
              >
                {m.charAt(0).toUpperCase() + m.slice(1).replace('pomodoro', 'Pomodoro').replace('short', 'Short Break').replace('long', 'Long Break')}
              </button>
            ))}
          </div>

          <div style={{ fontSize: '6rem', fontWeight: 'bold', marginBottom: '1.5rem', letterSpacing: '-2px' }}>
            {formatTime(timeLeft)}
          </div>

          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', justifyContent: 'center' }}>
            <button 
              onClick={() => setIsRunning(!isRunning)}
              style={{
                padding: '12px 40px',
                borderRadius: '30px',
                border: 'none',
                backgroundColor: 'white',
                color: 'black',
                fontSize: '1.2rem',
                fontWeight: 'bold',
                cursor: 'pointer',
                boxShadow: '0 4px 15px rgba(255,255,255,0.3)'
              }}
            >
              {isRunning ? 'STOP' : 'START'}
            </button>
            <button 
              onClick={() => { setIsRunning(false); handleModeChange(mode); }}
              style={{ background: 'none', border: 'none', color: 'white', fontSize: '1.5rem', cursor: 'pointer' }}
            >
              🔄
            </button>
          </div>
        </div>
      </div>

      {/* Right: Brain Dump */}
      <div className="brain-dump-section" style={{ backgroundColor: 'var(--bg-color-secondary)', borderRadius: '24px', padding: '2rem', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.8rem', color: 'var(--accent-green)', fontStyle: 'italic' }}>Brain dump</h2>
          <div style={{ display: 'flex', gap: '10px' }}>
             <span title="Shared with teacher" style={{ fontSize: '1.2rem', opacity: 0.6 }}>👁️‍🗨️</span>
          </div>
        </div>
        
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>Initial thoughts, quick notes, and creative debris.</p>
        
        <textarea 
          value={brainDump}
          onChange={(e) => saveBrainDump(e.target.value)}
          placeholder="Start typing your thoughts here..."
          style={{
            flex: 1,
            backgroundColor: 'transparent',
            border: 'none',
            color: 'var(--text-primary)',
            fontSize: '1rem',
            lineHeight: '1.6',
            resize: 'none',
            outline: 'none',
            fontFamily: 'inherit'
          }}
        />
        
        <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
          <span>{dbEntryId ? 'Synced with Cloud' : 'Initializing...'}</span>
          <span>{new Date().toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}
