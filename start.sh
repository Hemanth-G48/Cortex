#!/usr/bin/env bash
# ═════════════════════════════════════════════════════════════════════════════
# start.sh — one-command dev startup for Student Life OS
#
# Starts the FastAPI backend (uvicorn, :8000) and the Vite frontend (:5173),
# frees the ports if they're in use, waits for the backend health check, and
# shuts both down cleanly on Ctrl+C.
#
# Usage:
#   ./start.sh                  # default: dev mode (uvicorn --reload)
#   ./start.sh --no-reload      # backend without auto-reload
#   ./start.sh --install        # pip install + npm install first
#   ./start.sh --host 0.0.0.0   # override backend host (default 0.0.0.0)
#   ./start.sh --no-open        # don't auto-open the browser
# ═════════════════════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"

BACKEND_HOST="0.0.0.0"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
RELOAD=1
DO_INSTALL=0
OPEN_BROWSER=1
BACKEND_PID=""

# ── Local embeddings (fastembed/ONNX, offline — no PyTorch) ──
# EMBEDDINGS_DIM must match the local model (BAAI/bge-small-en-v1.5 = 384).
# Set EMBEDDINGS_BACKEND=provider to go back to the API /embeddings path.
# On NVIDIA GPUs, fastembed-gpu + onnxruntime-gpu run the model on CUDA
# automatically (embeddings.py preloads the venv-shipped CUDA libs).
export EMBEDDINGS_BACKEND="${EMBEDDINGS_BACKEND:-fastembed}"
export EMBEDDINGS_LOCAL_MODEL="${EMBEDDINGS_LOCAL_MODEL:-BAAI/bge-small-en-v1.5}"
export EMBEDDINGS_DIM="${EMBEDDINGS_DIM:-384}"
# Make the pip-shipped CUDA runtime libs resolvable for onnxruntime-gpu
# (belt-and-braces; embeddings.py preloads them via ctypes as the primary path).
NVIDIA_DIR="$BACKEND_DIR/.venv/lib/python3.12/site-packages/nvidia"
if [ -d "$NVIDIA_DIR" ]; then
  NV_LIBS="$(find "$NVIDIA_DIR" -type d -name lib 2>/dev/null | paste -sd:)"
  export LD_LIBRARY_PATH="$NV_LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

# ── Flag parsing ──
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-reload) RELOAD=0; shift ;;
    --install)   DO_INSTALL=1; shift ;;
    --no-open)   OPEN_BROWSER=0; shift ;;
    --host)      BACKEND_HOST="$2"; shift 2 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown option: $1 (see ./start.sh --help)" >&2; exit 1 ;;
  esac
done

# ── Cleanup: kill the backend (frontend exits with the terminal) ──
cleanup() {
  echo ""
  echo "🛑 Shutting down…"
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── Helpers ──
info()  { printf '  \033[1;36m%s\033[0m\n' "$*"; }
warn()  { printf '  \033[1;33m%s\033[0m\n' "$*"; }
ok()    { printf '  \033[1;32m%s\033[0m\n' "$*"; }
die()   { printf '  \033[1;31m%s\033[0m\n' "$*" >&2; exit 1; }

# Free a port if something is already listening on it.
free_port() {
  local port="$1"
  local pid
  pid=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    warn "Port $port in use (PID $pid) — freeing it…"
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
}

# ── Resolve the Python interpreter (prefer backend/.venv) ──
if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  PYTHON="$BACKEND_DIR/.venv/bin/python"
  info "Using backend/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
  warn "No backend/.venv found — using system $PYTHON"
fi

# ── Optional dependency install ──
if [ "$DO_INSTALL" -eq 1 ]; then
  info "Installing backend dependencies…"
  (cd "$BACKEND_DIR" && "$PYTHON" -m pip install -r requirements.txt)
  info "Installing frontend dependencies…"
  (cd "$FRONTEND_DIR" && npm install)
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  warn "node_modules missing — run './start.sh --install' or 'cd frontend && npm install'"
fi

echo ""
echo "🚀 Starting Student Life OS"
echo "────────────────────────────────────────────────────────"

# ── Backend ──
info "Starting backend (uvicorn) on :$BACKEND_PORT"
free_port "$BACKEND_PORT"
cd "$BACKEND_DIR"
if [ "$RELOAD" -eq 1 ]; then
  "$PYTHON" -m uvicorn main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
else
  "$PYTHON" -m uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
fi
BACKEND_PID=$!

# ── Wait for the backend to be healthy ──
info "Waiting for backend health check…"
HEALTH_OK=0
for _ in $(seq 1 30); do
  if curl -fsS "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
    HEALTH_OK=1
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    die "Backend exited before becoming healthy — check the log above."
  fi
  sleep 1
done
[ "$HEALTH_OK" -eq 1 ] || die "Backend did not become healthy within 30s."

# ── Frontend ──
info "Starting frontend (Vite) on :$FRONTEND_PORT"
free_port "$FRONTEND_PORT"
cd "$FRONTEND_DIR"

if [ "$OPEN_BROWSER" -eq 1 ]; then
  (
    sleep 3
    xdg-open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 ||
      open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || true
  ) &
fi

ok "✓ Backend  → http://localhost:$BACKEND_PORT  (API: /api/health)"
ok "✓ Frontend → http://localhost:$FRONTEND_PORT"
echo ""
info "Press Ctrl+C to stop both servers."
echo ""

npm run dev
