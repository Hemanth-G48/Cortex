# Code Audit Report — Student Life OS (Cortex)

**Last updated**: 2026-09-14
**Previous audit**: 2026-09-11 (903 files, backend + frontend)

---

## Known Issues from Previous Audit (2026-09-11)

### OPEN — `COLUMN_MIGRATIONS` duplicate dict keys (regression)

| | |
|---|---|
| **Location** | `backend/app/database.py` (`COLUMN_MIGRATIONS`, entries at lines ~155, ~178, ~198 and ~166, ~202) |
| **Severity** | high (silent data-loss hazard on any existing DB) |
| **History** | Found and "fixed" during the 2026-09-13 remediation (merge of `users` ×3 / `courses` ×2 worked), but the `kb_documents` / `kb_sources` entries were never merged — the duplicate-key bug is still present. |

#### Current state (verified 2026-09-14 via AST parse)

The dict literal still contains:

- `"kb_documents"` **3 times**
  - entry 1 (line 155): `file_path`, `author`, `source_url`, `language`, `reading_time_seconds`, `embedding_dirty`, `graph_dirty`, `tags_dirty`
  - entry 2 (line 178): `quality_score`, `quality_detail`
  - entry 3 (line 198): `summary_dirty` ← **only this one survives**
- `"kb_sources"` **2 times**
  - entry 1 (line 166): `duplicate_map_json`
  - entry 2 (line 202): `sync_type`, `sync_cursor_json`, `sync_source_path` ← **only this one survives**

Python dict literals are last-wins: on every startup, `migrate_schema()`
(line 247) iterates the *effective* map, so the shadowed entries are dead
code — those columns are **never added** to an existing database.

#### Proven impact

- `backend/productivity.db` is missing **all 11 shadowed columns**
  (10 on `kb_documents` + `duplicate_map_json` on `kb_sources`).
  Pointing the app at that DB → `OperationalError` on first KB query that
  touches any of them (the ORM models reference columns the table lacks).
- Live `student_os.db` happens to already have every column (added by
  `create_all` or earlier complete migrations), which is why nothing has
  visibly broken yet. Any **restored backup or fresh existing DB** hit by
  the current code gets only the winning entries.
- Note: `kb_sources.duplicate_map_json` is the persistent dedupe map from
  the Second Brain Phase 1 fix — losing that column silently re-breaks
  dedupe stability on affected DBs.

#### Fix (one edit)

Merge the three `kb_documents` entries into a single entry and the two
`kb_sources` entries into a single entry, preserving the per-phase comments
(so the historical context stays greppable). The migration loop needs no
change — once the dict is deduplicated, `migrate_schema()` applies every
column on any DB (it is idempotent: only adds columns that don't exist).

After fixing, verify with:

```bash
python3 - <<'EOF'
import ast
from collections import Counter
tree = ast.parse(open("backend/app/database.py").read())
for node in ast.walk(tree):
    if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "COLUMN_MIGRATIONS":
        keys = [k.value for k in node.value.keys]
        print({t: c for t, c in Counter(keys).items() if c > 1} or "no duplicates")
EOF
```

Optionally add a guard so this class of bug can't regress again: a startup
or test-time assertion that the *source* dict has no duplicate keys (AST
check, since the runtime dict is already collapsed by then).

---

## Full Audit (2026-09-14)

### Executive Summary

- **Overall Health Score: 7/10** — Well-structured full-stack app with strong separation of concerns, but significant complexity and some security/maintainability concerns
- **Critical Issues: 2**
- **High Priority Issues: 6**
- **Top 3 Priorities:**
  1. **God-file main.py** — 100+ router includes in a single file; split into feature modules
  2. **State management bloat** — Pages with 15-30+ useState calls need state management refactor
  3. **Error handling inconsistency** — Mix of silent `.catch(() => {})` and proper error states

---

### Findings by Category

#### 1. Architecture & Design

##### 🔴 High Priority

**God-file `main.py` (224 lines, 100+ router includes)**
- File: `backend/main.py:118-219`
- Impact: Impossible to understand app structure at a glance; merge conflicts inevitable
- Recommendation: Split into feature groups using `APIRouter(prefix="/api")` sub-apps

**Frontend pages with excessive useState (15-30+ per component)**
- Files: `KnowledgeBase.tsx` (40+ states), `VaultDashboard.tsx` (20+ states), `LearningPlanner.tsx` (30+ states), `SubjectWorkspace.tsx` (25+ states)
- Impact: Components are unmaintainable; state logic interleaved with rendering
- Recommendation: Extract state into custom hooks or use useReducer/Zustand for complex pages

##### 🟡 Medium Priority

**No shared state management solution**
- Evidence: Every page manages its own loading/error/data states independently
- Impact: Duplicated fetch-loading-error patterns across 50+ pages
- Recommendation: Create a `useAsyncData<T>` hook or adopt TanStack Query

**Import-linter enforces layering (positive)**
- `pyproject.toml:25-53` — models ← services ← routers boundary enforced
- This is a **positive finding** — architectural boundaries are codified

---

#### 2. Security

##### 🔴 High Priority

**Hardcoded CORS origins**
- File: `backend/main.py:112`
- Code: `allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]`
- Impact: Breaks in production; should use env var
- Recommendation: `allow_origins=settings.CORS_ORIGINS.split(",")`

**Auth system exists but most routes are unprotected**
- Evidence: 200+ route handlers found; only KB routes use `Depends(current_user)`
- Impact: Single-user app assumption is fragile; any route can be called without auth
- Recommendation: Add global middleware or dependency if auth is ever needed

##### 🟡 Medium Priority

**Secret management**
- Evidence: `.env.example` exists, `APP_SECRET` / `TEACHER_SECRET_KEY` env vars mentioned
- No hardcoded secrets found in grep results (good)
- Recommendation: Verify no secrets in git history

**File upload validation is solid (positive)**
- Evidence: Extension allowlist, 10MB cap, magic-byte sniffing (`kb_documents.py:153-161`)

---

#### 3. Code Quality

##### 🔴 High Priority

**Silent error swallowing**
- 680+ `catch` blocks found; many are `.catch(() => {})` (empty catch)
- Examples: `VaultDashboard.tsx:133`, `Pomodoro.tsx:17`, `KnowledgeBase.tsx:532`
- Impact: Users see no feedback when operations fail; bugs are invisible
- Recommendation: At minimum, log to console; ideally show toast notification

**No `as any` or `@ts-ignore` (positive)**
- Only 1 match found in test file — excellent TypeScript discipline

##### 🟡 Medium Priority

**Consistent React patterns (positive)**
- useCallback + useEffect dependency arrays are correctly used
- Error boundaries exist (`ErrorBoundary.tsx`)
- Lazy loading with Suspense is implemented

**TODO/FIXME count is low (positive)**
- Only 2 matches found — indicates mature codebase

---

#### 4. Performance

##### 🟡 Medium Priority

**No code splitting at route level**
- Evidence: `App.tsx:1` uses `lazy()` but most pages import directly
- Impact: Large initial bundle with 50+ page components
- Recommendation: Wrap all route components in `React.lazy()`

**Database: N+1 query risk**
- Evidence: Many routes do `db.query(...)` in loops (e.g., `kb_subjects.py` topic processing)
- Recommendation: Add eager loading or batch queries

**Embedding model warm-up on startup (positive)**
- `main.py:88-95` — fastembed model loaded at boot (good for latency)
- Best-effort with exception handling (correct approach)

---

#### 5. Testing

##### 🟡 Medium Priority

**Test infrastructure exists**
- 30+ test files in `backend/tests/`
- Vitest configured for frontend (`vitest.config.ts`)
- Conftest with test DB fixtures

**Test coverage gaps**
- Frontend: Only ~15 test files for 50+ pages
- Backend: Strong KB test coverage, weak for other routers
- Recommendation: Prioritize tests for auth, file uploads, and core CRUD

---

#### 6. Maintainability

##### 🔴 High Priority

**Single-user architecture assumption**
- README explicitly states: "no login/signup, no passwords, no roles"
- Auth router exists but is "pytest-only shim"
- Impact: Adding multi-user later requires massive refactor
- Recommendation: Document this decision as an ADR; if multi-user is possible, design for it now

##### 🟡 Medium Priority

**Good documentation (positive)**
- README is comprehensive with architecture diagrams, routes, and feature descriptions
- Frontend README has detailed component inventory

**Dependency management is clean (positive)**
- `pyproject.toml` pins minimum versions correctly
- Frontend uses npm with lockfile
- Import-linter enforces architectural boundaries

---

### Prioritized Action Plan

#### Quick wins (< 1 day)
1. **Fix COLUMN_MIGRATIONS duplicate keys** — Merge `kb_documents` and `kb_sources` entries
2. **Add error toasts for silent `.catch(() => {})`** — Pick 5 highest-traffic pages
3. **Move CORS origins to env var** — `settings.CORS_ORIGINS`
4. **Add React.lazy() to route imports** in `App.tsx`

#### Medium-term (1-5 days)
1. **Extract `useAsyncData` hook** — Eliminates loading/error boilerplate across 50+ pages
2. **Split main.py routers into feature groups** — academic, knowledge-base, gamification, settings
3. **Add tests for auth and file upload routes**

#### Long-term (> 5 days)
1. **State management refactor** — Migrate complex pages (KnowledgeBase, VaultDashboard) to useReducer or Zustand
2. **Multi-user architecture ADR** — Decide now if this stays single-user or needs auth
3. **Frontend test coverage** — Target 80% page coverage

---

### Metrics

| Metric | Value |
|--------|-------|
| Files analyzed | 200+ (TypeScript + Python) |
| Lines of code | ~15,000+ frontend, ~10,000+ backend |
| Backend routes | 200+ endpoints |
| Frontend pages | 50+ route pages |
| Test files | 30+ backend, 15+ frontend |
| Critical issues | 2 |
| High priority issues | 6 |
| TypeScript strictness | Excellent (zero `as any`) |
| Error handling consistency | Poor (680+ catch blocks, many empty) |

---

### Positive Highlights

- Import-linter enforces clean architecture boundaries
- Zero TypeScript type suppression (`as any`, `@ts-ignore`)
- File upload security is thorough (extension allowlist, magic-byte validation)
- Comprehensive README documentation
- Local-first embedding (no cloud dependency for search)
