#!/usr/bin/env bash

set -euo pipefail

# Local production deploy (8506/8507) for servers that use:
#   /opt/oneearth/cesium_app_v6/{releases,current,.env.prod}
#   systemd backend service: oneearth-v6-backend-8507
#   nginx serving 8506 and proxying /api -> 8507
#
# This script:
#  1) builds frontend/dist (using /opt/.../.env.prod for VITE_* injection)
#  2) packages a release archive
#  3) extracts to /opt/.../releases/<release_id>
#  4) runs deploy/scripts/deploy_release.sh (atomic symlink switch + restart + health checks)
#
# Requires interactive sudo (it will prompt for password).

BASE_PATH="${PROD_PATH:-/opt/oneearth/cesium_app_v6}"
BACKEND_SERVICE="${PROD_BACKEND_SERVICE:-oneearth-v6-backend-8507}"
HEALTH_URL="${PROD_HEALTH_URL:-http://127.0.0.1:8507/health}"
FRONTEND_URL="${PROD_FRONTEND_URL:-http://127.0.0.1:8506/}"
KEEP_RELEASES="${PROD_KEEP_RELEASES:-5}"

if [ ! -d "$BASE_PATH" ]; then
  echo "❌ PROD base path not found: $BASE_PATH"
  exit 1
fi

if [ ! -f "$BASE_PATH/.env.prod" ]; then
  echo "❌ Missing production env file: $BASE_PATH/.env.prod"
  echo "   This file should contain at least ports and VITE_* build-time vars (e.g. VITE_CESIUM_TOKEN)."
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if ! command -v git >/dev/null 2>&1; then
  echo "❌ git not found"
  exit 1
fi

short_sha="$(git rev-parse --short=8 HEAD)"
ts="$(date -u +'%Y%m%d_%H%M%S')"
release_id="${PROD_RELEASE_ID:-${ts}_${short_sha}}"
archive="/tmp/release_${release_id}.tar.gz"

_echo() {
  echo
  echo "==> $*"
}

_echo "Build frontend/dist (production)"
set +x
set -a
# shellcheck disable=SC1090
source "$BASE_PATH/.env.prod"
set +a
set -x

cd "$REPO_ROOT/frontend"

# Ensure reproducible deps
npm ci
npm run build

cd "$REPO_ROOT"

_echo "Create release archive: $archive"
rm -f "$archive"
tar -czf "$archive" \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='.venv' \
  --exclude='backend/venv' \
  --exclude='frontend/node_modules' \
  --exclude='logs' \
  --exclude='**/__pycache__' \
  --exclude='**/.pytest_cache' \
  backend frontend/dist deploy run_backend.sh run_prod_single.sh Makefile pytest.ini README.md QUICK_REFERENCE.md

_echo "Extract into releases/${release_id}"
# This part requires root on most servers; allow interactive prompt.
sudo mkdir -p "$BASE_PATH/releases/$release_id"
sudo tar -xzf "$archive" -C "$BASE_PATH/releases/$release_id"

_echo "Deploy (atomic switch + restart + health checks)"
# Force interactive sudo inside deploy_release.sh if sudoers requires password.
DEPLOY_SUDO_INTERACTIVE=1 sudo bash "$REPO_ROOT/deploy/scripts/deploy_release.sh" \
  --base-path "$BASE_PATH" \
  --release-id "$release_id" \
  --backend-service "$BACKEND_SERVICE" \
  --health-url "$HEALTH_URL" \
  --frontend-url "$FRONTEND_URL" \
  --reload-nginx 1 \
  --keep-releases "$KEEP_RELEASES"

_echo "Done"
echo "✅ release_id=$release_id"
echo "✅ current -> $(readlink -f "$BASE_PATH/current")"

echo
echo "==> Verify (fingerprint)"
echo "Frontend URL: ${FRONTEND_URL}"
if command -v curl >/dev/null 2>&1; then
  echo "--- ${FRONTEND_URL} headers ---"
  curl -fsSI "${FRONTEND_URL}" | sed -n '1,12p' || true
  echo "--- main asset referenced by index.html ---"
  curl -fsS "${FRONTEND_URL}" | tr -d '\r' | grep -Eo '/assets/index-[^"\x27>]+\.js' | head -n 1 || true
  echo "Tip: if you are checking docker-prod, use http://127.0.0.1:8406/ (different deployment target)."
fi
