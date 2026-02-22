#!/bin/bash
# Production single-process launcher:
# - Builds frontend into frontend/dist
# - Serves frontend/dist + /api from ONE uvicorn process on :8504
# This eliminates the "frontend upstream missing" class of 502s.

set -euo pipefail

PRINT_CONFIG=0
if [ "${1:-}" = "--print-config" ]; then
  PRINT_CONFIG=1
  shift || true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ONEEARTH_PROFILE="${ONEEARTH_PROFILE:-v6}"

# Load env file similarly to run_* scripts
ENV_PATH=""
if [ -n "${ENV_FILE:-}" ]; then
  ENV_PATH="$ENV_FILE"
elif [ -f ".env.${ONEEARTH_PROFILE}" ]; then
  ENV_PATH=".env.${ONEEARTH_PROFILE}"
elif [ -f ".env" ]; then
  ENV_PATH=".env"
fi

if [ -n "$ENV_PATH" ] && [ -f "$ENV_PATH" ]; then
  echo "📋 Loading environment from $ENV_PATH..."
  set -a
  # shellcheck disable=SC1090
  source "$ENV_PATH"
  set +a
fi

# Bind port (frontend+api)
FRONTEND_PORT="${FRONTEND_PORT:-8504}"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="$FRONTEND_PORT"

# Uvicorn worker count (default 1: lower memory footprint)
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"

# Make FastAPI serve built dist
export SERVE_FRONTEND_DIST=1
export FRONTEND_DIST_DIR="${FRONTEND_DIST_DIR:-$SCRIPT_DIR/frontend/dist}"

if [ "$PRINT_CONFIG" = "1" ]; then
  echo "ONEEARTH_PROFILE=$ONEEARTH_PROFILE"
  echo "ENV_PATH=${ENV_PATH:-<none>}"
  echo "API_HOST=$API_HOST"
  echo "API_PORT=$API_PORT"
  echo "FRONTEND_DIST_DIR=$FRONTEND_DIST_DIR"
  echo "UVICORN_WORKERS=$UVICORN_WORKERS"
  exit 0
fi

echo "🧱 Building frontend (Vite)..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run build

echo "🐍 Starting backend+frontend on http://${API_HOST}:${API_PORT}"
cd "$SCRIPT_DIR"

# Reuse existing backend launcher to ensure venv + deps + GEE auth handling are consistent.
# We force API_PORT to FRONTEND_PORT for single-process mode.
export API_PORT="$API_PORT"
export API_HOST="$API_HOST"

# Note: run_backend.sh ends with `python -m uvicorn ...`.
# We need to pass workers; easiest is to invoke uvicorn directly after ensuring deps are installed.
# So we call run_backend.sh up to dependency installation by reusing its venv, then exec uvicorn.

# Ensure backend venv exists and deps installed.
# (This is a light re-implementation of the env selection + venv bootstrap from run_backend.sh)
PYTHON_BIN=""
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "❌ Python not found"
  exit 1
fi

if [ ! -d "$SCRIPT_DIR/backend/venv" ]; then
  echo "📦 Creating backend virtual environment..."
  "$PYTHON_BIN" -m venv "$SCRIPT_DIR/backend/venv"
fi

# shellcheck disable=SC1091
source "$SCRIPT_DIR/backend/venv/bin/activate"

python -m pip install --upgrade pip -q
pip install --no-cache-dir -q -r "$SCRIPT_DIR/backend/requirements.txt"

cd "$SCRIPT_DIR/backend"
exec python -m uvicorn main:app --host "$API_HOST" --port "$API_PORT" --workers "$UVICORN_WORKERS"
