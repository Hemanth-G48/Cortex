import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function CourseManager({ studentId }) {
  const [courses, setCourses] = useState([]);

  useEffect(() => {
    if (studentId) {
      axios.get(`http://localhost:5000/api/courses/${studentId}`)
        .then(res => setCourses(res.data))
        .catch(err => console.error(err));
    }
  }, [studentId]);


  return (
    <section id="view-courses" className="view active">
      <div className="course-manager-container">
        <input type="text" className="search-bar" placeholder="✨ Add your subjects here to organize each class like a pro." />
        
        <div className="courses-header">
          <h2 className="widget-title"><span className="icon">📚</span> Courses</h2>
        </div>
        
        <div className="courses-grid" id="courses-grid">
          {courses.map((course, idx) => (
            <div className="course-card" key={idx}>
              <div className="course-icon-container" style={{backgroundColor: `${course.color}20`, color: course.color}}>
                {course.icon}
              </div>
              <div className="course-info">
                <div className="course-name">{course.name}</div>
              </div>
              <div>
                <div className="course-stats">
                  <span>{course.progress.toFixed(2)}%</span>
                  <span>—</span>
                </div>
                <div className="progress-container">
                  <div className="progress-bar" style={{width: `${course.progress}%`, backgroundColor: course.progress === 100 ? '#68ab84' : course.color}}></div>
                </div>
              </div>
            </div>
          ))}

        </div>
      </div>
    </section>
  );
}
