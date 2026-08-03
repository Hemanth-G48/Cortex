import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

export default function TeacherDashboard() {
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null); // for modal
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);
  const assigningStudentIdRef = useRef(null);
  const assigningAssignmentStudentIdRef = useRef(null);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const fileInputRef = useRef(null);
  const assignmentFileInputRef = useRef(null);
  const navigate = useNavigate();

  const fetchStudents = async () => {
    try {
      const res = await axios.get('http://localhost:5000/api/students');
      
      const studentsWithStats = await Promise.all(res.data.map(async (student) => {
        const assigns = await axios.get(`http://localhost:5000/api/assignments/${student._id}`);
        const todos = await axios.get(`http://localhost:5000/api/todos/${student._id}`);
        const dumps = await axios.get(`http://localhost:5000/api/braindumps/${student._id}`);
        const books = await axios.get(`http://localhost:5000/api/books/${student._id}`);
        const latestDump = dumps.data.length > 0 ? dumps.data[dumps.data.length - 1] : { text: 'No entry yet' };
        return { 
          ...student, 
          pendingTasks: assigns.data.filter(a => a.status !== 'done').length + todos.data.filter(t => !t.done).length,
          assignments: assigns.data,
          todos: todos.data,
          brainDump: latestDump,
          readingList: books.data
        };
      }));
      setStudents(studentsWithStats);
    } catch (err) {
      console.error("Failed to fetch students", err);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('user');
    navigate('/');
  };

  const assignAssignment = (studentId) => {
    assigningAssignmentStudentIdRef.current = studentId;
    assignmentFileInputRef.current.click();
  };

  const assignCourse = async (studentId) => {
    const name = prompt("Enter new course name:");
    if (!name) return;
    const colors = ['#00ffcc', '#0088ff', '#ff0055', '#bb00ff'];
    const color = colors[Math.floor(Math.random() * colors.length)];
    try {
      await axios.post(`http://localhost:5000/api/courses`, { studentId, name, icon: '📖', color, progress: 0 });
      alert('Course instantiated successfully!');
    } catch (err) { alert('Failed to assign course'); }
  };

  const assignTodo = async (studentId) => {
    const text = prompt('Enter a new To-Do task:');
    if (!text) return;
    try {
      await axios.post(`http://localhost:5000/api/todos`, { studentId, text, done: false });
      alert('Todo injected successfully!');
      fetchStudents();
    } catch (err) { alert('Failed to assign todo'); }
  };

  const getTargetStudents = () => {
    if (selectedStudentIds.length === 0) return students;
    return students.filter(s => selectedStudentIds.includes(s._id));
  };

  const toggleStudentSelection = (id) => {
    setSelectedStudentIds(prev => 
      prev.includes(id) ? prev.filter(sid => sid !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => setSelectedStudentIds(students.map(s => s._id));
  const handleDeselectAll = () => setSelectedStudentIds([]);

  const broadcastAssignment = () => {
    assigningAssignmentStudentIdRef.current = 'ALL';
    assignmentFileInputRef.current.click();
  };

  const broadcastCourse = async () => {
    const targets = getTargetStudents();
    const name = prompt(`ENTER GLOBAL COURSE NAME (will be sent to ${targets.length} students):`);
    if (!name) return;
    setIsBroadcasting(true);
    const colors = ['#00ffcc', '#0088ff', '#ff0055', '#bb00ff'];
    const color = colors[Math.floor(Math.random() * colors.length)];
    try {
      await Promise.all(targets.map(student =>
        axios.post(`http://localhost:5000/api/courses`, { studentId: student._id, name, icon: '📖', color, progress: 0 })
      ));
      alert('Course Broadcast Successful!');
      fetchStudents();
    } catch (err) { alert('Broadcast failed'); }
    setIsBroadcasting(false);
  };

  const broadcastTodo = async () => {
    const targets = getTargetStudents();
    const text = prompt(`ENTER GLOBAL TO-DO TASK (will be sent to ${targets.length} students):`);
    if (!text) return;
    setIsBroadcasting(true);
    try {
      await Promise.all(targets.map(student =>
        axios.post(`http://localhost:5000/api/todos`, { studentId: student._id, text, done: false })
      ));
      alert('To-Do Broadcast Successful!');
      fetchStudents();
    } catch (err) { alert('Broadcast failed'); }
    setIsBroadcasting(false);
  };

  const triggerGlobalBookAssign = () => {
    assigningStudentIdRef.current = 'ALL';
    fileInputRef.current.click();
  };

  const triggerBookAssign = (studentId) => {
    assigningStudentIdRef.current = studentId;
    fileInputRef.current.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const targets = getTargetStudents();
    const assigningId = assigningStudentIdRef.current;
    
    // Automatically parse the title from the file name, dropping the extension
    const title = file.name.split('.').slice(0, -1).join('.') || file.name;
    const author = 'Teacher';
    
    const covers = ['/book1.png', '/book2.png', '/book3.png'];
    const coverUrl = covers[Math.floor(Math.random() * covers.length)];
    
    if (assigningId === 'ALL') {
      setIsBroadcasting(true);
      try {
        await Promise.all(targets.map(student => {
          const formData = new FormData();
          formData.append('studentId', student._id);
          formData.append('title', title);
          formData.append('author', author);
          formData.append('category', 'reading');
          formData.append('coverUrl', coverUrl);
          formData.append('bookFile', file);
          return axios.post('http://localhost:5000/api/upload-book', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
        }));
        alert(`Book '${title}' Broadcasted Successfully!`);
        fetchStudents();
      } catch (err) { 
        console.error("Broadcast Auth Error:", err.response?.data || err);
        alert('Broadcast failed: ' + (err.response?.data?.error || err.message)); 
      }
      setIsBroadcasting(false);
    } else {
      const formData = new FormData();
      formData.append('studentId', assigningId);
      formData.append('title', title);
      formData.append('author', author);
      formData.append('category', 'reading');
      formData.append('coverUrl', coverUrl);
      formData.append('bookFile', file);

      try {
        await axios.post('http://localhost:5000/api/upload-book', formData, {
           headers: { 'Content-Type': 'multipart/form-data' }
        });
        alert(`Book '${title}' assigned successfully!`);
        fetchStudents();
      } catch (err) { 
        console.error("Upload Error:", err.response?.data || err);
        alert('Failed to assign book: ' + (err.response?.data?.error || err.message)); 
      }
    }
    e.target.value = null;
  };

  const handleAssignmentFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const defaultTitle = file.name.split('.').slice(0, -1).join('.') || file.name;
    const title = prompt("Confirm assignment title to send:", defaultTitle);
    if (!title) {
      e.target.value = null;
      return;
    }

    const targets = getTargetStudents();
    const assigningId = assigningAssignmentStudentIdRef.current;

    if (assigningId === 'ALL') {
      setIsBroadcasting(true);
      try {
        await Promise.all(targets.map(student => {
          const formData = new FormData();
          formData.append('studentId', student._id);
          formData.append('title', title);
          formData.append('course', 'Global Broadcast');
          formData.append('type', 'Homework');
          formData.append('status', 'not-started');
          formData.append('date', 'TBD');
          formData.append('time', 'Urgent');
          formData.append('typeColor', 'purple');
          formData.append('assignmentFile', file);
          return axios.post('http://localhost:5000/api/upload-assignment', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
        }));
        alert(`Assignment '${title}' Broadcasted Successfully!`);
        fetchStudents();
      } catch (err) {
        console.error("Broadcast Assignment Error:", err.response?.data || err);
        alert('Broadcast failed: ' + (err.response?.data?.error || err.message));
      }
      setIsBroadcasting(false);
    } else {
      const formData = new FormData();
      formData.append('studentId', assigningId);
      formData.append('title', title);
      formData.append('course', 'Teacher Assigned');
      formData.append('type', 'Homework');
      formData.append('status', 'not-started');
      formData.append('date', 'TBD');
      formData.append('time', 'Urgent');
      formData.append('typeColor', 'purple');
      formData.append('assignmentFile', file);

      try {
        await axios.post('http://localhost:5000/api/upload-assignment', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        alert(`Assignment '${title}' assigned successfully!`);
        fetchStudents();
      } catch (err) {
        console.error("Assignment Upload Error:", err.response?.data || err);
        alert('Failed to assign task: ' + (err.response?.data?.error || err.message));
      }
    }
    e.target.value = null;
  };

  const studentCardStyle = {
    backgroundColor: 'var(--bg-color-secondary)',
    padding: '1.5rem',
    borderRadius: '12px',
    border: '1px solid var(--border-color)',
    backdropFilter: 'blur(12px)',
    boxShadow: 'inset 0 0 20px rgba(0,136,255,0.05)',
    display: 'flex',
    flexDirection: 'column'
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', color: 'var(--text-primary)' }}>
      <input type="file" ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} />
      <input type="file" ref={assignmentFileInputRef} onChange={handleAssignmentFileChange} style={{ display: 'none' }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-blue)', letterSpacing: '2px', textShadow: '0 0 10px rgba(0,136,255,0.4)' }}>Teacher Gateway</h1>
        <button className="btn-ghost" onClick={handleLogout} style={{ color: 'var(--accent-red)', borderColor: 'var(--accent-red)' }}>🚪 Terminate Session</button>
      </div>
      
      <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Administrative access to deploy coursework directly into student databases.</p>
      
      <div style={{ backgroundColor: 'rgba(0,136,255,0.05)', border: '1px solid rgba(0,136,255,0.2)', padding: '1.5rem', borderRadius: '12px', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.2rem', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
            📡 Global Broadcast Hub
          </h2>
          <div style={{ display: 'flex', gap: '10px' }}>
            {selectedStudentIds.length === 0 ? (
              <span style={{ fontSize: '0.8rem', padding: '4px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.1)' }}>Mode: ALL STUDENTS ({students.length})</span>
            ) : (
              <span style={{ fontSize: '0.8rem', padding: '4px 8px', borderRadius: '4px', backgroundColor: 'rgba(0,255,204,0.2)', color: 'var(--accent-green)' }}>Mode: TARGETED SELECTION ({selectedStudentIds.length})</span>
            )}
            <button onClick={handleSelectAll} style={{ fontSize: '0.8rem', background: 'none', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>Select All</button>
            <button onClick={handleDeselectAll} style={{ fontSize: '0.8rem', background: 'none', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>Clear</button>
          </div>
        </div>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Distribute materials instantly to the selected targets. If no students are checked below, broadcasts go to EVERYONE.</p>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <button disabled={isBroadcasting} onClick={broadcastAssignment} style={{ padding: '0.8rem', backgroundColor: 'transparent', border: '1px solid var(--accent-blue)', color: 'var(--text-primary)', borderRadius: '8px', cursor: isBroadcasting ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}>
             {isBroadcasting ? 'Broadcasting...' : '📡 Broadcast Assignment'}
          </button>
          <button disabled={isBroadcasting} onClick={broadcastCourse} style={{ padding: '0.8rem', backgroundColor: 'transparent', border: '1px solid var(--accent-purple)', color: 'var(--text-primary)', borderRadius: '8px', cursor: isBroadcasting ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}>
             {isBroadcasting ? 'Broadcasting...' : '📡 Broadcast Course'}
          </button>
          <button disabled={isBroadcasting} onClick={broadcastTodo} style={{ padding: '0.8rem', backgroundColor: 'transparent', border: '1px solid var(--accent-green)', color: 'var(--text-primary)', borderRadius: '8px', cursor: isBroadcasting ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}>
             {isBroadcasting ? 'Broadcasting...' : '📡 Broadcast To-Do'}
          </button>
          <button disabled={isBroadcasting} onClick={triggerGlobalBookAssign} style={{ padding: '0.8rem', backgroundColor: 'transparent', border: '1px solid var(--accent-yellow)', color: 'var(--text-primary)', borderRadius: '8px', cursor: isBroadcasting ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}>
             {isBroadcasting ? 'Broadcasting...' : '📡 Broadcast Book'}
          </button>
        </div>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
        {students.map((student) => (
          <div key={student._id} style={{ ...studentCardStyle, border: selectedStudentIds.includes(student._id) ? '1px solid var(--accent-green)' : '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', color: 'var(--accent-green)', marginBottom: '0.2rem', textShadow: '0 0 5px rgba(0,255,204,0.3)' }}>
                  🎓 {student.fullName ? student.fullName : 'Unnamed Student'}
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>@{student.name}</p>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input 
                  type="checkbox" 
                  checked={selectedStudentIds.includes(student._id)} 
                  onChange={() => toggleStudentSelection(student._id)}
                  style={{ width: '20px', height: '20px', cursor: 'pointer', accentColor: 'var(--accent-green)' }}
                />
              </label>
            </div>
            
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Active Dependencies: {student.pendingTasks}</p>
            
            <div style={{ flex: 1, marginBottom: '1.5rem' }}>
              {student.assignments && student.assignments.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <strong style={{ color: 'var(--text-primary)', fontSize: '0.9rem' }}>Assignments:</strong>
                  <ul style={{ listStyle: 'none', padding: 0, marginTop: '0.5rem', fontSize: '0.85rem' }}>
                    {student.assignments.map(a => (
                      <li key={a._id} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                        <span style={{ textDecoration: a.status === 'done' ? 'line-through' : 'none' }}>{a.title}</span>
                        <span>{a.status === 'done' ? '✅' : '⏳'}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {student.todos && student.todos.length > 0 && (
                <div>
                  <strong style={{ color: 'var(--text-primary)', fontSize: '0.9rem' }}>To-Dos:</strong>
                  <ul style={{ listStyle: 'none', padding: 0, marginTop: '0.5rem', fontSize: '0.85rem' }}>
                    {student.todos.map(t => (
                      <li key={t._id} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                        <span style={{ textDecoration: t.done ? 'line-through' : 'none' }}>{t.text}</span>
                        <span>{t.done ? '✅' : '⏳'}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div 
                onClick={() => setSelectedStudent(student)}
                style={{ marginTop: '1.5rem', cursor: 'pointer', padding: '10px', borderRadius: '8px', backgroundColor: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', transition: '0.3s' }}
                className="hover-trigger"
              >
                <strong style={{ color: 'var(--accent-orange)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Reading Tracker (View Details):</strong>
                <div style={{ display: 'flex', gap: '10px', marginTop: '0.5rem' }}>
                  <div style={{ flex: 1, textAlign: 'center', backgroundColor: 'rgba(255,153,0,0.1)', padding: '5px', borderRadius: '4px' }}>
                    <div style={{ fontSize: '1rem', fontWeight: 'bold', color: 'var(--accent-orange)' }}>{student.readingList?.filter(b => b.category === 'reading').length || 0}</div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>READING</div>
                  </div>
                  <div style={{ flex: 1, textAlign: 'center', backgroundColor: 'rgba(0,255,204,0.1)', padding: '5px', borderRadius: '4px' }}>
                    <div style={{ fontSize: '1rem', fontWeight: 'bold', color: 'var(--accent-green)' }}>{student.readingList?.filter(b => b.category === 'finished').length || 0}</div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>FINISHED</div>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto', flexWrap: 'wrap' }}>
              <button 
                onClick={() => assignAssignment(student._id)}
                style={{ flex: 1, padding: '0.5rem', backgroundColor: 'var(--accent-blue)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600, fontSize: '0.8rem', boxShadow: '0 0 10px rgba(0,136,255,0.3)' }}
              >
                + Assign
              </button>
              <button 
                onClick={() => assignCourse(student._id)}
                style={{ flex: 1, padding: '0.5rem', backgroundColor: 'var(--accent-purple)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600, fontSize: '0.8rem', boxShadow: '0 0 10px rgba(187,0,255,0.3)' }}
              >
                + Course
              </button>
              <button 
                onClick={() => assignTodo(student._id)}
                style={{ flex: 1, padding: '0.5rem', backgroundColor: 'var(--accent-green)', color: '#000', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600, fontSize: '0.8rem', boxShadow: '0 0 10px rgba(0,255,204,0.3)' }}
              >
                + To-Do
              </button>
              <button 
                onClick={() => triggerBookAssign(student._id)}
                style={{ flex: 1, padding: '0.5rem', backgroundColor: 'var(--accent-yellow)', color: '#000', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600, fontSize: '0.8rem', boxShadow: '0 0 10px rgba(255,238,0,0.3)' }}
              >
                + Book
              </button>
            </div>
          </div>
        ))}
        {students.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>No students found in the database.</p>}
      </div>

      {/* Modal for Student Details */}
      {selectedStudent && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
           <div style={{ backgroundColor: '#0b0c10', border: '1px solid var(--border-color)', borderRadius: '16px', width: '100%', maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto', padding: '2rem', position: 'relative' }}>
              <button 
                onClick={() => setSelectedStudent(null)}
                style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'none', border: 'none', color: 'var(--accent-red)', fontSize: '1.5rem', cursor: 'pointer' }}
              >
                ✕
              </button>
              
              <h2 style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-blue)', marginBottom: '0.5rem' }}>Student Insight: {selectedStudent.fullName}</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Reviewing current thoughts and literature.</p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                 <div>
                    <h3 style={{ fontSize: '0.9rem', color: 'var(--accent-green)', textTransform: 'uppercase', marginBottom: '1rem' }}>Full Brain Dump</h3>
                    <div style={{ backgroundColor: 'rgba(26, 28, 35, 0.65)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.9rem', lineHeight: '1.6', minHeight: '200px', color: 'var(--text-primary)' }}>
                       "{selectedStudent.brainDump?.text || 'No thoughts recorded yet.'}"
                    </div>
                 </div>
                 <div>
                    <h3 style={{ fontSize: '0.9rem', color: 'var(--accent-orange)', textTransform: 'uppercase', marginBottom: '1rem' }}>Reading Shelf</h3>
                    <ul style={{ listStyle: 'none', padding: 0 }}>
                       {selectedStudent.readingList?.map(book => (
                         <li key={book._id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', padding: '0.5rem', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '4px' }}>
                           <img src={book.coverUrl} style={{ width: '30px', height: '45px', objectFit: 'cover', borderRadius: '2px' }} alt="" />
                           <div>
                              <div style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>{book.title}</div>
                              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{book.category.toUpperCase()}</div>
                           </div>
                         </li>
                       ))}
                       {selectedStudent.readingList?.length === 0 && <p style={{ fontSize: '0.85rem', opacity: 0.5 }}>Empty shelf.</p>}
                    </ul>
                 </div>
              </div>
           </div>
        </div>
      )}
      <style>{`
        .hover-trigger:hover { border-color: var(--accent-orange) !important; background-color: rgba(255,153,0,0.05) !important; }
      `}</style>
    </div>
  );
}
