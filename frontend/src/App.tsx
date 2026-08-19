import { lazy, Suspense, useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { AIChat } from './components/AIChat';
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { PageLoader } from './components/shared/PageLoader';
import { CrashFallback } from './components/shared/CrashFallback';
import { CommandPalette } from './components/kb/CommandPalette';
import { ProfileProvider } from './context/ProfileContext';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { ShortcutModal } from './components/ShortcutModal';
import { QuickCapture } from './components/QuickCapture';
import { InstallBanner } from './components/InstallBanner';
import { isChunkLoadError } from './utils/chunkErrors';

// ── Route code-splitting ─────────────────────────────────────────────────────
// Every page is React.lazy: its chunk loads on first navigation instead of at
// startup, so the initial bundle is just the shell + the first page. Pages use
// named exports, hence the `then((m) => ({ default: m.X }))` mapper.
// Module-scope lazy is deliberate — a lazy created inside a component body
// (e.g. via useState) breaks React's Suspense resolution.
const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })));
const Courses = lazy(() => import('./pages/Courses').then((m) => ({ default: m.Courses })));
const CourseDetail = lazy(() => import('./pages/CourseDetail').then((m) => ({ default: m.CourseDetail })));
const Tasks = lazy(() => import('./pages/Tasks').then((m) => ({ default: m.Tasks })));
const Schedule = lazy(() => import('./pages/Schedule').then((m) => ({ default: m.Schedule })));
const Assignments = lazy(() => import('./pages/Assignments').then((m) => ({ default: m.Assignments })));
const Exams = lazy(() => import('./pages/Exams').then((m) => ({ default: m.Exams })));
const Goals = lazy(() => import('./pages/Goals').then((m) => ({ default: m.Goals })));
const Notes = lazy(() => import('./pages/Notes').then((m) => ({ default: m.Notes })));
const HabitTracker = lazy(() => import('./pages/HabitTracker').then((m) => ({ default: m.HabitTracker })));
const Pomodoro = lazy(() => import('./pages/Pomodoro').then((m) => ({ default: m.Pomodoro })));
const Fitness = lazy(() => import('./pages/Fitness').then((m) => ({ default: m.Fitness })));
const Journal = lazy(() => import('./pages/Journal').then((m) => ({ default: m.Journal })));
const Quests = lazy(() => import('./pages/Quests').then((m) => ({ default: m.Quests })));
const Projects = lazy(() => import('./pages/Projects').then((m) => ({ default: m.Projects })));
const LifeAreas = lazy(() => import('./pages/LifeAreas').then((m) => ({ default: m.LifeAreas })));
const Character = lazy(() => import('./pages/Character').then((m) => ({ default: m.Character })));
const Rewards = lazy(() => import('./pages/Rewards').then((m) => ({ default: m.Rewards })));
const Missions = lazy(() => import('./pages/Missions').then((m) => ({ default: m.Missions })));
const RPGDashboard = lazy(() => import('./pages/RPGDashboard').then((m) => ({ default: m.RPGDashboard })));
const VaultDashboard = lazy(() => import('./pages/VaultDashboard').then((m) => ({ default: m.VaultDashboard })));
const VaultDatabase = lazy(() => import('./pages/VaultDatabase').then((m) => ({ default: m.VaultDatabase })));
const HabitReport = lazy(() => import('./pages/HabitReport').then((m) => ({ default: m.HabitReport })));
const ArchiveHabits = lazy(() => import('./pages/ArchiveHabits').then((m) => ({ default: m.ArchiveHabits })));
const GoalsSetting = lazy(() => import('./pages/GoalsSetting').then((m) => ({ default: m.GoalsSetting })));
const HabitLogs = lazy(() => import('./pages/HabitLogs').then((m) => ({ default: m.HabitLogs })));
const GridDesign = lazy(() => import('./pages/GridDesign').then((m) => ({ default: m.GridDesign })));
const LifePlannerDashboard = lazy(() => import('./pages/LifePlannerDashboard').then((m) => ({ default: m.LifePlannerDashboard })));
const QuestCentreDashboard = lazy(() => import('./pages/QuestCentreDashboard').then((m) => ({ default: m.QuestCentreDashboard })));
const GamifiedHabitTracker = lazy(() => import('./pages/GamifiedHabitTracker').then((m) => ({ default: m.GamifiedHabitTracker })));
const FitnessHubDashboard = lazy(() => import('./pages/FitnessHubDashboard').then((m) => ({ default: m.FitnessHubDashboard })));
const Grades = lazy(() => import('./pages/Grades').then((m) => ({ default: m.Grades })));
const Flashcards = lazy(() => import('./pages/Flashcards').then((m) => ({ default: m.Flashcards })));
const StudyPlans = lazy(() => import('./pages/StudyPlans').then((m) => ({ default: m.StudyPlans })));
const Quiz = lazy(() => import('./pages/Quiz').then((m) => ({ default: m.Quiz })));
const SyllabusImport = lazy(() => import('./pages/SyllabusImport').then((m) => ({ default: m.SyllabusImport })));
const Analytics = lazy(() => import('./pages/Analytics').then((m) => ({ default: m.Analytics })));
const Settings = lazy(() => import('./pages/Settings').then((m) => ({ default: m.Settings })));
const Reading = lazy(() => import('./pages/Reading').then((m) => ({ default: m.Reading })));
const BookGapReader = lazy(() => import('./pages/BookGapReader').then((m) => ({ default: m.BookGapReader })));
const KnowledgeBase = lazy(() => import('./pages/KnowledgeBase').then((m) => ({ default: m.KnowledgeBase })));
const Today = lazy(() => import('./pages/Today').then((m) => ({ default: m.Today })));
const WeeklyReview = lazy(() => import('./pages/WeeklyReview').then((m) => ({ default: m.WeeklyReview })));
const LearningPlanner = lazy(() => import('./pages/LearningPlanner').then((m) => ({ default: m.LearningPlanner })));
const Workflows = lazy(() => import('./pages/Workflows').then((m) => ({ default: m.Workflows })));
const KnowledgeGraph = lazy(() => import('./pages/KnowledgeGraph').then((m) => ({ default: m.KnowledgeGraph })));
const VaultSearch = lazy(() => import('./pages/VaultSearch').then((m) => ({ default: m.VaultSearch })));
const KbInsights = lazy(() => import('./pages/KbInsights').then((m) => ({ default: m.KbInsights })));
const GapAnalysis = lazy(() => import('./pages/GapAnalysis').then((m) => ({ default: m.GapAnalysis })));
const Tutor = lazy(() => import('./pages/Tutor').then((m) => ({ default: m.Tutor })));
const Practice = lazy(() => import('./pages/Practice').then((m) => ({ default: m.Practice })));
const Mocks = lazy(() => import('./pages/Mocks').then((m) => ({ default: m.Mocks })));
const Interview = lazy(() => import('./pages/Interview').then((m) => ({ default: m.Interview })));
const Skills = lazy(() => import('./pages/Skills').then((m) => ({ default: m.Skills })));
const FlashcardReview = lazy(() => import('./pages/FlashcardReview').then((m) => ({ default: m.FlashcardReview })));
const Leaderboard = lazy(() => import('./pages/Leaderboard').then((m) => ({ default: m.Leaderboard })));
const QualityList = lazy(() => import('./pages/QualityList').then((m) => ({ default: m.QualityList })));
const Browse = lazy(() => import('./pages/Browse').then((m) => ({ default: m.Browse })));
const Subject = lazy(() => import('./pages/Subject').then((m) => ({ default: m.Subject })));
const Subjects = lazy(() => import('./pages/Subjects').then((m) => ({ default: m.Subjects })));
const SubjectWorkspace = lazy(() => import('./pages/SubjectWorkspace').then((m) => ({ default: m.SubjectWorkspace })));
const Unit = lazy(() => import('./pages/Unit').then((m) => ({ default: m.Unit })));
const DomainDetail = lazy(() => import('./pages/DomainDetail').then((m) => ({ default: m.DomainDetail })));
const Admin = lazy(() => import('./pages/Admin').then((m) => ({ default: m.Admin })));
const CompleteProfile = lazy(() => import('./pages/CompleteProfile').then((m) => ({ default: m.CompleteProfile })));

// App-level crash fallback: catches a lazy chunk failing to load or a page
// render error. React.lazy caches a rejected import, so Retry reloads for
// chunk failures (see utils/chunkErrors.ts) and resets the boundary
// otherwise.
const routeCrashFallback = (error: Error, reset: () => void) => (
  <div className="page-section" data-testid="route-error-boundary">
    <CrashFallback
      title="This page failed to render."
      error={error}
      onRetry={() => (isChunkLoadError(error) ? window.location.reload() : reset())}
    />
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <ProfileProvider>
        <AppShell />
      </ProfileProvider>
    </BrowserRouter>
  );
}

function AppShell() {
  const [shortcutOpen, setShortcutOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const location = useLocation();

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
        <ErrorBoundary resetKey={location.pathname} fallback={routeCrashFallback}>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/today" element={<Today />} />
              <Route path="/weekly-review" element={<WeeklyReview />} />
              <Route
                path="/learning-planner"
                element={
                  <ErrorBoundary
                    resetKey="learning-planner"
                    fallback={(error, reset) => (
                      <div className="page-section" data-testid="learning-planner-error-boundary">
                        <CrashFallback
                          title="The Learning Path Planner failed to render."
                          error={error}
                          onRetry={reset}
                        />
                      </div>
                    )}
                  >
                    <LearningPlanner />
                  </ErrorBoundary>
                }
              />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/courses" element={<Courses />} />
              <Route path="/courses/:id" element={<CourseDetail />} />
              <Route path="/courses/:courseId/domain/:domainId" element={<DomainDetail />} />
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
              <Route path="/reading" element={<Reading />} />
              <Route path="/book-gaps" element={<BookGapReader />} />
              <Route path="/book-gaps/:bookId" element={<BookGapReader />} />
              <Route path="/knowledge-base" element={<KnowledgeBase />} />
              <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
              <Route path="/vault-search" element={<VaultSearch />} />
              <Route path="/kb-insights" element={<KbInsights />} />
              <Route path="/gap-analysis" element={<GapAnalysis />} />
              {/* ----- Phase 7: AI Tutor & Assessment (Ideas 61-70) ----- */}
              <Route path="/tutor" element={<Tutor />} />
              <Route path="/practice" element={<Practice />} />
              <Route path="/mocks" element={<Mocks />} />
              <Route path="/interview" element={<Interview />} />
              <Route path="/skills" element={<Skills />} />
              <Route path="/flashcard-review" element={<FlashcardReview />} />
              <Route path="/leaderboard" element={<Leaderboard />} />
              <Route path="/quality" element={<QualityList />} />
              <Route path="/browse" element={<Browse />} />
              <Route path="/subjects" element={<Subjects />} />
              <Route path="/subjects/profiles/:id" element={<SubjectWorkspace />} />
              <Route path="/subjects/:id" element={<Subject />} />
              <Route path="/units/:id" element={<Unit />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/complete-profile" element={<CompleteProfile />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
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
