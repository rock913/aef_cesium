#!/bin/bash
# AlphaEarth Cesium Frontend 启动脚本

set -e

# Supported usage:
#   ./run_frontend.sh [start|stop|restart|status|tail] [--daemon] [--print-config]
ACTION="start"
DAEMON=0
PRINT_CONFIG=0

for arg in "$@"; do
    case "$arg" in
        start|stop|restart|status|tail)
            ACTION="$arg"
            ;;
        --daemon)
            DAEMON=1
            ;;
        --print-config)
            PRINT_CONFIG=1
            ;;
        *)
            ;;
    esac
done

if [ "$PRINT_CONFIG" = "1" ]; then
    # (Handled later after env resolution)
    true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p logs
PID_FILE="$SCRIPT_DIR/logs/frontend.dev.pid"
LOG_FILE="$SCRIPT_DIR/logs/frontend.dev.log"

echo "🚀 Starting AlphaEarth Cesium Frontend..."

# Profile/config mode
ONEEARTH_PROFILE="${ONEEARTH_PROFILE:-v6}"
ENV_PATH=""
ENV_SOURCE_KIND="none"
if [ -n "${ENV_FILE:-}" ]; then
    ENV_PATH="$ENV_FILE"
    ENV_SOURCE_KIND="explicit"
elif [ -f ".env.${ONEEARTH_PROFILE}" ]; then
    ENV_PATH=".env.${ONEEARTH_PROFILE}"
    ENV_SOURCE_KIND="profile"
elif [ -f ".env" ]; then
    ENV_PATH=".env"
    ENV_SOURCE_KIND="fallback"
fi

# 加载环境文件（如果存在）
if [ -n "$ENV_PATH" ] && [ -f "$ENV_PATH" ]; then
    echo "📋 Loading environment from $ENV_PATH..."
    set -a
    # shellcheck disable=SC1090
    source "$ENV_PATH"
    set +a
fi

DEFAULT_FRONTEND_PORT="8504"
if [ "$ONEEARTH_PROFILE" = "v5" ]; then
    DEFAULT_FRONTEND_PORT="8502"
fi

FRONTEND_PORT="${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}"

# Guardrail: if we fell back to a generic .env while running v6, it's very easy
# to accidentally carry over v5 ports (8502) and then open :8504 in the browser,
# hitting some other reverse proxy/service that returns 502.
# Allow bypass via ONEEARTH_ALLOW_V5_PORTS_IN_V6=1.
if [ "$ONEEARTH_PROFILE" = "v6" ] && [ "$ENV_SOURCE_KIND" = "fallback" ] && [ "${ONEEARTH_ALLOW_V5_PORTS_IN_V6:-0}" != "1" ]; then
    if [ "$FRONTEND_PORT" = "8502" ]; then
        echo "⚠️  Detected FRONTEND_PORT=8502 from .env fallback (likely v5). Forcing v6 default FRONTEND_PORT=8504."
        FRONTEND_PORT="8504"
    fi
fi

# Run mode:
# - dev: vite dev server (serves /src/*)
# - preview: vite preview (serves /assets/* from dist; recommended for remote deployment)
FRONTEND_RUN_MODE="${FRONTEND_RUN_MODE:-dev}"

_port_in_use() {
    # Usage: _port_in_use 8504
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -ltn "sport = :${port}" 2>/dev/null | awk 'NR>1 {print}' | grep -q .
        return $?
    fi
    if command -v netstat >/dev/null 2>&1; then
        netstat -lnt 2>/dev/null | awk '{print $4}' | grep -q ":${port}$"
        return $?
    fi
    return 1
}

_print_port_owner() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        echo "--- ss -ltnp sport=:${port} ---"
        ss -ltnp "sport = :${port}" 2>/dev/null || true
    elif command -v netstat >/dev/null 2>&1; then
        echo "--- netstat -lntp | grep :${port} ---"
        netstat -lntp 2>/dev/null | grep ":${port} " || true
    fi
}

if [ "$ONEEARTH_PROFILE" = "v6" ] && [ "$FRONTEND_PORT" = "8502" ]; then
    echo "⚠️  ONEEARTH_PROFILE=v6 but FRONTEND_PORT=8502 (likely loaded v5 env)."
    echo "   Recommended: create .env.v6 with API_PORT=8505 and FRONTEND_PORT=8504"
fi

if [ "$PRINT_CONFIG" = "1" ]; then
    echo "ONEEARTH_PROFILE=$ONEEARTH_PROFILE"
    echo "ENV_PATH=${ENV_PATH:-<none>}"
    echo "ENV_SOURCE_KIND=$ENV_SOURCE_KIND"
    echo "FRONTEND_PORT=$FRONTEND_PORT"
    echo "FRONTEND_RUN_MODE=$FRONTEND_RUN_MODE"
    exit 0
fi

_pid_running() {
    local pid="$1"
    if [ -z "$pid" ]; then
        return 1
    fi
    if kill -0 "$pid" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

_read_pidfile() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE" 2>/dev/null | tr -d ' \t\n\r'
        return 0
    fi
    return 1
}

_stop_by_pidfile() {
    local pid
    pid="$(_read_pidfile || true)"
    if _pid_running "$pid"; then
        echo "🛑 Stopping frontend (pid=$pid)..."
        set +e
        kill "$pid" >/dev/null 2>&1
        for _ in $(seq 1 40); do
            if _pid_running "$pid"; then
                sleep 0.2
            else
                break
            fi
        done
        if _pid_running "$pid"; then
            echo "⚠️  Frontend still running, sending SIGKILL..."
            kill -9 "$pid" >/dev/null 2>&1
        fi
        set -e
        rm -f "$PID_FILE" >/dev/null 2>&1 || true
        echo "✅ Frontend stopped"
        return 0
    fi
    rm -f "$PID_FILE" >/dev/null 2>&1 || true
    echo "ℹ️  Frontend not running (no live pid in $PID_FILE)"
    return 0
}

_status() {
    local pid
    pid="$(_read_pidfile || true)"
    if _pid_running "$pid"; then
        echo "✅ Frontend running (pid=$pid) at http://0.0.0.0:${FRONTEND_PORT}"
        if command -v curl >/dev/null 2>&1; then
            code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${FRONTEND_PORT}/" 2>/dev/null || echo "000")
            echo "   / : HTTP $code"
        fi
        return 0
    fi

    # If the port is open, the frontend may be running but not started via this script.
    if _port_in_use "$FRONTEND_PORT"; then
        echo "⚠️  FRONTEND_PORT=${FRONTEND_PORT} is in use, but no live pid in $PID_FILE"
        echo "   (frontend may be started outside this script; stop/restart here won't affect it)"
        if command -v curl >/dev/null 2>&1; then
            code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${FRONTEND_PORT}/" 2>/dev/null || echo "000")
            echo "   / : HTTP $code"
            if [ "$code" = "200" ]; then
                return 0
            fi
        fi
        _print_port_owner "$FRONTEND_PORT"
        return 1
    fi

    echo "❌ Frontend not running"
    return 1
}

if [ "$ACTION" = "tail" ]; then
    echo "📄 Tailing $LOG_FILE"
    tail -n 200 -f "$LOG_FILE"
    exit 0
fi

if [ "$ACTION" = "status" ]; then
    _status
    exit $?
fi

if [ "$ACTION" = "stop" ]; then
    _stop_by_pidfile
    exit 0
fi

if [ "$ACTION" = "restart" ]; then
    _stop_by_pidfile
    ACTION="start"
fi

# 进入前端目录
cd frontend

# Fail fast if the port is already in use.
# A common real-world symptom is that an existing reverse proxy (e.g., nginx) is
# listening on 8504 and returning 502 because its upstream is misconfigured.
if _port_in_use "$FRONTEND_PORT"; then
    existing_pid="$(_read_pidfile || true)"
    if _pid_running "$existing_pid"; then
        echo "ℹ️  Frontend already running (pid=$existing_pid) on :${FRONTEND_PORT}"
        exit 0
    fi
    echo "❌ FRONTEND_PORT=${FRONTEND_PORT} is already in use."
    _print_port_owner "$FRONTEND_PORT"
    echo "💡 Fix options:"
    echo "   1) Stop the existing process using :${FRONTEND_PORT}"
    echo "   2) Or run with a different port: FRONTEND_PORT=8514 ONEEARTH_PROFILE=$ONEEARTH_PROFILE ./run_frontend.sh"
    echo "   3) If this is nginx, either stop it or configure it to serve frontend dist assets instead of proxying to a dead upstream"
    exit 1
fi

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# 启动前端
echo "✅ Frontend starting on http://0.0.0.0:${FRONTEND_PORT:-8504} (remote: http://47.245.113.151:${FRONTEND_PORT:-8504})"
if [ "$FRONTEND_RUN_MODE" = "preview" ]; then
    echo "🧱 FRONTEND_RUN_MODE=preview: building + serving dist (recommended for remote deployment)"
    npm run build
    if [ "$DAEMON" = "1" ]; then
        echo "🧷 Running frontend in background"
        echo "   Log: $LOG_FILE"
        nohup npm run preview -- --host 0.0.0.0 --port ${FRONTEND_PORT:-8504} --strictPort >"$LOG_FILE" 2>&1 &
        pid=$!
        echo "$pid" >"$PID_FILE"
    else
        exec npm run preview -- --host 0.0.0.0 --port ${FRONTEND_PORT:-8504} --strictPort
    fi
else
    echo "🧪 FRONTEND_RUN_MODE=dev: running Vite dev server (serves /src/*)"
    if [ "$DAEMON" = "1" ]; then
        echo "🧷 Running frontend in background"
        echo "   Log: $LOG_FILE"
        nohup npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT:-8504} --strictPort >"$LOG_FILE" 2>&1 &
        pid=$!
        echo "$pid" >"$PID_FILE"
    else
        exec npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT:-8504} --strictPort
    fi
fi

if [ "$DAEMON" = "1" ]; then
    # Wait for ready
    if command -v curl >/dev/null 2>&1; then
        for _ in $(seq 1 60); do
            code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${FRONTEND_PORT}/" 2>/dev/null || echo "000")
            if [ "$code" = "200" ]; then
                echo "✅ Frontend ready (pid=$(cat "$PID_FILE" 2>/dev/null || echo "?"))"
                exit 0
            fi
            sleep 0.25
        done
        echo "⚠️  Frontend did not become ready in time; last log lines:"
        tail -n 120 "$LOG_FILE" || true
    fi
    exit 0
fi
