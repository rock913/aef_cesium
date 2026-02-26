#!/bin/bash
# AlphaEarth Cesium Backend 启动脚本

set -e

# Supported usage:
#   ./run_backend.sh [start|stop|restart|status|tail] [--daemon] [--print-config]
#   ./run_backend.sh start --ch5-rf-reset-default --ch5-rf-yes
ACTION="start"
DAEMON=0
PRINT_CONFIG=0
CH5_RF_RESET_DEFAULT=0
CH5_RF_RESET_YES=0

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
        --ch5-rf-reset-default)
            # Destructive: delete the *default* derived CH5 RF asset id and submit a fresh export task.
            CH5_RF_RESET_DEFAULT=1
            ;;
        --ch5-rf-yes)
            # Confirm destructive CH5 RF operations.
            CH5_RF_RESET_YES=1
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
PID_FILE="$SCRIPT_DIR/logs/backend.dev.pid"
LOG_FILE="$SCRIPT_DIR/logs/backend.dev.log"

echo "🚀 Starting AlphaEarth Cesium Backend..."

# Profile/config mode
# - Default profile is v6 (ports 8504/8505) to avoid conflict with v5
# - Prefer loading .env.<profile> if present (e.g. .env.v6)
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

# Select Python interpreter used to (re)create the venv when needed.
# NOTE: On some systems /usr/bin/python3 may be 3.6, while a newer python exists.
PYTHON_BIN=""
if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.11)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "❌ Python not found"
    exit 1
fi

# Prefer a single workspace venv to avoid "two-venv" drift (backend/venv vs .venv).
VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"

echo "🐍 Bootstrap Python: $($PYTHON_BIN -V) ($PYTHON_BIN)"

# 加载环境文件（如果存在）
if [ -n "$ENV_PATH" ] && [ -f "$ENV_PATH" ]; then
    echo "📋 Loading environment from $ENV_PATH..."
    set -a
    # shellcheck disable=SC1090
    source "$ENV_PATH"
    set +a
else
    echo "⚠️  No env file found (looked for .env.${ONEEARTH_PROFILE} or .env), using defaults"
    echo "💡 Tip: Copy .env.example to .env.v6 (recommended) or .env and configure it"
fi

# Resolve defaults by profile
DEFAULT_API_HOST="127.0.0.1"
DEFAULT_API_PORT="8505"
if [ "$ONEEARTH_PROFILE" = "v5" ]; then
    DEFAULT_API_PORT="8503"
fi

API_HOST="${API_HOST:-$DEFAULT_API_HOST}"
API_PORT="${API_PORT:-$DEFAULT_API_PORT}"

# Guardrail: if we fell back to a generic .env while running v6, it's very easy
# to accidentally carry over v5 ports (8503) and then start frontend expecting 8505.
# Allow bypass via ONEEARTH_ALLOW_V5_PORTS_IN_V6=1.
if [ "$ONEEARTH_PROFILE" = "v6" ] && [ "$ENV_SOURCE_KIND" = "fallback" ] && [ "${ONEEARTH_ALLOW_V5_PORTS_IN_V6:-0}" != "1" ]; then
    if [ "$API_PORT" = "8503" ]; then
        echo "⚠️  Detected API_PORT=8503 from .env fallback (likely v5). Forcing v6 default API_PORT=8505."
        API_PORT="8505"
    fi
fi

_port_in_use() {
    # Usage: _port_in_use 8505
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

if [ "$ONEEARTH_PROFILE" = "v6" ] && [ "$API_PORT" = "8503" ]; then
    echo "⚠️  ONEEARTH_PROFILE=v6 but API_PORT=8503 (likely loaded v5 env)."
    echo "   Recommended: create .env.v6 with API_PORT=8505 and FRONTEND_PORT=8504"
fi

if [ "$PRINT_CONFIG" = "1" ]; then
    echo "ONEEARTH_PROFILE=$ONEEARTH_PROFILE"
    echo "ENV_PATH=${ENV_PATH:-<none>}"
    echo "ENV_SOURCE_KIND=$ENV_SOURCE_KIND"
    echo "API_HOST=$API_HOST"
    echo "API_PORT=$API_PORT"
    echo "CH5_RF_BOOTSTRAP=${CH5_RF_BOOTSTRAP:-<unset>}"
    echo "CH5_RF_AUTO_EXPORT=${CH5_RF_AUTO_EXPORT:-<unset>}"
    echo "CH5_ALIGN_BOOTSTRAP=${CH5_ALIGN_BOOTSTRAP:-<unset>}"
    echo "CH5_INLAND_CLASS_ID=${CH5_INLAND_CLASS_ID:-<unset>}"
    echo "CH5_DEEP_SEA_CLASS_ID=${CH5_DEEP_SEA_CLASS_ID:-<unset>}"
    echo "CH5_PALETTE=${CH5_PALETTE:-<unset>}"
    echo "CH5_RF_RESET_DEFAULT=$CH5_RF_RESET_DEFAULT"
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
        echo "🛑 Stopping backend (pid=$pid)..."
        set +e
        kill "$pid" >/dev/null 2>&1
        for _ in $(seq 1 30); do
            if _pid_running "$pid"; then
                sleep 0.2
            else
                break
            fi
        done
        if _pid_running "$pid"; then
            echo "⚠️  Backend still running, sending SIGKILL..."
            kill -9 "$pid" >/dev/null 2>&1
        fi
        set -e
        rm -f "$PID_FILE" >/dev/null 2>&1 || true
        echo "✅ Backend stopped"
        return 0
    fi
    rm -f "$PID_FILE" >/dev/null 2>&1 || true
    echo "ℹ️  Backend not running (no live pid in $PID_FILE)"
    return 0
}

_status() {
    local pid
    pid="$(_read_pidfile || true)"
    if _pid_running "$pid"; then
        echo "✅ Backend running (pid=$pid) at http://${API_HOST}:${API_PORT}"
        if command -v curl >/dev/null 2>&1; then
            code=$(curl -s -o /dev/null -w "%{http_code}" "http://${API_HOST}:${API_PORT}/health" 2>/dev/null || echo "000")
            echo "   /health: HTTP $code"
        fi
        return 0
    fi

    # If the port is open, the backend may be running but not started via this script.
    if _port_in_use "$API_PORT"; then
        echo "⚠️  API_PORT=${API_PORT} is in use, but no live pid in $PID_FILE"
        echo "   (backend may be started outside this script; stop/restart here won't affect it)"
        if command -v curl >/dev/null 2>&1; then
            code=$(curl -s -o /dev/null -w "%{http_code}" "http://${API_HOST}:${API_PORT}/health" 2>/dev/null || echo "000")
            echo "   /health: HTTP $code"
            if [ "$code" = "200" ]; then
                return 0
            fi
        fi
        _print_port_owner "$API_PORT"
        return 1
    fi

    echo "❌ Backend not running"
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

# Fail fast if the port is already in use.
# This avoids uvicorn failing to bind while a reverse proxy keeps returning 502.
if _port_in_use "$API_PORT"; then
    # If we believe we're already running, treat as OK.
    existing_pid="$(_read_pidfile || true)"
    if _pid_running "$existing_pid"; then
        echo "ℹ️  Backend already running (pid=$existing_pid) on :${API_PORT}"
        exit 0
    fi
    echo "❌ API_PORT=${API_PORT} is already in use."
    _print_port_owner "$API_PORT"
    echo "💡 Fix options:"
    echo "   1) Stop the existing process using :${API_PORT}"
    echo "   2) Or run with a different port: API_PORT=8515 ONEEARTH_PROFILE=$ONEEARTH_PROFILE ./run_backend.sh"
    exit 1
fi

# Ensure the workspace venv exists and matches this repo path.
if [ -d "$VENV_DIR" ] && [ -x "$VENV_DIR/bin/python" ]; then
    EXPECTED_VENV="$VENV_DIR"
    ACTIVATE_FILE="$VENV_DIR/bin/activate"
    VENV_REMOVED=0
    if [ -f "$ACTIVATE_FILE" ]; then
        ACTUAL_VENV=$(grep -E '^VIRTUAL_ENV=' "$ACTIVATE_FILE" 2>/dev/null | head -n 1 | cut -d= -f2-)
        # Strip optional surrounding quotes.
        ACTUAL_VENV="${ACTUAL_VENV%\"}"
        ACTUAL_VENV="${ACTUAL_VENV#\"}"
        ACTUAL_VENV="${ACTUAL_VENV%\'}"
        ACTUAL_VENV="${ACTUAL_VENV#\'}"
        if [ -n "$ACTUAL_VENV" ] && [ "$ACTUAL_VENV" != "$EXPECTED_VENV" ]; then
            echo "♻️  Recreating venv (path mismatch)"
            echo "   expected: $EXPECTED_VENV"
            echo "   found:    $ACTUAL_VENV"
            rm -rf "$VENV_DIR"
            VENV_REMOVED=1
        fi
    fi

    if [ "$VENV_REMOVED" = "0" ]; then
        VENV_VER_RAW=$($VENV_DIR/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
        VENV_MAJOR=$(echo "$VENV_VER_RAW" | cut -d. -f1)
        VENV_MINOR=$(echo "$VENV_VER_RAW" | cut -d. -f2)
        if [ "$VENV_MAJOR" -lt 3 ] || [ "$VENV_MINOR" -lt 9 ]; then
            echo "♻️  Recreating venv (found Python $VENV_VER_RAW, need >= 3.9)"
            rm -rf "$VENV_DIR"
        fi
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment at $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# Activate venv
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "🐍 Runtime Python: $(python -V) ($(python -c 'import sys; print(sys.executable)'))"

# 升级 pip 并安装依赖（使用国内镜像源加速）
# To make restarts fast, only reinstall when requirements.txt changes.
REQ_SHA=$(python -c 'import hashlib, pathlib; p=pathlib.Path("backend/requirements.txt"); print(hashlib.sha256(p.read_bytes()).hexdigest())' 2>/dev/null || echo "")
REQ_STAMP_FILE="$VENV_DIR/.requirements.sha256"
NEED_INSTALL=0

if [ "${FORCE_PIP_INSTALL:-0}" = "1" ]; then
    NEED_INSTALL=1
elif [ ! -f "$REQ_STAMP_FILE" ]; then
    NEED_INSTALL=1
elif [ -n "$REQ_SHA" ] && [ "$(cat "$REQ_STAMP_FILE" 2>/dev/null || true)" != "$REQ_SHA" ]; then
    NEED_INSTALL=1
elif [ -z "$REQ_SHA" ]; then
    NEED_INSTALL=1
fi

if [ "$NEED_INSTALL" = "1" ]; then
    echo "📦 Upgrading pip..."
    python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

    echo "📦 Installing dependencies..."
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r backend/requirements.txt

    if [ -n "$REQ_SHA" ]; then
        echo "$REQ_SHA" >"$REQ_STAMP_FILE"
    fi
else
    echo "✅ Dependencies up-to-date (skipping pip install)"
fi

# 验证必需的环境变量
if [ -z "$GEE_USER_PATH" ] || [ "$GEE_USER_PATH" = "users/default/aef_demo" ]; then
    echo "⚠️  WARNING: GEE_USER_PATH not configured or using default value"
    echo "   Please set it in .env file: GEE_USER_PATH=users/your_username/aef_demo"
fi

# Optional: Chapter 5 supervised RF classifier (assetized) bootstrap.
# - Hard gate startup: backend will NOT start unless the asset is ready.
# - If missing, it will auto-submit an export task and wait until ready (timeout).
CH5_RF_BOOTSTRAP="${CH5_RF_BOOTSTRAP:-1}"
CH5_RF_AUTO_EXPORT="${CH5_RF_AUTO_EXPORT:-1}"
CH5_RF_WAIT_TIMEOUT_S="${CH5_RF_WAIT_TIMEOUT_S:-420}"
CH5_RF_WAIT_INTERVAL_S="${CH5_RF_WAIT_INTERVAL_S:-8}"

# Earth Engine initialization check.
# IMPORTANT: Never attempt interactive authentication in non-interactive contexts
# (systemd / CI / ssh without TTY). The FastAPI app can still start with
# gee_initialized=false; it will degrade gracefully.
NONINTERACTIVE=0
if [ ! -t 0 ] || [ ! -t 1 ] || [ -n "${INVOCATION_ID:-}" ] || [ -n "${SYSTEMD_EXEC_PID:-}" ]; then
    NONINTERACTIVE=1
fi

echo "🔐 Checking Earth Engine initialization (service account preferred)..."
set +e
python - <<'PY'
from backend.gee_service import init_earth_engine

init_earth_engine()
print('✅ Earth Engine initialization successful')
PY
EE_INIT_STATUS=$?
set -e

if [ "$EE_INIT_STATUS" -ne 0 ]; then
    echo "⚠️  Earth Engine initialization failed."
    if [ "$NONINTERACTIVE" = "1" ]; then
        echo "   Non-interactive environment detected; skipping interactive Earth Engine authentication."
        echo "   Fix options:"
        echo "    - Configure service account: EE_SERVICE_ACCOUNT + EE_PRIVATE_KEY_FILE (recommended for production)"
        echo "    - Or pre-authenticate the service user and ensure systemd runs as that user"
    else
        echo "📝 You will get a URL. Open it in your browser and paste the code back here."
        echo ""

        # Best-effort interactive authentication helper.
        set +e
        if [ -x "$VENV_DIR/bin/earthengine" ]; then
            "$VENV_DIR/bin/earthengine" authenticate --auth_mode=notebook
        elif command -v earthengine >/dev/null 2>&1; then
            earthengine authenticate --auth_mode=notebook
        else
            echo "❌ earthengine command not found"
            echo "   Please install: pip install earthengine-api"
        fi

        echo ""
        echo "🔍 Re-checking Earth Engine initialization..."
        python - <<'PY'
from backend.gee_service import init_earth_engine

init_earth_engine()
print('✅ Earth Engine initialization successful')
PY
        EE_INIT_STATUS=$?
        set -e

        if [ "$EE_INIT_STATUS" -ne 0 ]; then
            echo "⚠️  Earth Engine is still not initialized; continuing in degraded mode."
        fi
    fi

    if [ "$CH5_RF_BOOTSTRAP" = "1" ]; then
        echo "⚠️  Disabling CH5_RF_BOOTSTRAP because Earth Engine is not initialized."
        CH5_RF_BOOTSTRAP="0"
    fi
else
    echo "✅ Earth Engine initialized"
fi

if [ "$CH5_RF_BOOTSTRAP" = "1" ]; then
    echo "🧊 Checking CH5 RF classifier asset..."

    # Optional: reset/retrain default asset id by deleting it and submitting a fresh export task.
    # Safety rules:
    # - Only operates on the derived default: ${GEE_USER_PATH}/classifiers/ch5_coastline_rf_v1
    # - Requires explicit confirmation flag: --ch5-rf-yes
    CH5_RF_EXPORT_ALREADY_SUBMITTED=0
    if [ "$CH5_RF_RESET_DEFAULT" = "1" ]; then
        if [ "$CH5_RF_RESET_YES" != "1" ]; then
            echo "❌ Refusing to reset CH5 RF default asset without --ch5-rf-yes"
            echo "   Example: ./run_backend.sh start --ch5-rf-reset-default --ch5-rf-yes"
            exit 1
        fi

        if [ -z "${GEE_USER_PATH:-}" ] || [ "${GEE_USER_PATH:-}" = "users/default/aef_demo" ]; then
            echo "❌ Cannot reset default CH5 RF asset because GEE_USER_PATH is not configured (or still default)."
            echo "   Fix: set GEE_USER_PATH in .env/.env.v6 (recommended), then retry."
            exit 1
        fi

        DEFAULT_CH5_RF_ASSET_ID="${GEE_USER_PATH%/}/classifiers/ch5_coastline_rf_v1"
        EFFECTIVE_CH5_RF_ASSET_ID="${CH5_RF_ASSET_ID:-$DEFAULT_CH5_RF_ASSET_ID}"

        if [ "$EFFECTIVE_CH5_RF_ASSET_ID" != "$DEFAULT_CH5_RF_ASSET_ID" ]; then
            echo "❌ Refusing to reset because CH5_RF_ASSET_ID is not the derived default."
            echo "   CH5_RF_ASSET_ID=$EFFECTIVE_CH5_RF_ASSET_ID"
            echo "   default=$DEFAULT_CH5_RF_ASSET_ID"
            echo "   Tip: unset CH5_RF_ASSET_ID (or set it to the default) if you really want to reset the default asset."
            exit 1
        fi

        echo "🧨 Resetting CH5 RF default asset (delete + re-export)"
        echo "   asset_id=$DEFAULT_CH5_RF_ASSET_ID"
        set +e
        python backend/ch5_rf_export.py --asset-id "$DEFAULT_CH5_RF_ASSET_ID" --delete --yes
        DEL_RC=$?
        if [ "$DEL_RC" -ne 0 ]; then
            echo "❌ Failed to delete default CH5 RF asset (rc=$DEL_RC)."
            set -e
            exit 1
        fi

        python backend/ch5_rf_export.py --asset-id "$DEFAULT_CH5_RF_ASSET_ID" --ensure
        ENSURE_RC=$?
        if [ "$ENSURE_RC" -ne 0 ]; then
            echo "❌ Failed to submit export task for default CH5 RF asset (rc=$ENSURE_RC)."
            set -e
            exit 1
        fi
        CH5_RF_EXPORT_ALREADY_SUBMITTED=1
        set -e
    fi

    set +e
    python backend/ch5_rf_export.py --check >/dev/null 2>&1
    CHECK_RC=$?
    if [ "$CHECK_RC" -ne 0 ]; then
        echo "❌ CH5 RF classifier asset not ready (rc=$CHECK_RC)."
        if [ "$CHECK_RC" -eq 2 ]; then
            echo "❌ CH5 RF asset id not configured. Set CH5_RF_ASSET_ID or GEE_USER_PATH (non-default)."
            set -e
            exit 1
        fi

        if [ "$CH5_RF_AUTO_EXPORT" = "1" ]; then
            if [ "$CH5_RF_EXPORT_ALREADY_SUBMITTED" != "1" ]; then
                echo "🚚 Submitting export task for CH5 RF classifier..."
                python backend/ch5_rf_export.py --ensure
                ENSURE_RC=$?
                if [ "$ENSURE_RC" -ne 0 ]; then
                    echo "❌ Failed to submit export task (rc=$ENSURE_RC)."
                    set -e
                    exit 1
                fi
            else
                echo "ℹ️  Export task already submitted (via --ch5-rf-reset-default); skipping re-submit"
            fi
            echo "⏳ Waiting for CH5 RF asset to become ready (timeout=${CH5_RF_WAIT_TIMEOUT_S}s)..."
            ELAPSED=0
            while [ "$ELAPSED" -lt "$CH5_RF_WAIT_TIMEOUT_S" ]; do
                python backend/ch5_rf_export.py --check >/dev/null 2>&1
                if [ "$?" -eq 0 ]; then
                    echo "✅ CH5 RF classifier asset is ready"
                    break
                fi
                sleep "$CH5_RF_WAIT_INTERVAL_S"
                ELAPSED=$((ELAPSED + CH5_RF_WAIT_INTERVAL_S))
            done
            if [ "$ELAPSED" -ge "$CH5_RF_WAIT_TIMEOUT_S" ]; then
                echo "❌ Timeout waiting for CH5 RF asset."
                echo "   Monitor tasks: https://code.earthengine.google.com/tasks"
                set -e
                exit 1
            fi
        else
            echo "❌ CH5 RF auto-export disabled (CH5_RF_AUTO_EXPORT=0)."
            echo "   Run: python backend/ch5_rf_export.py --ensure"
            echo "   Then re-run backend start after the task completes."
            set -e
            exit 1
        fi
    else
        echo "✅ CH5 RF classifier asset looks ready"
    fi
    set -e

    # Optional: blind-box alignment (legacy V6.7/V6.8).
    # V7.0 uses ESA gold-standard training so class IDs are stable; alignment is
    # not required and is disabled by default.
    CH5_ALIGN_BOOTSTRAP="${CH5_ALIGN_BOOTSTRAP:-0}"
    if [ "$CH5_ALIGN_BOOTSTRAP" = "1" ]; then
        echo "🎨 Auto-aligning CH5 coastline audit palette/mask (one-time heuristic)..."
        set +e
        ALIGN_OUT=$(python backend/ch5_rf_export.py --align 2>/dev/null)
        ALIGN_RC=$?
        set -e

        if [ "$ALIGN_RC" -eq 0 ] && [ -n "${ALIGN_OUT:-}" ]; then
            while IFS='=' read -r k v; do
                # Strip optional leading "export " (defensive) and spaces.
                k=$(echo "$k" | sed 's/^export[[:space:]]\+//' | tr -d ' \t\r')
                v=$(echo "$v" | tr -d '\r')
                case "$k" in
                    CH5_INLAND_CLASS_ID)
                        export CH5_INLAND_CLASS_ID="$v"
                        ;;
                    CH5_DEEP_SEA_CLASS_ID)
                        export CH5_DEEP_SEA_CLASS_ID="$v"
                        ;;
                    CH5_PALETTE)
                        export CH5_PALETTE="$v"
                        ;;
                    *)
                        ;;
                esac
            done <<<"$ALIGN_OUT"

            echo "✅ CH5 aligned: INLAND_CLASS_ID=${CH5_INLAND_CLASS_ID:-<unset>} DEEP_SEA_CLASS_ID=${CH5_DEEP_SEA_CLASS_ID:-<unset>}"
        else
            echo "⚠️  CH5 auto-alignment skipped/failed (rc=$ALIGN_RC)."
            echo "   Tip: set CH5_ALIGN_BOOTSTRAP=0 to disable; or manually set CH5_INLAND_CLASS_ID / CH5_DEEP_SEA_CLASS_ID / CH5_PALETTE in .env.v6"
        fi
    fi
fi

# 启动后端
echo "✅ Backend starting on http://${API_HOST}:${API_PORT}"
cd backend

# 默认关闭 --reload（当前环境里经常出现无意义的文件变更检测导致频繁重启）
# 如需开发热重载：DEV_RELOAD=1 ./run_backend.sh
UVICORN_RELOAD_ARGS=()
if [ "${DEV_RELOAD:-0}" = "1" ]; then
    UVICORN_RELOAD_ARGS=(--reload)
fi

UVICORN_WORKERS_VAL="${UVICORN_WORKERS:-}"
UVICORN_WORKERS_ARGS=()
if [ -n "$UVICORN_WORKERS_VAL" ]; then
    if [ "${DEV_RELOAD:-0}" = "1" ] && [ "$UVICORN_WORKERS_VAL" != "1" ]; then
        echo "⚠️  DEV_RELOAD=1 is incompatible with --workers>1; forcing UVICORN_WORKERS=1"
        UVICORN_WORKERS_VAL="1"
    fi
    if [ "$UVICORN_WORKERS_VAL" != "" ]; then
        UVICORN_WORKERS_ARGS=(--workers "$UVICORN_WORKERS_VAL")
    fi
fi

CMD=(python -m uvicorn main:app --host "$API_HOST" --port "$API_PORT")
CMD+=("${UVICORN_RELOAD_ARGS[@]}")
CMD+=("${UVICORN_WORKERS_ARGS[@]}")

if [ "$DAEMON" = "1" ]; then
    echo "🧷 Running backend in background"
    echo "   Log: $LOG_FILE"
    nohup "${CMD[@]}" >"$LOG_FILE" 2>&1 &
    pid=$!
    echo "$pid" >"$PID_FILE"

    # Wait for health
    if command -v curl >/dev/null 2>&1; then
        for _ in $(seq 1 40); do
            code=$(curl -s -o /dev/null -w "%{http_code}" "http://${API_HOST}:${API_PORT}/health" 2>/dev/null || echo "000")
            if [ "$code" = "200" ]; then
                echo "✅ Backend ready (pid=$pid)"
                exit 0
            fi
            sleep 0.25
        done
        echo "⚠️  Backend did not become ready in time; last log lines:"
        tail -n 80 "$LOG_FILE" || true
    fi
    exit 0
fi

exec "${CMD[@]}"
