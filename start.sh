#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── Free up ports if already in use ──
kill_port() {
  local pid
  pid=$(lsof -ti :"$1" 2>/dev/null) && kill "$pid" 2>/dev/null && echo "  Freed port $1 (PID $pid)" || true
}

echo "🔍 Checking ports…"
kill_port 8000
kill_port 5173

# ── Backend ──
echo "📍 Starting backend (uvicorn) on port 8000…"
cd "$ROOT/backend"
python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!

# ── Frontend ──
echo "📍 Starting frontend (Vite) on port 5173…"
cd "$ROOT/frontend"
npm run dev
