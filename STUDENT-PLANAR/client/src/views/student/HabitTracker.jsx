import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const days = ['Mon 24', 'Tue 25', 'Wed 26', 'Thu 27', 'Fri 28', 'Sat 29', 'Sun 30'];

export default function HabitTracker({ studentId }) {
  const [habits, setHabits] = useState([]);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (studentId) {
      axios.get(`http://localhost:5000/api/habits/${studentId}`)
        .then(res => setHabits(res.data))
        .catch(err => console.error(err));
    }
  }, [studentId]);

  const toggleHabit = async (hIdx, dIdx) => {
    const habit = habits[hIdx];
    const newDates = [...habit.dates];
    newDates[dIdx] = !newDates[dIdx];
    
    try {
      const res = await axios.put(`http://localhost:5000/api/habits/${habit._id}`, { dates: newDates });
      const newHabits = [...habits];
      newHabits[hIdx] = res.data;
      setHabits(newHabits);
    } catch (err) { console.error(err); }
  };

  const addHabit = async () => {
    const name = prompt("Enter new habit name:");
    if (name) {
      try {
        const res = await axios.post(`http://localhost:5000/api/habits`, {
          studentId, name, dates: [false, false, false, false, false, false, false]
        });
        setHabits([...habits, res.data]);
      } catch (err) { console.error(err); }
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if(!canvas) return;
    const ctx = canvas.getContext('2d');
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const dailyPercentages = days.map((_, dIdx) => {
      let completed = 0;
      habits.forEach(habit => {
        if(habit.dates[dIdx]) completed++;
      });
      return completed / habits.length;
    });

    const padding = 40;
    const w = canvas.width - padding * 2;
    const h = canvas.height - padding * 2;
    
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath();
    [0, 0.25, 0.5, 0.75, 1].forEach(val => {
      const y = padding + h - (val * h);
      ctx.moveTo(padding, y);
      ctx.lineTo(padding + w, y);
      
      ctx.fillStyle = 'rgba(255,255,255,0.4)';
      ctx.font = '10px Inter';
      ctx.fillText(Math.round(val * 100) + '%', 10, y + 4);
    });
    ctx.stroke();

    ctx.strokeStyle = '#4d90ce';
    ctx.lineWidth = 3;
    ctx.beginPath();
    
    const points = dailyPercentages.map((pct, i) => {
      const x = padding + (i * (w / (days.length - 1)));
      const y = padding + h - (pct * h);
      return {x, y, pct};
    });

    points.forEach((p, i) => {
      if(i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();

    points.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#191919';
      ctx.fill();
      ctx.stroke();
      
      ctx.fillStyle = 'rgba(255,255,255,0.6)';
      ctx.fillText(days[i].split(' ')[0], p.x - 10, padding + h + 20);
    });
  }, [habits]);

  return (
    <section id="view-habits" className="view active">
      <div className="habit-tracker-container">
        <div className="tracker-header">
          <h2 className="widget-title">Habits</h2>
          <div className="tracker-controls">
            <button className="btn-primary" onClick={addHabit}>New +</button>
          </div>
        </div>
        <div className="habits-table-wrapper" id="habits-table-wrapper">
          <table className="habits-table">
            <thead>
              <tr>
                <th>Habit</th>
                {days.map(d => <th key={d}>{d}</th>)}
                <th>Progress</th>
              </tr>
            </thead>
            <tbody>
              {habits.map((habit, hIdx) => {
                const completed = habit.dates.filter(Boolean).length;
                const progress = Math.round((completed / 7) * 100);
                
                return (
                  <tr key={hIdx}>
                    <td><strong>{habit.name}</strong></td>
                    {habit.dates.map((isDone, dIdx) => (
                      <td key={dIdx}>
                        <input 
                          type="checkbox" 
                          className="habit-checkbox" 
                          checked={isDone} 
                          onChange={() => toggleHabit(hIdx, dIdx)} 
                        />
                      </td>
                    ))}
                    <td>
                      <div>{progress}%</div>
                      <div className="habit-progress-bg">
                        <div className="habit-progress-fill" style={{width: `${progress}%`}}></div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        <div className="chart-container">
          <div className="chart-header">
            <span className="icon">📈</span> Chart
          </div>
          <div className="chart-canvas-wrapper">
            <canvas ref={canvasRef} width="800" height="200"></canvas>
          </div>
        </div>
      </div>
    </section>
  );
}
