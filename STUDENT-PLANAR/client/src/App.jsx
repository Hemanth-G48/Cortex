import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import RoleSelect from './views/common/RoleSelect';
import StudentApp from './StudentApp';
import TeacherDashboard from './views/teacher/TeacherDashboard';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<RoleSelect />} />
        <Route path="/student/dashboard/*" element={<StudentApp />} />
        <Route path="/teacher/dashboard" element={<TeacherDashboard />} />
      </Routes>
    </Router>
  );
}

export default App;
