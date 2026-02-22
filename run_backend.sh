#!/bin/bash
# AlphaEarth Cesium Backend 启动脚本

set -e

PRINT_CONFIG=0
if [ "${1:-}" = "--print-config" ]; then
    PRINT_CONFIG=1
    shift
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting AlphaEarth Cesium Backend..."

# Profile/config mode
# - Default profile is v6 (ports 8504/8505) to avoid conflict with v5
# - Prefer loading .env.<profile> if present (e.g. .env.v6)
ONEEARTH_PROFILE="${ONEEARTH_PROFILE:-v6}"
ENV_PATH=""
if [ -n "${ENV_FILE:-}" ]; then
    ENV_PATH="$ENV_FILE"
elif [ -f ".env.${ONEEARTH_PROFILE}" ]; then
    ENV_PATH=".env.${ONEEARTH_PROFILE}"
elif [ -f ".env" ]; then
    ENV_PATH=".env"
fi

# Select Python interpreter.
# NOTE: On some systems /usr/bin/python3 may be 3.6, while a newer python exists.
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

echo "🐍 Using Python: $($PYTHON_BIN -V) ($PYTHON_BIN)"

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

if [ "$ONEEARTH_PROFILE" = "v6" ] && [ "$API_PORT" = "8503" ]; then
    echo "⚠️  ONEEARTH_PROFILE=v6 but API_PORT=8503 (likely loaded v5 env)."
    echo "   Recommended: create .env.v6 with API_PORT=8505 and FRONTEND_PORT=8504"
fi

if [ "$PRINT_CONFIG" = "1" ]; then
    echo "ONEEARTH_PROFILE=$ONEEARTH_PROFILE"
    echo "ENV_PATH=${ENV_PATH:-<none>}"
    echo "API_HOST=$API_HOST"
    echo "API_PORT=$API_PORT"
    exit 0
fi

# 检查 Python 环境
# If an existing venv was created with an old interpreter (e.g., Python 3.6), rebuild it.
if [ -d "backend/venv" ] && [ -x "backend/venv/bin/python" ]; then
    VENV_VER_RAW=$(backend/venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
    VENV_MAJOR=$(echo "$VENV_VER_RAW" | cut -d. -f1)
    VENV_MINOR=$(echo "$VENV_VER_RAW" | cut -d. -f2)
    if [ "$VENV_MAJOR" -lt 3 ] || [ "$VENV_MINOR" -lt 9 ]; then
        echo "♻️  Recreating backend/venv (found Python $VENV_VER_RAW, need >= 3.9)"
        rm -rf backend/venv
    fi
fi

if [ ! -d "backend/venv" ]; then
    echo "📦 Creating virtual environment..."
    "$PYTHON_BIN" -m venv backend/venv
fi

# 激活虚拟环境
source backend/venv/bin/activate

# 升级 pip 并安装依赖（使用国内镜像源加速）
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "📦 Installing dependencies..."
pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r backend/requirements.txt

# 验证必需的环境变量
if [ -z "$GEE_USER_PATH" ] || [ "$GEE_USER_PATH" = "users/default/aef_demo" ]; then
    echo "⚠️  WARNING: GEE_USER_PATH not configured or using default value"
    echo "   Please set it in .env file: GEE_USER_PATH=users/your_username/aef_demo"
fi

# Earth Engine 认证检查
echo "🔐 Checking Earth Engine authentication..."
set +e
python -c "import ee; ee.Initialize(); print('Earth Engine: Already authenticated')" 2>/dev/null
EE_AUTH_STATUS=$?
set -e

if [ $EE_AUTH_STATUS -ne 0 ]; then
    echo "⚠️  Earth Engine not authenticated"
    echo "📝 You will get a URL. Open it in your browser and paste the code back here."
    echo ""
    
    # 检查是否有 earthengine 命令
    if [ -x "backend/venv/bin/earthengine" ]; then
        backend/venv/bin/earthengine authenticate --quiet --auth_mode=notebook
    else
        # 尝试全局 earthengine 命令
        if command -v earthengine >/dev/null 2>&1; then
            earthengine authenticate --quiet --auth_mode=notebook
        else
            echo "❌ earthengine command not found"
            echo "   Please install: pip install earthengine-api"
            echo "   Then run: earthengine authenticate"
            echo ""
            echo "   Or use a service account by setting in .env:"
            echo "   EE_SERVICE_ACCOUNT=xxx@yyy.iam.gserviceaccount.com"
            echo "   EE_PRIVATE_KEY_FILE=/path/to/key.json"
        fi
    fi
    
    # 验证认证是否成功
    echo ""
    echo "🔍 Validating Earth Engine authentication..."
    set +e
    python -c "import ee; ee.Initialize(); print('✅ Earth Engine authentication successful!')"
    if [ $? -ne 0 ]; then
        echo "⚠️  Authentication validation failed, but continuing..."
        echo "   You may see warnings when the server starts."
    fi
    set -e
    echo ""
else
    echo "✅ Earth Engine already authenticated"
fi

# 启动后端
echo "✅ Backend starting on http://${API_HOST}:${API_PORT}"
cd backend

# 默认关闭 --reload（当前环境里经常出现无意义的文件变更检测导致频繁重启）
# 如需开发热重载：DEV_RELOAD=1 ./run_backend.sh
UVICORN_RELOAD_ARGS=""
if [ "${DEV_RELOAD:-0}" = "1" ]; then
    UVICORN_RELOAD_ARGS="--reload"
fi

python -m uvicorn main:app --host ${API_HOST} --port ${API_PORT} ${UVICORN_RELOAD_ARGS}
