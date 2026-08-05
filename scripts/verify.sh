#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# verify.sh — one-command local CI-style check (all plans: STUDENT-PLANAR
# Phase 94, SyllabusAI Phase 96, Zenith / Shiori / Vault verification).
#
# Runs, in order: backend pytest → frontend tsc -b → vitest → production build
# → oxlint. Exits non-zero (1) if any gate fails so it is safe to use in
# pre-commit hooks or CI pipelines.
#
# Usage:
#   ./scripts/verify.sh                    # full check
#   VERIFY_SKIP_BUILD=1 ./scripts/verify.sh   # skip the (slow) vite build
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAIL=0

gate() {
  local name="$1" dir="$2"
  shift 2
  echo ""
  echo "▶ [$name] $*"
  if ! (cd "$ROOT/$dir" && "$@"); then
    echo "❌ [$name] failed"
    FAIL=1
  fi
}

echo "🛠  verify.sh — Student Life OS full check (pytest · tsc · vitest · build · oxlint)"
echo ""

gate "backend:pytest"    backend  python -m pytest -q
gate "frontend:tsc"      frontend npx tsc -b
gate "frontend:vitest"   frontend npx vitest run
if [ "${VERIFY_SKIP_BUILD:-0}" != "1" ]; then
  gate "frontend:build"  frontend npm run build
fi
gate "frontend:oxlint"   frontend npm run lint

echo ""
if [ "$FAIL" -ne 0 ]; then
  echo "❌ verify.sh — one or more gates failed."
  exit 1
fi
echo "✅ verify.sh — all gates passed."
