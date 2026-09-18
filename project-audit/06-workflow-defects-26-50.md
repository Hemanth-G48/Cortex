# Workflow Defects 26–50

## Projects

### Defect 26: Projects page has no CRUD functionality
- **Module:** Projects.tsx
- **Current:** Displays projects but no create/edit/delete buttons
- **Problem:** Users can't manage projects from this page
- **Fix:** Add project creation modal and edit/delete actions
- **Priority:** High

### Defect 27: Projects page has no link to project detail
- **Module:** Projects.tsx
- **Current:** Projects rendered as plain cards
- **Problem:** Users can't view project tasks or details
- **Fix:** Add `<Link>` to project detail view
- **Priority:** Medium

### Defect 28: Projects page has no loading/error states
- **Module:** Projects.tsx
- **Current:** `.catch(() => {})` swallows errors
- **Fix:** Add loading skeleton and error message
- **Priority:** Medium

## Schedule

### Defect 29: Schedule page has no event creation
- **Module:** Schedule.tsx
- **Current:** Displays timetable grid from API but no create/edit
- **Problem:** Users can't manage schedule events
- **Fix:** Add event creation form and edit/delete
- **Priority:** High

### Defect 30: Schedule page has no error state
- **Module:** Schedule.tsx
- **Current:** `.catch(() => {})` swallows errors
- **Fix:** Add error message
- **Priority:** Low

## Fitness

### Defect 31: Fitness page has no workout creation
- **Module:** Fitness.tsx
- **Current:** Displays workouts and goals but no create buttons
- **Problem:** Users can't log new workouts from this page
- **Fix:** Add workout creation form
- **Priority:** Medium

### Defect 32: Fitness page has no goal creation
- **Module:** Fitness.tsx
- **Current:** Displays fitness goals but no create button
- **Fix:** Add fitness goal creation form
- **Priority:** Medium

### Defect 33: Fitness page has no loading/error states
- **Module:** Fitness.tsx
- **Current:** `.catch(() => {})` swallows errors
- **Fix:** Add loading skeleton and error message
- **Priority:** Medium

## LifeAreas

### Defect 34: LifeAreas page has no CRUD
- **Module:** LifeAreas.tsx
- **Current:** Displays life areas but no create/edit/delete
- **Problem:** Users can't manage life areas
- **Fix:** Add lifecycle management
- **Priority:** Medium

### Defect 35: LifeAreas page has no loading/error states
- **Module:** LifeAreas.tsx
- **Current:** `.catch(() => {})` swallows errors
- **Fix:** Add loading skeleton and error message
- **Priority:** Low

## Exams

### Defect 36: Exams page has no create/edit functionality
- **Module:** Exams.tsx
- **Current:** Likely displays exams but no management UI
- **Fix:** Add exam creation and management
- **Priority:** Medium

## Study Plans

### Defect 37: StudyPlans page has no create from AI
- **Module:** StudyPlans.tsx
- **Current:** Displays study plans but may lack AI generation integration
- **Fix:** Add "Generate with AI" button using `endpoints.ai.studyPlan()`
- **Priority:** Medium

## Quiz

### Defect 38: Quiz page doesn't track history
- **Module:** Quiz.tsx
- **Current:** Generates quiz but history may not be visible
- **Fix:** Add quiz history view using `endpoints.quizzes.history()`
- **Priority:** Low

## Syllabus Import

### Defect 39: SyllabusImport doesn't show import progress
- **Module:** SyllabusImport.tsx
- **Current:** May not show loading state during AI processing
- **Fix:** Add progress indicator for syllabus parsing
- **Priority:** Medium

## Analytics

### Defect 40: Analytics page has no data export
- **Module:** Analytics.tsx
- **Current:** Displays charts but no export
- **Fix:** Add CSV/PDF export for analytics data
- **Priority:** Low

### Defect 41: Analytics summary uses `.catch(() => {})`
- **Module:** Analytics.tsx
- **Current:** All 5 API calls have silent error handling
- **Fix:** Add per-section error states
- **Priority:** Medium

## Grades

### Defect 42: Grade predictor recalculates on every render
- **Module:** Grades.tsx
- **Current:** `predict` is called in `useEffect` with `currentPct`, `finalWeight`, `desiredGrade` deps
- **Problem:** Triggers API call on every input change (no debounce)
- **Fix:** Add debounce (300ms) to predictor
- **Priority:** Low

### Defect 43: Grades page has no delete grade functionality
- **Module:** Grades.tsx
- **Current:** Can add grades but not delete them
- **Fix:** Add delete button per grade
- **Priority:** Medium

## Flashcards

### Defect 44: Flashcard XP not persisted to user profile
- **Module:** Flashcards.tsx
- **Current:** `xpEarned` tracked in component state only
- **Problem:** XP earned during study session lost on navigation
- **Fix:** Persist XP to user profile via API after session
- **Priority:** Medium

### Defect 45: Flashcard deck deletion has no confirmation
- **Module:** Flashcards.tsx
- **Current:** `handleDeleteDeck(id)` calls API directly
- **Problem:** Accidental deletion of entire deck
- **Fix:** Add confirmation dialog
- **Priority:** High

### Defect 46: Flashcard generation limit not enforced on frontend
- **Module:** Flashcards.tsx
- **Current:** Generates up to 12 cards, no limit display
- **Problem:** User doesn't know the limit or remaining budget
- **Fix:** Show generation count and budget remaining
- **Priority:** Low

## Reading

### Defect 47: Reading page may not show empty state
- **Module:** Reading.tsx
- **Current:** May show empty list when no books
- **Fix:** Add empty state with "Add your first book" prompt
- **Priority:** Low

## Goals

### Defect 48: Goals page may lack goal creation
- **Module:** Goals.tsx
- **Current:** Displays goals but may lack full CRUD
- **Fix:** Ensure create/update/delete are all available
- **Priority:** Medium

### Defect 49: Goals page has no progress update UI
- **Module:** Goals.tsx
- **Current:** Goals show progress_percentage but no way to update
- **Fix:** Add inline progress slider or edit modal
- **Priority:** Medium

## Character

### Defect 50: Character page "Add XP" doesn't persist meaningful changes
- **Module:** Character.tsx
- **Current:** Adds XP via API but doesn't trigger level-up calculation
- **Problem:** XP increases but level/stats may not update correctly
- **Fix:** Ensure level-up logic runs server-side after XP addition
- **Priority:** Medium
