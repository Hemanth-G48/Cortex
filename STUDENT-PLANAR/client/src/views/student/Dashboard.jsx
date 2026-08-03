import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function Dashboard({ studentId }) {
  const [time, setTime] = useState({
    hour: '00', minute: '00', ampm: 'AM', day: 'MONDAY'
  });

  const [todos, setTodos] = useState([]);

  useEffect(() => {
    if (studentId) {
      axios.get(`http://localhost:5000/api/todos/${studentId}`)
        .then(res => setTodos(res.data))
        .catch(err => console.error(err));
    }
  }, [studentId]);

  const toggleTodo = async (idx) => {
    const todo = todos[idx];
    try {
      const res = await axios.put(`http://localhost:5000/api/todos/${todo._id}`, { done: !todo.done });
      const updated = [...todos];
      updated[idx] = res.data;
      setTodos(updated);
    } catch (err) { console.error(err); }
  };


  useEffect(() => {
    const update = () => {
      const now = new Date();
      let chars = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }).split(' ');
      let timeArr = chars[0].split(':');
      const days = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];
      
      setTime({
        hour: timeArr[0],
        minute: timeArr[1],
        ampm: chars[1].toUpperCase(),
        day: days[now.getDay()]
      });
    };
    update();
    const interval = setInterval(update, 10000);
    return () => clearInterval(interval);
  }, []);

  const data = [
    {
      day: 'Monday',
      icon: '💚',
      items: [
        { time: '7:30', name: 'Biology 🦠', done: false },
        { time: '9:55', name: 'History 🏛️', done: false },
        { time: '11:00', name: 'Break ☕', done: false },
        { time: '11:55', name: 'Chemistry 🧪', done: false },
        { time: '12:50', name: 'Social 🗣️', done: false }
      ]
    },
    {
      day: 'Tuesday',
      icon: '💚',
      items: [
        { time: '7:30', name: 'Literature 📚', done: false },
        { time: '9:55', name: 'Math 🧮', done: false },
        { time: '11:00', name: 'Break ☕', done: false },
        { time: '11:55', name: 'Spanish 🇪🇸', done: false },
        { time: '12:50', name: 'Art 🎨', done: false }
      ]
    },
    {
      day: 'Wednesday',
      icon: '💚',
      items: [
        { time: '7:30', name: 'Geography 🌍', done: false },
        { time: '9:55', name: 'Science 🔭', done: false },
        { time: '11:00', name: 'Chill 😌', done: false },
        { time: '11:55', name: 'ICT 💻', done: false },
        { time: '12:50', name: 'Music 🎵', done: false }
      ]
    },
    {
      day: 'Thursday',
      icon: '💚',
      items: [
        { time: '7:30', name: 'Math 🧮', done: false },
        { time: '9:55', name: 'Physics ⚛️', done: false },
        { time: '11:00', name: 'Break ☕', done: false },
        { time: '11:55', name: 'Writing ✍️', done: false },
        { time: '12:50', name: 'Debate 🎤', done: false }
      ]
    },
    {
      day: 'Friday',
      icon: '💚',
      items: [
        { time: '7:30', name: 'Chemistry 🧪', done: false },
        { time: '9:55', name: 'PE 🏃‍♂️', done: false },
        { time: '11:00', name: 'Break ☕', done: false },
        { time: '11:55', name: 'History 🏛️', done: false },
        { time: '12:50', name: 'Free Time ✨', done: false }
      ]
    },
    {
      day: 'Saturday',
      icon: '💚',
      items: [
        { time: '9:00', name: 'Study Group 📚', done: false },
        { time: '11:00', name: 'Homework 📝', done: false },
        { time: '13:00', name: 'Relaxation 🧘', done: false },
        { time: '15:00', name: 'Coding 💻', done: false },
        { time: '18:00', name: 'Movie 🍿', done: false }
      ]
    }
  ];

  return (
    <section id="view-dashboard" className="view active">
      <div className="dashboard-grid">
        <div className="side-panel">
          <div className="clock-widget">
            <div className="time-block">{time.hour}</div>
            <div className="time-block">{time.minute}</div>
            <div className="time-meta">
              <span>{time.ampm}</span>
              <span>{time.day}</span>
            </div>
          </div>
          <div className="image-widget">
            <img src="/moody_plant.png" alt="Vibe" />
          </div>
        </div>
        
        <div className="schedule-widget">
          {data.map(day => (
            <div className="day-card" key={day.day}>
              <div className="day-title">{day.icon} {day.day}</div>
              <ul className="day-items">
                {day.items.map((item, idx) => (
                  <li key={idx}>
                    <input type="checkbox" defaultChecked={item.done} />
                    <span>{item.time} {item.name}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="todos-widget">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 className="widget-title" style={{ marginBottom: 0 }}>Weekly To-Dos</h3>
          </div>
          <ul id="todo-list">
            {todos.map((todo, idx) => (
              <li key={idx} onClick={() => toggleTodo(idx)} style={{ display: 'flex', gap: '8px', cursor: 'pointer', opacity: todo.done ? 0.5 : 1, textDecoration: todo.done ? 'line-through' : 'none' }}>
                <span className="arrow">{todo.done ? '✓' : '▶'}</span> {todo.text}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
