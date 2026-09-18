# Workflow Defects 01–25

## Dashboard & Navigation

### Defect 01: Dashboard shows 0s before data loads
- **Module:** Dashboard.tsx
- **Current:** stat-grid tiles render immediately with computed values (0, "0/0", "0%")
- **Problem:** User sees empty stats briefly while API calls are in-flight
- **Fix:** Add loading skeleton or show "Loading..." state
- **Priority:** Medium

### Defect 02: Dashboard stat tiles have no error state
- **Module:** Dashboard.tsx
- **Current:** `.catch(() => {})` silently swallows all API errors
- **Problem:** If API fails, tiles show 0 indefinitely with no indication of failure
- **Fix:** Add error state per data section, show retry option
- **Priority:** Medium

### Defect 03: Dashboard courses don't link to CourseDetail
- **Module:** Dashboard.tsx
- **Current:** Course cards rendered as plain `<div>` elements
- **Problem:** Users can't navigate to a course from the dashboard
- **Fix:** Wrap course cards in `<Link to={/courses/${c.id}}>`
- **Priority:** Medium

### Defect 04: Dashboard tasks table has no link to task detail
- **Module:** Dashboard.tsx
- **Current:** Tasks rendered in a table with no click handler
- **Problem:** Users can't navigate to task management from dashboard
- **Fix:** Add `onClick` to navigate to /tasks
- **Priority:** Low

### Defect 05: Dashboard has no loading state
- **Module:** Dashboard.tsx
- **Current:** Page renders immediately with empty arrays
- **Problem:** Flash of empty content before data loads
- **Fix:** Add a loading spinner/skeleton while initial fetch completes
- **Priority:** Medium

## Tasks

### Defect 06: Tasks page has no create task UI
- **Module:** Tasks.tsx
- **Current:** Displays tasks via TaskList component but no "Add Task" button visible
- **Problem:** Users can only create tasks from other pages (Vault), not from Tasks page
- **Fix:** Add task creation form or modal to Tasks page
- **Priority:** High

### Defect 07: Tasks page has no error/loading states
- **Module:** Tasks.tsx
- **Current:** `.catch(() => {})` swallows errors, no loading indicator
- **Problem:** If API fails, page shows empty table with no explanation
- **Fix:** Add loading skeleton and error message
- **Priority:** Medium

### Defect 08: Tasks page has no search/filter
- **Module:** Tasks.tsx
- **Current:** Shows all tasks in a flat list
- **Problem:** With many tasks, hard to find specific ones
- **Fix:** Add search bar and filter by status/priority/subject
- **Priority:** Medium

### Defect 09: Task deletion has no confirmation dialog
- **Module:** TaskList.tsx / HabitTracker.tsx
- **Current:** `handleDelete` calls API immediately
- **Problem:** Accidental clicks permanently delete data
- **Fix:** Add confirmation modal before destructive actions
- **Priority:** High

### Defect 10: Tasks don't refresh after completing from Dashboard
- **Module:** Dashboard.tsx
- **Current:** Task completion not handled on Dashboard
- **Problem:** Dashboard doesn't show completed task status
- **Fix:** Add complete button or link to tasks page
- **Priority:** Low

## Habits

### Defect 11: Habit deletion has no confirmation
- **Module:** HabitTracker.tsx
- **Current:** `handleDelete(id)` calls `endpoints.habits.delete(id)` directly
- **Problem:** Single click deletes a habit permanently
- **Fix:** Add confirmation dialog
- **Priority:** High

### Defect 12: HabitTracker page doesn't sync with VaultDashboard
- **Module:** HabitTracker.tsx + VaultDashboard.tsx
- **Current:** Both pages fetch habits independently
- **Problem:** Logging a habit on one page doesn't reflect on the other without reload
- **Fix:** Add shared state or callback refresh mechanism
- **Priority:** Medium

### Defect 13: No "create habit" UI on HabitTracker page
- **Module:** HabitTracker.tsx
- **Current:** Only displays existing habits with log/delete buttons
- **Problem:** Users can't create new habits from this page
- **Fix:** Add habit creation form
- **Priority:** High

### Defect 14: HabitTracker has no loading/error states
- **Module:** HabitTracker.tsx
- **Current:** Empty page until data loads
- **Problem:** No feedback during loading or on failure
- **Fix:** Add loading skeleton and error message
- **Priority:** Medium

## Notes

### Defect 15: Notes page doesn't use Second Brain
- **Module:** Notes.tsx
- **Current:** Uses `endpoints.notes.*` (traditional DB notes table)
- **Problem:** Notes created here don't appear in KB search or vault
- **Fix:** Either migrate to KB documents or bridge the two systems
- **Priority:** High

### Defect 16: Notes page has no delete confirmation
- **Module:** Notes.tsx
- **Current:** `remove()` deletes immediately on button click
- **Problem:** Accidental deletion with no undo
- **Fix:** Add confirmation dialog
- **Priority:** High

### Defect 17: Notes search is client-side only
- **Module:** Notes.tsx
- **Current:** `filtered` computed via `useMemo` on the `notes` array
- **Problem:** Doesn't search note content deeply, no full-text search
- **Fix:** Use KB search for note content or add client-side content search
- **Priority:** Medium

### Defect 18: Notes have no empty state message
- **Module:** Notes.tsx
- **Current:** Shows "No notes found." only when search returns nothing
- **Problem:** When no notes exist at all, user sees empty list
- **Fix:** Show "Create your first note" prompt
- **Priority:** Low

## Journal

### Defect 19: Journal has no error handling
- **Module:** Journal.tsx
- **Current:** `handleSubmit` has no try/catch, `load()` has `.catch(() => {})`
- **Problem:** If save fails, user gets no feedback
- **Fix:** Add try/catch with toast notification
- **Priority:** Medium

### Defect 20: Journal has no edit/update capability
- **Module:** Journal.tsx
- **Current:** Can only create entries, cannot edit or delete
- **Problem:** Users can't correct mistakes or remove entries
- **Fix:** Add edit and delete functionality
- **Priority:** Medium

### Defect 21: Journal has no loading state
- **Module:** Journal.tsx
- **Current:** Empty page until entries load
- **Fix:** Add loading indicator
- **Priority:** Low

## Quests & RPG

### Defect 22: Quests page has no create/delete functionality
- **Module:** Quests.tsx
- **Current:** Displays quests from API but no CRUD UI
- **Problem:** Users can't manage quests from this page
- **Fix:** Add quest creation and deletion
- **Priority:** Medium

### Defect 23: Quests page filter doesn't persist on navigation
- **Module:** Quests.tsx
- **Current:** Filter state in local `useState`
- **Problem:** Filter resets when navigating away and back
- **Fix:** Use URL search params for filter state
- **Priority:** Low

### Defect 24: Missions page creates inline API calls
- **Module:** Missions.tsx
- **Current:** Uses `api.get<MissionTask[]>('/missions/${missionId}/tasks')` directly
- **Problem:** Bypasses the typed endpoints object, inconsistent pattern
- **Fix:** Add `endpoints.missions.listTasks()` (which exists but isn't used here)
- **Priority:** Low

### Defect 25: RPGDashboard character ID hardcoded to 1
- **Module:** RPGDashboard.tsx
- **Current:** `endpoints.characters.get(1)` hardcoded
- **Problem:** Won't work for any other user (though single-user app)
- **Fix:** Use profile context user ID
- **Priority:** Low
