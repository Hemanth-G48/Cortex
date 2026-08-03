import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function DailySchedule({ studentId }) {
  const today = new Date().toISOString().split('T')[0];
  const [schedule, setSchedule] = useState([]);
  const [activeTab, setActiveTab] = useState('Overview');
  const [selectedDate, setSelectedDate] = useState(today);

  useEffect(() => {
    if (studentId) {
      axios.get(`http://localhost:5000/api/schedules/${studentId}`)
        .then(res => setSchedule(res.data))
        .catch(err => console.error(err));
    }
  }, [studentId]);

  const toggleDone = async (idx) => {
    const item = schedule[idx];
    try {
      const res = await axios.put(`http://localhost:5000/api/schedules/${item._id}`, { done: !item.done });
      const updated = [...schedule];
      updated[idx] = res.data;
      setSchedule(updated);
    } catch (err) { console.error(err); }
  };

  const addBlock = async () => {
    const time = prompt("Enter time block (e.g. 22:00-23:00):");
    if (time) {
      const activity = prompt("Enter activity details:");
      try {
        const res = await axios.post(`http://localhost:5000/api/schedules`, {
          studentId, date: selectedDate, time, activity, category: 'Study Time', catClass: 'cat-study', location: 'TBD', energy: 'Medium', eClass: 'energy-medium', notes: '', done: false
        });
        setSchedule([...schedule, res.data]);
      } catch (err) { console.error(err); }
    }
  };

  return (
    <section id="view-schedule" className="view active">
      <div className="schedule-container">
        <div className="schedule-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <style>{`
            .neon-date-picker::-webkit-calendar-picker-indicator {
              cursor: pointer;
              filter: invert(0.8) sepia(1) saturate(5) hue-rotate(130deg) brightness(1.2);
              transition: 0.2s filter;
            }
            .neon-date-picker::-webkit-calendar-picker-indicator:hover {
              filter: invert(1) sepia(1) saturate(10) hue-rotate(300deg) brightness(1.5);
            }
          `}</style>
          <div>
            <h2 className="widget-title">📅 Daily Schedule</h2>
            <p style={{color: 'var(--text-secondary)', fontSize: '0.9rem'}}>📌 Plan out your day hour by hour.</p>
          </div>
          <div>
            <input 
              type="date" 
              className="neon-date-picker"
              min={today}
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-color-secondary)', color: 'var(--text-primary)', border: '1px solid var(--accent-green)', padding: '0.75rem', borderRadius: '8px', fontFamily: 'var(--font-sans)', cursor: 'pointer', boxShadow: '0 0 15px rgba(0,255,204,0.2)', textShadow: '0 0 5px rgba(0,255,204,0.5)'
              }}
            />
          </div>
        </div>
        
        <div className="schedule-tabs" style={{ display: 'flex', justifyContent: 'space-between', width: '100%', borderBottom: '1px solid var(--border-color)', marginBottom: '1rem' }}>
          <div>
            <button className={`tab-btn ${activeTab === 'Overview' ? 'active' : ''}`} onClick={() => setActiveTab('Overview')}>Overview</button>
            <button className={`tab-btn ${activeTab === 'School' ? 'active' : ''}`} onClick={() => setActiveTab('School')}>School</button>
            <button className={`tab-btn ${activeTab === 'Study Time' ? 'active' : ''}`} onClick={() => setActiveTab('Study Time')}>Study Time</button>
            <button className={`tab-btn ${activeTab === 'Break' ? 'active' : ''}`} onClick={() => setActiveTab('Break')}>Break</button>
          </div>
          <button className="btn-primary" onClick={addBlock} style={{ marginBottom: '0.5rem', backgroundColor: 'var(--accent-blue)', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>New Block +</button>
        </div>
        
        <div className="schedule-table-wrapper">
          <table className="schedule-table">
            <thead>
              <tr>
                <th>Block</th>
                <th>Activity</th>
                <th>Category</th>
                <th>Location</th>
                <th>Energy Level</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {schedule.filter(item => item.date === selectedDate && (activeTab === 'Overview' || item.category === activeTab)).map((item, idx) => (
                <tr key={idx}>
                  <td>
                    <div className="time-col">
                      <input type="checkbox" className="habit-checkbox" checked={item.done} onChange={() => toggleDone(idx)} />
                      <span style={{ textDecoration: item.done ? 'line-through' : 'none', opacity: item.done ? 0.5 : 1 }}>{item.time}</span>
                    </div>
                  </td>
                  <td style={{ textDecoration: item.done ? 'line-through' : 'none', opacity: item.done ? 0.5 : 1 }}><strong>{item.activity}</strong></td>
                  <td><span className={`category-tag ${item.catClass}`}>{item.category}</span></td>
                  <td>📍 {item.location}</td>
                  <td><span className={`energy-tag ${item.eClass}`}>{item.energy}</span></td>
                  <td style={{color: 'var(--text-secondary)', fontStyle: 'italic'}}>{item.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
