# Architecture notes — UX-safety pass (September 2026)

Structure established by the confirm-policy consolidation. Later passes should build with it, not against it.

## Destructive-action confirm policy — one owner

`frontend/src/utils/confirm.ts` exports `confirmDelete(what: string): boolean`.

- Every delete flow gates on `confirmDelete('<noun phrase>')` — e.g. `confirmDelete('this task')`, `confirmDelete('this deck and all its cards')`.
- Message phrasing ("Delete X? This cannot be undone.") is owned by the helper, not call sites. To change the wording or swap `window.confirm` for a styled dialog later, change exactly one file.
- **Not** routed through the helper: confirmations with bespoke, non-delete explanations (KnowledgeBase reindex / merge / restore). Those are one-off policies with unique context, kept inline deliberately. Don't force them into the template.

## Seed data ownership

`backend/app/seed/__init__.py`:

- **Freshness is decided once**: `fresh = user is None` at the top of `seed_database`; both `seed_vault_habits` and `seed_vault_demo` run inside a single `if fresh:` block. User deletions are never resurrected on restart.
- **LifeArea has exactly one seeder**: `seed_rpg_additions` (the richer set with progress/target_days/status). `seed_full` no longer adds its own satisfaction-only areas — the two-seeder overlap used to be masked by a `db.query(LifeArea).delete()`, which also wiped user modifications.
- General rule: when two seeders can create the same entity, delete the weaker one; gate the survivor on emptiness, never delete-then-reseed.

## Presentation affordance

Click affordance lives on the element that navigates (the `<Link>`), not the wrapper div. Dashboard course cards no longer carry a misleading `cursor: pointer` on a non-interactive container.

## Verification status at time of writing

- Frontend: `tsc --noEmit` clean; vitest 164/164 (incl. `utils/confirm.test.ts`).
- Backend: pytest 1621 passed, 5 skipped.
- Real run: backend `main:app` (note: entrypoint is `backend/main.py`, not `app.main` — README is stale on this) + Vite dev server; life-areas endpoint returns exactly the canonical 4; task create/delete roundtrip 200.
