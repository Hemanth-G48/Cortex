# Workflow Defects 51–75

## Vault Dashboard

### Defect 51: VaultDashboard N+1 heatmap loading
- **Module:** VaultDashboard.tsx
- **Current:** `habitsData.map((h) => reloadHabit(h.id))` — one API call per habit
- **Problem:** With many habits, this creates excessive API calls
- **Fix:** Add batch heatmap endpoint or load all heatmaps in one call
- **Priority:** Medium

### Defect 52: VaultDashboard N+1 project summary loading
- **Module:** VaultDashboard.tsx
- **Current:** `projectsData.map((p) => endpoints.projects.summary(p.id))` — one call per project
- **Problem:** Excessive API calls
- **Fix:** Add batch project summary endpoint
- **Priority:** Medium

### Defect 53: VaultDashboard task tab doesn't persist selection
- **Module:** VaultDashboard.tsx
- **Current:** `activeTab` in useState, resets on remount
- **Problem:** Navigating away loses the active tab
- **Fix:** Use URL search params for tab state
- **Priority:** Low

### Defect 54: VaultDashboard create task button location
- **Module:** VaultDashboard.tsx
- **Current:** `showCreate` state controls modal, button in sidebar
- **Problem:** Users may not find the create button
- **Fix:** Make create button more prominent
- **Priority:** Low

## Second Brain / Knowledge Base

### Defect 55: KB Sources page may lack delete confirmation
- **Module:** KbSources component
- **Current:** Source removal deletes all documents
- **Problem:** Destructive action without warning
- **Fix:** Add confirmation dialog with document count warning
- **Priority:** High

### Defect 56: KB Search has no loading state
- **Module:** VaultSearch.tsx
- **Current:** May show empty results while searching
- **Fix:** Add loading spinner during search
- **Priority:** Medium

### Defect 57: KB Search has no empty state for no results
- **Module:** VaultSearch.tsx
- **Current:** May show blank when no results
- **Fix:** Add "No results found" message with suggestions
- **Priority:** Low

### Defect 58: KnowledgeGraph has no fallback for empty graph
- **Module:** KnowledgeGraph.tsx
- **Current:** Sigma.js may render empty canvas
- **Fix:** Add empty state message
- **Priority:** Low

### Defect 59: KB Source scan has no progress indicator
- **Module:** KB source management
- **Current:** Scan triggers background job, no frontend progress
- **Problem:** User doesn't know if scan is running or complete
- **Fix:** Show scan status/progress in UI
- **Priority:** Medium

### Defect 60: KB Backup/Restore lacks validation feedback
- **Module:** Settings.tsx
- **Current:** Backup/restore shows notice but no detailed progress
- **Fix:** Show file-by-file progress during restore
- **Priority:** Low

## AI Features

### Defect 61: AI Chat has no conversation persistence
- **Module:** AIChat.tsx
- **Current:** Chat history lives in component state
- **Problem:** Closing the chat loses all history
- **Fix:** Persist chat history to localStorage or API
- **Priority:** Medium

### Defect 62: AI Chat has no streaming response
- **Module:** AIChat.tsx
- **Current:** Waits for full response before displaying
- **Problem:** Long responses feel slow
- **Fix:** Implement SSE streaming for AI responses
- **Priority:** Medium

### Defect 63: AI Insights card has no retry on failure
- **Module:** AiInsightsCard component
- **Current:** If insights API fails, card shows error
- **Fix:** Add retry button
- **Priority:** Low

### Defect 64: AI Tutor has no rate limiting display
- **Module:** Tutor.tsx
- **Current:** No indication of API budget remaining
- **Fix:** Show daily budget remaining
- **Priority:** Low

## Settings

### Defect 65: Settings page has no unsaved changes warning
- **Module:** Settings.tsx
- **Current:** AI model selection saves immediately
- **Problem:** No confirmation or undo for settings changes
- **Fix:** Add save confirmation or undo mechanism
- **Priority:** Low

### Defect 66: Settings export doesn't include KB data
- **Module:** Settings.tsx
- **Current:** `exportData` exports DB tables but not KB documents
- **Problem:** KB data not included in data export
- **Fix:** Include KB documents in export or link to vault backup
- **Priority:** Medium

## Authentication & Profile

### Defect 67: CompleteProfile page may not validate inputs
- **Module:** CompleteProfile.tsx
- **Current:** May accept empty name
- **Fix:** Add input validation
- **Priority:** Low

### Defect 68: Profile updates don't refresh sidebar
- **Module:** ProfileContext.tsx
- **Current:** Profile updates via API but sidebar may not reflect changes
- **Fix:** Ensure ProfileContext triggers re-render on update
- **Priority:** Medium

## Enrollment

### Defect 69: EnrollmentBadge doesn't show change option
- **Module:** EnrollmentBadge.tsx
- **Current:** Shows enrollment status but no way to change
- **Fix:** Add "Change enrollment" link to settings
- **Priority:** Low

## Curriculum

### Defect 70: CurriculumSection may not handle empty curriculum
- **Module:** CurriculumSection.tsx
- **Current:** May show empty section when no curriculum
- **Fix:** Add empty state with "Import syllabus" prompt
- **Priority:** Low

## Search

### Defect 71: Global search (Ctrl+K) has no recent searches
- **Module:** CommandPalette.tsx
- **Current:** Search starts fresh each time
- **Fix:** Show recent searches from localStorage
- **Priority:** Low

### Defect 72: Global search doesn't debounce input
- **Module:** CommandPalette.tsx
- **Current:** May fire API call on every keystroke
- **Fix:** Add 300ms debounce
- **Priority:** Medium

## PWA / Offline

### Defect 73: InstallBanner shows without checking PWA support
- **Module:** InstallBanner.tsx
- **Current:** May show install prompt on unsupported browsers
- **Fix:** Check `beforeinstallprompt` event availability
- **Priority:** Low

### Defect 74: No offline fallback for API calls
- **Module:** api.ts
- **Current:** `fetch()` throws on network error
- **Problem:** No offline queue or retry mechanism
- **Fix:** Add service worker caching for API responses
- **Priority:** Medium

### Defect 75: Service Worker registration not verified
- **Module:** main.tsx
- **Current:** PWA manifest may be present but SW not functional
- **Fix:** Verify SW registration and caching strategy
- **Priority:** Low
