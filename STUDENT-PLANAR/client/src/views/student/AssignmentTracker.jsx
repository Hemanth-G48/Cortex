import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function AssignmentTracker({ studentId }) {
  const [assignments, setAssignments] = useState([]);
  const [activeTab, setActiveTab] = useState('Current Assignments');

  useEffect(() => {
    if (studentId) {
      axios.get(`http://localhost:5000/api/assignments/${studentId}`)
        .then(res => setAssignments(res.data))
        .catch(err => console.error(err));
    }
  }, [studentId]);

  const markDone = async (id) => {
    try {
      const res = await axios.put(`http://localhost:5000/api/assignments/${id}`, { status: 'done' });
      const updated = assignments.map(a => a._id === id ? res.data : a);
      setAssignments(updated);
    } catch (err) { console.error(err); }
  };

  const getStatusProps = (status) => {
    switch (status) {
      case 'done': return { label: 'Done', className: 'status-done' };
      case 'progress': return { label: 'In progress', className: 'status-progress' };
      case 'not-started': return { label: 'Not started', className: 'status-not-started' };
      default: return { label: '', className: '' };
    }
  };

  return (
    <section id="view-assignments" className="view active">
      <div className="assignments-container">
        <div className="assignments-header">
          <div className="assignments-tabs" style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
            <div>
              <button className={`tab-btn ${activeTab === 'Current Assignments' ? 'active' : ''}`} onClick={() => setActiveTab('Current Assignments')}>📝 Current Assignments</button>
              <button className={`tab-btn ${activeTab === 'By Course' ? 'active' : ''}`} onClick={() => setActiveTab('By Course')}>By Course</button>
              <button className={`tab-btn ${activeTab === 'By Type' ? 'active' : ''}`} onClick={() => setActiveTab('By Type')}>By Type</button>
              <button className={`tab-btn ${activeTab === 'Completed' ? 'active' : ''}`} onClick={() => setActiveTab('Completed')}>Completed</button>
            </div>

          </div>
        </div>
        
        <div className="assignments-table-container">
          <table className="assignments-table">
            <thead>
              <tr>
                <th>Assignment Title</th>
                <th>Course</th>
                <th>Due Date</th>
                <th>Assignment Type</th>
                <th>Submission Status</th>
                <th>Time Remaining</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                let displayed = [...assignments];
                if (activeTab === 'Current Assignments') {
                   displayed = displayed.filter(a => a.status !== 'done');
                } else if (activeTab === 'Completed') {
                   displayed = displayed.filter(a => a.status === 'done');
                } else if (activeTab === 'By Course') {
                   displayed.sort((a, b) => a.course.localeCompare(b.course));
                } else if (activeTab === 'By Type') {
                   displayed.sort((a, b) => a.type.localeCompare(b.type));
                }
                
                return displayed.map((a, idx) => {
                  const status = getStatusProps(a.status);
                  return (
                    <tr key={idx}>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <strong style={{ textDecoration: a.status === 'done' ? 'line-through' : 'none' }}>✏️ {a.title}</strong>
                          {a.fileUrl && (
                            <a 
                              href={`http://localhost:5000${a.fileUrl}`} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="file-download-btn"
                            >
                              📥 Download Attachment
                            </a>
                          )}
                        </div>
                      </td>
                      <td style={{ textDecoration: a.status === 'done' ? 'line-through' : 'none' }}>{a.course}</td>
                      <td>📅 {a.date}</td>
                      <td><span className={`type-tag tag-${a.typeColor}`}>{a.type}</span></td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className={`status-tag ${status.className}`}>
                            {a.status === 'done' ? '✅ ' : '● '}{status.label}
                          </span>
                          {a.status !== 'done' && (
                            <button 
                              onClick={() => markDone(a._id)}
                              style={{ padding: '0.2rem 0.5rem', backgroundColor: 'var(--accent-green)', color: '#000', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 'bold' }}
                            >
                              Complete
                            </button>
                          )}
                        </div>
                      </td>
                      <td>{a.time}</td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
