# Security Notes — Cortex Productivity App

**Threat model: local-first, single-user desktop-style app.**
The backend is expected to run on the user's own machine (`localhost:8000`),
serving one owner. The security posture below is scoped to that deployment.
If the app is ever hosted on a network or cloud, revisit every item marked
"local-only" before doing so.

## Identity model (single owner)

- The app is **tokenless in production**: `app/services/users.py::current_user`
  resolves "the current user" as the first `users` row (the seeded owner).
  There are no roles or per-request auth in production by design.
- `app/routers/auth.py` is a **pytest-only shim** (signup/login/me/logout with
  bearer tokens) so the legacy test suite can exercise `user_id` scoping.
  It is mounted in `main.py` because the test suite imports the real app; it
  implements bcrypt password hashing and per-IP login throttling, but it is
  not a production auth path.
- Google OAuth (`auth_google.py` + `google_oauth.py`): the link between a
  `User` row and the `GoogleToken` row (single row, id=1) is **email match,
  not a foreign key**. Acceptable for the single-owner app; if multi-account
  support is added, introduce a `GoogleAccount.user_id` FK.

## Secrets at rest (local-only)

| Secret | Storage | Notes |
|---|---|---|
| Google OAuth refresh tokens | `google_tokens` SQLite table | DB file is the encryption boundary. Local-only assumption. |
| AI provider API keys | `backend/app/data/ai_providers.json` | Git-ignored (see `.gitignore`). Any process with filesystem read access can extract keys. |
| `APP_SECRET` / `TEACHER_SECRET_KEY` | `app/config.py` defaults | Test-only auth shim; safe dev defaults, never used for production auth. |

**Before any cloud/hosted deployment:** encrypt the token columns (e.g.
SQLCipher or app-level encryption with an OS keychain-held key) and move
provider API keys to the OS keychain or a secrets manager. Do not migrate
the SQLite file as-is.

## Path traversal defenses

All user-controlled paths are sanitized through a single utility:
`app/services/path_utils.py::safe_path` (strips directory components,
removes `..` segments, optionally anchors under a base directory).
Callers that build filesystem paths from `KbDocument.source`-like values
must use it — see `routers/kb_backup.py`, `services/kb/auto_sync.py`,
`services/kb/backup.py`. Upload endpoints additionally strip to a basename
(`Path(name).name`) and use UUID storage names on disk.

## Live test credentials

`backend/tests/test_kb_learning_sessions.py` can run opt-in live PortSwigger
login tests. Credentials are read from `PS_PORT_SWIGGER_EMAIL` /
`PS_PORT_SWIGGER_PASSWORD` env vars — never hardcoded, never committed.
No secrets are stored in this repository.
