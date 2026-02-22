#!/bin/bash
# AlphaEarth Cesium Frontend 启动脚本

set -e

PRINT_CONFIG=0
if [ "${1:-}" = "--print-config" ]; then
    PRINT_CONFIG=1
    shift
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting AlphaEarth Cesium Frontend..."

# Profile/config mode
ONEEARTH_PROFILE="${ONEEARTH_PROFILE:-v6}"
ENV_PATH=""
if [ -n "${ENV_FILE:-}" ]; then
    ENV_PATH="$ENV_FILE"
elif [ -f ".env.${ONEEARTH_PROFILE}" ]; then
    ENV_PATH=".env.${ONEEARTH_PROFILE}"
elif [ -f ".env" ]; then
    ENV_PATH=".env"
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

if [ "$ONEEARTH_PROFILE" = "v6" ] && [ "$FRONTEND_PORT" = "8502" ]; then
    echo "⚠️  ONEEARTH_PROFILE=v6 but FRONTEND_PORT=8502 (likely loaded v5 env)."
    echo "   Recommended: create .env.v6 with API_PORT=8505 and FRONTEND_PORT=8504"
fi

if [ "$PRINT_CONFIG" = "1" ]; then
    echo "ONEEARTH_PROFILE=$ONEEARTH_PROFILE"
    echo "ENV_PATH=${ENV_PATH:-<none>}"
    echo "FRONTEND_PORT=$FRONTEND_PORT"
    exit 0
fi

# 进入前端目录
cd frontend

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# 启动前端
echo "✅ Frontend starting on http://0.0.0.0:${FRONTEND_PORT:-8504} (remote: http://47.245.113.151:${FRONTEND_PORT:-8504})"
npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT:-8504} --strictPort
