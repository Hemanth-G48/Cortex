import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { Courses } from './pages/Courses';
import { Tasks } from './pages/Tasks';
import { Schedule } from './pages/Schedule';
import { Assignments } from './pages/Assignments';
import { Exams } from './pages/Exams';
import { Goals } from './pages/Goals';
import { Notes } from './pages/Notes';
import { HabitTracker } from './pages/HabitTracker';
import { Pomodoro } from './pages/Pomodoro';
import { Fitness } from './pages/Fitness';
import { Journal } from './pages/Journal';
import { Quests } from './pages/Quests';
import { Projects } from './pages/Projects';
import { LifeAreas } from './pages/LifeAreas';
import { Character } from './pages/Character';
import { Rewards } from './pages/Rewards';
import { Missions } from './pages/Missions';
import { RPGDashboard } from './pages/RPGDashboard';
import { VaultDashboard } from './pages/VaultDashboard';
import { VaultDatabase } from './pages/VaultDatabase';
import { HabitReport } from './pages/HabitReport';
import { ArchiveHabits } from './pages/ArchiveHabits';
import { GoalsSetting } from './pages/GoalsSetting';
import { HabitLogs } from './pages/HabitLogs';
import { GridDesign } from './pages/GridDesign';
import { LifePlannerDashboard } from './pages/LifePlannerDashboard';
import { QuestCentreDashboard } from './pages/QuestCentreDashboard';
import { GamifiedHabitTracker } from './pages/GamifiedHabitTracker';
import { FitnessHubDashboard } from './pages/FitnessHubDashboard';

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/courses" element={<Courses />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/assignments" element={<Assignments />} />
            <Route path="/exams" element={<Exams />} />
            <Route path="/goals" element={<Goals />} />
            <Route path="/notes" element={<Notes />} />
            <Route path="/habits" element={<HabitTracker />} />
            <Route path="/pomodoro" element={<Pomodoro />} />
            <Route path="/fitness" element={<Fitness />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/quests" element={<Quests />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/life-areas" element={<LifeAreas />} />
            <Route path="/character" element={<Character />} />
            <Route path="/rewards" element={<Rewards />} />
            <Route path="/missions" element={<Missions />} />
            <Route path="/rpg-dashboard" element={<RPGDashboard />} />
            <Route path="/vault" element={<VaultDashboard />} />
            <Route path="/vault-database" element={<VaultDatabase />} />
            <Route path="/habits/:habitId/report" element={<HabitReport />} />
            <Route path="/habits/archive" element={<ArchiveHabits />} />
            <Route path="/goals-setting" element={<GoalsSetting />} />
            <Route path="/habit-logs" element={<HabitLogs />} />
            <Route path="/grid-design" element={<GridDesign />} />
            <Route path="/habit-report" element={<HabitReport />} />
            <Route path="/archive-habits" element={<ArchiveHabits />} />
            <Route path="/life-planner" element={<LifePlannerDashboard />} />
            <Route path="/quest-centre" element={<QuestCentreDashboard />} />
            <Route path="/habit-tracker" element={<GamifiedHabitTracker />} />
            <Route path="/fitness-hub" element={<FitnessHubDashboard />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
