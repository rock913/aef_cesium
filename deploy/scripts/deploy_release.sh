#!/usr/bin/env bash

set -euo pipefail

_usage() {
  cat <<'EOF'
Usage:
  deploy_release.sh --base-path /opt/oneearth/cesium_app_v6 --release-id <id> \
    --backend-service oneearth-v6-backend-8507 \
    --health-url http://127.0.0.1:8507/health --frontend-url http://127.0.0.1:8506/ \
    --reload-nginx 1 --keep-releases 5

Notes:
- Expects the release to be extracted into: <base-path>/releases/<release-id>
- Switches <base-path>/current symlink to the new release.
- Restarts backend systemd service, optionally reloads nginx.
- Performs health checks; on failure auto-rollbacks.
EOF
}

BASE_PATH=""
RELEASE_ID=""
BACKEND_SERVICE=""
HEALTH_URL="http://127.0.0.1:8507/health"
FRONTEND_URL="http://127.0.0.1:8506/"
RELOAD_NGINX="0"
KEEP_RELEASES="5"

SUDO="sudo"

_init_sudo() {
  # Prefer non-interactive sudo when running as a non-root deploy user.
  if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
    return 0
  fi

  if command -v sudo >/dev/null 2>&1; then
    if sudo -n true >/dev/null 2>&1; then
      SUDO="sudo -n"
      return 0
    fi
  fi

  SUDO=""
}

while [ $# -gt 0 ]; do
  case "$1" in
    --base-path)
      BASE_PATH="${2:-}"; shift 2;;
    --release-id)
      RELEASE_ID="${2:-}"; shift 2;;
    --backend-service)
      BACKEND_SERVICE="${2:-}"; shift 2;;
    --health-url)
      HEALTH_URL="${2:-}"; shift 2;;
    --frontend-url)
      FRONTEND_URL="${2:-}"; shift 2;;
    --reload-nginx)
      RELOAD_NGINX="${2:-}"; shift 2;;
    --keep-releases)
      KEEP_RELEASES="${2:-}"; shift 2;;
    -h|--help)
      _usage; exit 0;;
    *)
      echo "Unknown arg: $1"; _usage; exit 2;;
  esac
done

if [ -z "$BASE_PATH" ] || [ -z "$RELEASE_ID" ] || [ -z "$BACKEND_SERVICE" ]; then
  echo "Missing required args."
  _usage
  exit 2
fi

_init_sudo

CURRENT_LINK="$BASE_PATH/current"
RELEASE_DIR="$BASE_PATH/releases/$RELEASE_ID"

if [ ! -d "$RELEASE_DIR" ]; then
  echo "Release dir not found: $RELEASE_DIR"
  exit 1
fi

if [ ! -d "$RELEASE_DIR/backend" ]; then
  echo "Invalid release (missing backend/): $RELEASE_DIR"
  exit 1
fi

if [ ! -d "$RELEASE_DIR/frontend/dist" ]; then
  echo "Invalid release (missing frontend/dist/). Did you run frontend build before packaging?"
  exit 1
fi

PREV_TARGET=""
if [ -L "$CURRENT_LINK" ]; then
  PREV_TARGET="$(readlink -f "$CURRENT_LINK" || true)"
fi

_echo_step() {
  echo
  echo "==> $*"
}

_wait_http_ok() {
  local url="$1"
  local name="$2"
  local tries="${3:-30}"
  local delay_s="${4:-1}"

  for i in $(seq 1 "$tries"); do
    if command -v curl >/dev/null 2>&1; then
      if curl -fsS "$url" >/dev/null 2>&1; then
        echo "✅ ${name} OK: $url"
        return 0
      fi
    else
      # Minimal fallback (no curl): skip
      echo "⚠️  curl not found; skipping http check for ${name}"
      return 0
    fi
    sleep "$delay_s"
  done

  echo "❌ ${name} check failed: $url"
  return 1
}

_restart_services() {
  _echo_step "Restarting backend service: $BACKEND_SERVICE"
  if ! ${SUDO} systemctl restart "$BACKEND_SERVICE"; then
    echo "❌ Failed to restart backend service: $BACKEND_SERVICE"
    echo "   If deploying as a non-root user, grant passwordless sudo for: systemctl restart ${BACKEND_SERVICE}"
    return 1
  fi

  if [ "$RELOAD_NGINX" = "1" ]; then
    _echo_step "Reloading nginx"
    if command -v nginx >/dev/null 2>&1; then
      ${SUDO} nginx -t
    fi
    # Prefer systemd reload when available.
    if systemctl list-unit-files | grep -q '^nginx\.service'; then
      if ! ${SUDO} systemctl reload nginx; then
        echo "❌ Failed to reload nginx via systemd"
        return 1
      fi
    else
      if ! ${SUDO} nginx -s reload; then
        echo "❌ Failed to reload nginx"
        return 1
      fi
    fi
  fi
}

_rollback() {
  if [ -z "$PREV_TARGET" ]; then
    echo "No previous current target recorded; cannot rollback."
    return 1
  fi
  _echo_step "Rolling back current -> $PREV_TARGET"
  ln -sfn "$PREV_TARGET" "$CURRENT_LINK"
  _restart_services || true
  return 0
}

_prune_old_releases() {
  local keep="$1"

  if [ ! -d "$BASE_PATH/releases" ]; then
    return 0
  fi

  # Sort by name (release ids are timestamp-prefixed by convention).
  mapfile -t rels < <(ls -1 "$BASE_PATH/releases" 2>/dev/null | sort -r || true)

  local count="${#rels[@]}"
  if [ "$count" -le "$keep" ]; then
    return 0
  fi

  for idx in $(seq "$keep" $((count - 1))); do
    local r="${rels[$idx]}"
    local dir="$BASE_PATH/releases/$r"

    # Never delete current target.
    local cur=""
    cur="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"
    if [ -n "$cur" ] && [ "$cur" = "$(readlink -f "$dir" 2>/dev/null || true)" ]; then
      continue
    fi

    rm -rf "$dir" || true
  done
}

_echo_step "Switching current -> $RELEASE_DIR"
ln -sfn "$RELEASE_DIR" "$CURRENT_LINK"

set +e
_restart_services
svc_rc=$?
set -e
if [ "$svc_rc" -ne 0 ]; then
  echo "❌ Service restart failed (rc=$svc_rc)"
  _rollback || true
  exit 1
fi

_echo_step "Health checks"
set +e
_wait_http_ok "$HEALTH_URL" "backend" 30 1
hc1=$?
_wait_http_ok "$FRONTEND_URL" "frontend" 30 1
hc2=$?
set -e

if [ "$hc1" -ne 0 ] || [ "$hc2" -ne 0 ]; then
  echo "❌ Health checks failed; rolling back"
  _rollback || true
  exit 1
fi

_echo_step "Deployment succeeded"
_prune_old_releases "$KEEP_RELEASES"

echo "✅ current -> $(readlink -f "$CURRENT_LINK")"
