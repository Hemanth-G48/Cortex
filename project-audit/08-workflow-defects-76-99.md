# Workflow Defects 76–99

## Data Consistency

### Defect 76: Completing a task on Vault doesn't update Dashboard
- **Module:** VaultDashboard.tsx + Dashboard.tsx
- **Current:** Each page fetches tasks independently
- **Problem:** Completing a task on Vault still shows it as pending on Dashboard
- **Fix:** Use shared task state or refresh on navigation
- **Priority:** Medium

### Defect 77: Habit logging on HabitTracker doesn't update Vault heatmap
- **Module:** HabitTracker.tsx + VaultDashboard.tsx
- **Current:** Both pages fetch habits independently
- **Problem:** Logging on one page doesn't reflect on the other
- **Fix:** Use shared state or refresh mechanism
- **Priority:** Medium

### Defect 78: Note edits don't appear in KB search
- **Module:** Notes.tsx (DB notes) vs KB search
- **Current:** Notes are in DB, KB has separate documents
- **Problem:** User edits a note but can't find it via KB search
- **Fix:** Bridge DB notes to KB or unify the systems
- **Priority:** High

### Defect 79: Course counts may be stale
- **Module:** courses.py (backend)
- **Current:** `current_assignment`/`total_assignments` stored on Course row
- **Problem:** Counts not auto-updated when assignments are added/completed
- **Fix:** Calculate counts dynamically from Assignment table
- **Priority:** Medium

### Defect 80: Goal progress not auto-calculated
- **Module:** Goals.tsx
- **Current:** `progress_percentage` is a manual field
- **Problem:** Progress doesn't update automatically from task completion
- **Fix:** Auto-calculate from linked tasks/habits
- **Priority:** Medium

## Missing CRUD Operations

### Defect 81: No schedule event creation from frontend
- **Module:** Schedule.tsx
- **Current:** Only displays events
- **Problem:** Users must use API directly to create events
- **Fix:** Add event creation form
- **Priority:** High

### Defect 82: No mission creation from frontend
- **Module:** Missions.tsx
- **Current:** Displays missions but no create button
- **Problem:** Users can't create missions from the UI
- **Fix:** Add mission creation modal
- **Priority:** Medium

### Defect 83: No reward creation from frontend
- **Module:** Rewards.tsx
- **Current:** Displays available/claimed rewards but no create
- **Problem:** Users can't add custom rewards
- **Fix:** Add reward creation form
- **Priority:** Medium

### Defect 84: No journal entry deletion
- **Module:** Journal.tsx
- **Current:** Can only create, not delete
- **Fix:** Add delete with confirmation
- **Priority:** Medium

### Defect 85: No fitness goal update
- **Module:** Fitness.tsx
- **Current:** Displays goals but no progress update UI
- **Fix:** Add progress update slider or input
- **Priority:** Medium

## Loading & Error States

### Defect 86: Multiple pages have silent error swallowing
- **Module:** Tasks.tsx, Quests.tsx, Projects.tsx, Fitness.tsx, LifeAreas.tsx
- **Current:** `.catch(() => {})` on all API calls
- **Problem:** Users see empty pages with no explanation
- **Fix:** Add error state per page with retry option
- **Priority:** High

### Defect 87: No global error boundary for API failures
- **Module:** App.tsx
- **Current:** ErrorBoundary catches render errors, not API errors
- **Problem:** API errors are invisible to users
- **Fix:** Add global API error handler (toast/notification)
- **Priority:** Medium

### Defect 88: No loading skeleton on most pages
- **Module:** Tasks.tsx, Projects.tsx, Fitness.tsx, LifeAreas.tsx, etc.
- **Current:** Pages show empty content while loading
- **Fix:** Add skeleton loaders matching the page layout
- **Priority:** Medium

## State Management

### Defect 89: No request cancellation on navigation
- **Module:** All pages with useEffect + API calls
- **Current:** If user navigates away during fetch, response updates unmounted component
- **Problem:** React warnings, potential state update on unmounted component
- **Fix:** Add AbortController to cancel pending requests
- **Priority:** Medium

### Defect 90: ProfileContext doesn't refresh after mutations
- **Module:** ProfileContext.tsx
- **Current:** Profile loaded on mount, not refreshed after XP/status changes
- **Problem:** Sidebar may show stale user stats
- **Fix:** Add refresh mechanism after mutations
- **Priority:** Medium

### Defect 91: No optimistic updates anywhere
- **Module:** All pages
- **Current:** All mutations wait for server response before UI update
- **Problem:** UI feels slow on poor connections
- **Fix:** Add optimistic updates for common actions (complete task, log habit)
- **Priority:** Low

## Second Brain Integration Gaps

### Defect 92: Daily Vault not integrated
- **Module:** second_brain/daily-life/ (empty folder)
- **Current:** No daily notes flow
- **Problem:** User's daily notes not surfaced in application
- **Fix:** Implement daily notes integration
- **Priority:** Medium

### Defect 93: Obsidian Vault not connected
- **Module:** Obsidian Vault/ (exists but unused)
- **Current:** Not registered as KB source
- **Problem:** User's existing vault not utilized
- **Fix:** Auto-detect and offer to connect as KB source
- **Priority:** Low

### Defect 94: KB documents don't appear in Notes page
- **Module:** Notes.tsx vs KB system
- **Current:** Two separate note systems
- **Problem:** Confusing for users — where are my notes?
- **Fix:** Unify or clearly separate the two systems
- **Priority:** High

### Defect 95: Search doesn't include traditional DB notes
- **Module:** VaultSearch.tsx / global search
- **Current:** Only searches KB documents
- **Problem:** DB notes are invisible to search
- **Fix:** Include DB notes in search results or migrate to KB
- **Priority:** High

## Persistence

### Defect 96: Settings page AI model not persisted to backend
- **Module:** Settings.tsx
- **Current:** AI model override saved in `localStorage`
- **Problem:** Doesn't persist across devices/browsers
- **Fix:** Save model preference to user profile on backend
- **Priority:** Low

### Defect 97: Habit tab selection not persisted
- **Module:** VaultDashboard.tsx
- **Current:** `activeTab` in useState
- **Problem:** Resets on page refresh
- **Fix:** Persist to localStorage or URL params
- **Priority:** Low

### Defect 98: Grid columns preference not persisted
- **Module:** VaultDashboard.tsx
- **Current:** `getGridCols()` reads from localStorage
- **Problem:** Works correctly but not synced across devices
- **Priority:** Low

### Defect 99: No data refresh mechanism after long idle
- **Module:** All pages
- **Current:** Data fetched once on mount, no auto-refresh
- **Problem:** Stale data if app is open for hours
- **Fix:** Add periodic refresh or visibility-based refresh
- **Priority:** Medium
