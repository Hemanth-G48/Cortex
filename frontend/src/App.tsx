import { useState } from 'react';
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
import { Grades } from './pages/Grades';
import { Flashcards } from './pages/Flashcards';
import { StudyPlans } from './pages/StudyPlans';
import { Quiz } from './pages/Quiz';
import { SyllabusImport } from './pages/SyllabusImport';
import { AIChat } from './components/AIChat';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { Login } from './pages/Login';
import { Reading } from './pages/Reading';
import { KnowledgeBase } from './pages/KnowledgeBase';
import { KnowledgeGraph } from './pages/KnowledgeGraph';
import { VaultSearch } from './pages/VaultSearch';
import { KbInsights } from './pages/KbInsights';
import { Tutor } from './pages/Tutor';
import { Practice } from './pages/Practice';
import { Mocks } from './pages/Mocks';
import { Interview } from './pages/Interview';
import { Skills } from './pages/Skills';
import { FlashcardReview } from './pages/FlashcardReview';
import { Leaderboard } from './pages/Leaderboard';
import { QualityList } from './pages/QualityList';
import { CommandPalette } from './components/kb/CommandPalette';
import { Teacher } from './pages/Teacher';
import { Browse } from './pages/Browse';
import { Subject } from './pages/Subject';
import { Subjects } from './pages/Subjects';
import { SubjectWorkspace } from './pages/SubjectWorkspace';
import { Unit } from './pages/Unit';
import { Admin } from './pages/Admin';
import { CompleteProfile } from './pages/CompleteProfile';
import { RoleGate } from './components/auth/RoleGate';
import { AuthProvider } from './context/AuthContext';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { ShortcutModal } from './components/ShortcutModal';
import { QuickCapture } from './components/QuickCapture';
import { InstallBanner } from './components/InstallBanner';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  );
}

function AppShell() {
  const [shortcutOpen, setShortcutOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);

  // Global keyboard shortcuts: g+letter navigation, Ctrl+K AI chat,
  // Ctrl+Shift+A quick capture, `?` shortcut help.
  useKeyboardShortcuts({
    onShortcutHelp: () => setShortcutOpen(true),
    onQuickCapture: () => setCaptureOpen(true),
  });

  return (
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
          <Route path="/grades" element={<Grades />} />
          <Route path="/flashcards" element={<Flashcards />} />
          <Route path="/study-plans" element={<StudyPlans />} />
          <Route path="/quiz" element={<Quiz />} />
          <Route path="/import" element={<SyllabusImport />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
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
          <Route path="/login" element={<Login />} />
          <Route path="/reading" element={<Reading />} />
          <Route path="/knowledge-base" element={<KnowledgeBase />} />
          <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
          <Route path="/vault-search" element={<VaultSearch />} />
          <Route path="/kb-insights" element={<KbInsights />} />
          {/* ----- Phase 7: AI Tutor & Assessment (Ideas 61-70) ----- */}
          <Route path="/tutor" element={<Tutor />} />
          <Route path="/practice" element={<Practice />} />
          <Route path="/mocks" element={<Mocks />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/flashcard-review" element={<FlashcardReview />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/quality" element={<QualityList />} />
          <Route path="/teacher" element={<RoleGate role="teacher"><Teacher /></RoleGate>} />
          <Route path="/browse" element={<Browse />} />
          <Route path="/subjects" element={<Subjects />} />
          <Route path="/subjects/profiles/:id" element={<SubjectWorkspace />} />
          <Route path="/subjects/:id" element={<Subject />} />
          <Route path="/units/:id" element={<Unit />} />
          <Route path="/admin" element={<RoleGate role="admin"><Admin /></RoleGate>} />
          <Route path="/complete-profile" element={<CompleteProfile />} />
        </Routes>
      </main>
      <AIChat />
      <CommandPalette />
      <QuickCapture open={captureOpen} onOpenChange={setCaptureOpen} />
      <ShortcutModal open={shortcutOpen} onClose={() => setShortcutOpen(false)} />
      <InstallBanner />
    </div>
  );
}

export default App;
