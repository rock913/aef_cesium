#!/bin/bash
# OneEarth v6 one-click deploy (nohup)
#
# This script orchestrates running both backend and frontend in background
# by delegating to run_backend.sh / run_frontend.sh with --daemon.
#
# Usage:
#   ./deploy_nohup.sh start|stop|restart|status|tail [--profile v6] [--env-file .env.v6]
#
# Common production defaults:
#   FRONTEND_RUN_MODE=preview ONEEARTH_PROFILE=v6 ./deploy_nohup.sh start

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ACTION="${1:-start}"
shift || true

PROFILE_OVERRIDE=""
ENV_FILE_OVERRIDE=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --profile)
      PROFILE_OVERRIDE="${2:-}"
      shift 2
      ;;
    --env-file)
      ENV_FILE_OVERRIDE="${2:-}"
      shift 2
      ;;
    -h|--help)
      ACTION="help"
      shift
      ;;
    *)
      # ignore unknown flags for forward compatibility
      shift
      ;;
  esac
done

ONEEARTH_PROFILE="${PROFILE_OVERRIDE:-${ONEEARTH_PROFILE:-v6}}"
ENV_FILE="${ENV_FILE_OVERRIDE:-${ENV_FILE:-}}"

BACKEND_LOG="logs/backend.dev.log"
FRONTEND_LOG="logs/frontend.dev.log"

_print_urls() {
  local backend_cfg frontend_cfg api_host api_port frontend_port

  backend_cfg=$(ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_backend.sh --print-config)
  frontend_cfg=$(ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_frontend.sh --print-config)

  api_host=$(echo "$backend_cfg" | awk -F= '/^API_HOST=/{print $2}' | tail -n 1)
  api_port=$(echo "$backend_cfg" | awk -F= '/^API_PORT=/{print $2}' | tail -n 1)
  frontend_port=$(echo "$frontend_cfg" | awk -F= '/^FRONTEND_PORT=/{print $2}' | tail -n 1)

  echo "🌐 Frontend: http://127.0.0.1:${frontend_port}"
  echo "📘 Backend docs: http://${api_host}:${api_port}/docs"
}

_usage() {
  cat <<'EOF'
OneEarth one-click deploy (nohup)

Usage:
  ./deploy_nohup.sh start|stop|restart|status|tail [--profile v6] [--env-file .env.v6]

Notes:
  - Uses run_backend.sh / run_frontend.sh with --daemon (nohup).
  - Logs:
      logs/backend.dev.log
      logs/frontend.dev.log
  - PID files:
      logs/backend.dev.pid
      logs/frontend.dev.pid

Examples:
  FRONTEND_RUN_MODE=preview ./deploy_nohup.sh start
  ./deploy_nohup.sh status
  ./deploy_nohup.sh tail
  ./deploy_nohup.sh stop
EOF
}

case "$ACTION" in
  help|-h|--help)
    _usage
    exit 0
    ;;
  start)
    mkdir -p logs
    echo "🚀 Deploy (nohup) profile=$ONEEARTH_PROFILE"
    if [ -n "${ENV_FILE:-}" ]; then
      echo "📋 ENV_FILE=$ENV_FILE"
    fi
    echo "💡 Tip: For remote deployment, set FRONTEND_RUN_MODE=preview"
    echo

    echo "📡 Starting backend..."
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_backend.sh start --daemon

    echo
    echo "🎨 Starting frontend..."
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_frontend.sh start --daemon

    echo
    echo "✅ Started."
    _print_urls
    echo
    echo "📝 Logs:"
    echo "  Backend : $BACKEND_LOG"
    echo "  Frontend: $FRONTEND_LOG"
    echo "🔎 Tail: ./deploy_nohup.sh tail"
    ;;
  stop)
    echo "🛑 Stopping frontend..."
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_frontend.sh stop
    echo "🛑 Stopping backend..."
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_backend.sh stop
    echo "✅ Stopped."
    ;;
  restart)
    echo "🔁 Restarting..."
    echo
    echo "🛑 Stopping frontend..."
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_frontend.sh stop
    echo "🛑 Stopping backend..."
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_backend.sh stop
    echo
    echo "📡 Starting backend..."
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_backend.sh start --daemon
    echo
    echo "🎨 Starting frontend..."
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_frontend.sh start --daemon
    echo
    echo "✅ Restarted."
    _print_urls
    ;;
  status)
    echo "📋 Backend status:"
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_backend.sh status || true
    echo
    echo "📋 Frontend status:"
    ONEEARTH_PROFILE="$ONEEARTH_PROFILE" ENV_FILE="$ENV_FILE" bash ./run_frontend.sh status || true
    echo
    _print_urls
    ;;
  tail)
    mkdir -p logs
    echo "📄 Tailing logs (Ctrl+C to stop)"
    echo "  - $BACKEND_LOG"
    echo "  - $FRONTEND_LOG"
    touch "$BACKEND_LOG" "$FRONTEND_LOG"
    tail -n 200 -f "$BACKEND_LOG" "$FRONTEND_LOG"
    ;;
  *)
    echo "❌ Unknown action: $ACTION"
    echo
    _usage
    exit 2
    ;;
esac
