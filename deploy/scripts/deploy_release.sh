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
SYSTEMCTL="systemctl"
NGINX_BIN="nginx"

_init_sudo() {
  # Prefer non-interactive sudo when running as a non-root deploy user.
  if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
    return 0
  fi

  if ! command -v sudo >/dev/null 2>&1; then
    echo "❌ sudo not found, but deploying as non-root requires sudo for systemctl/nginx."
    exit 1
  fi

  # Deploy scripts often run in CI over SSH with a pseudo-tty allocated.
  # Even if a TTY exists, there is still no human to type a password.
  # Therefore default to non-interactive sudo.
  #
  # If a server requires interactive sudo, operators can override by exporting:
  #   DEPLOY_SUDO_INTERACTIVE=1
  if [ "${DEPLOY_SUDO_INTERACTIVE:-0}" = "1" ]; then
    SUDO="sudo"
  else
    SUDO="sudo -n"
  fi

  # Use absolute paths where possible so sudoers command matching is reliable.
  if [ -x /bin/systemctl ]; then
    SYSTEMCTL="/bin/systemctl"
  elif [ -x /usr/bin/systemctl ]; then
    SYSTEMCTL="/usr/bin/systemctl"
  fi

  if [ -x /usr/sbin/nginx ]; then
    NGINX_BIN="/usr/sbin/nginx"
  elif command -v nginx >/dev/null 2>&1; then
    NGINX_BIN="$(command -v nginx)"
  fi
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

# Guardrail: ensure key static assets exist in the built dist.
# If these are missing, nginx/vite-preview will often serve index.html (SPA fallback),
# which makes images look "not showing" even though the HTTP status is 200.
if [ ! -f "$RELEASE_DIR/frontend/dist/zero2x/ui/act2_geogpt.webp" ] || \
   [ ! -f "$RELEASE_DIR/frontend/dist/zero2x/ui/act2_astronomy.webp" ] || \
   [ ! -f "$RELEASE_DIR/frontend/dist/zero2x/ui/act3_genos.webp" ] || \
   [ ! -f "$RELEASE_DIR/frontend/dist/zero2x/ui/act3_oneporous.webp" ]; then
  echo "❌ Release is missing required Zero2x UI assets in frontend/dist/zero2x/ui/"
  echo "   Expected: act2_geogpt.webp, act2_astronomy.webp, act3_genos.webp, act3_oneporous.webp"
  echo "   Fix: rebuild frontend before packaging (cd frontend && npm ci && npm run build)"
  exit 1
fi

if [ ! -f "$RELEASE_DIR/run_backend.sh" ]; then
  echo "Invalid release (missing run_backend.sh): $RELEASE_DIR"
  exit 1
fi

PREV_TARGET=""
if [ -L "$CURRENT_LINK" ]; then
  PREV_TARGET="$(readlink -f "$CURRENT_LINK" || true)"
fi

_is_valid_release_dir() {
  local dir="$1"

  if [ -z "$dir" ] || [ ! -d "$dir" ]; then
    return 1
  fi
  if [ ! -d "$dir/backend" ]; then
    return 1
  fi
  if [ ! -d "$dir/frontend/dist" ]; then
    return 1
  fi
  if [ ! -f "$dir/run_backend.sh" ]; then
    return 1
  fi
  return 0
}

if [ -n "$PREV_TARGET" ] && ! _is_valid_release_dir "$PREV_TARGET"; then
  echo "⚠️  Previous current target is not a valid release; disabling rollback to it: $PREV_TARGET"
  PREV_TARGET=""
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
      if curl -fsS --connect-timeout 2 --max-time 4 "$url" >/dev/null 2>&1; then
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

_wait_http_header_contains() {
  local url="$1"
  local name="$2"
  local header_re="$3"
  local tries="${4:-30}"
  local delay_s="${5:-1}"

  for i in $(seq 1 "$tries"); do
    if command -v curl >/dev/null 2>&1; then
      headers="$(curl -fsSI --connect-timeout 2 --max-time 4 "$url" 2>/dev/null | tr -d '\r' || true)"
      if echo "$headers" | grep -Eqi "$header_re"; then
        echo "✅ ${name} OK: $url"
        return 0
      fi
    else
      echo "⚠️  curl not found; skipping header check for ${name}"
      return 0
    fi
    sleep "$delay_s"
  done

  echo "❌ ${name} header check failed: $url"
  return 1
}

_restart_services() {
  _echo_step "Restarting backend service: $BACKEND_SERVICE"
  if ! ${SUDO} ${SYSTEMCTL} restart "$BACKEND_SERVICE"; then
    echo "❌ Failed to restart backend service: $BACKEND_SERVICE"
    echo "   If deploying as a non-root user, grant passwordless sudo for: systemctl restart ${BACKEND_SERVICE}"
    return 1
  fi

  _reload_nginx() {
    local strict="${DEPLOY_STRICT_NGINX_RELOAD:-0}"

    _echo_step "Reloading nginx"
    if [ -n "${NGINX_BIN:-}" ] && command -v "${NGINX_BIN}" >/dev/null 2>&1; then
      # Validate config first (fast-fail if broken).
      if ! ${SUDO} "${NGINX_BIN}" -t; then
        echo "❌ nginx -t failed"
        return 1
      fi
    fi

    # Prefer systemd reload, but be robust about command path matching in sudoers.
    local reloaded=0
    if command -v systemctl >/dev/null 2>&1; then
      if [ -x /bin/systemctl ]; then
        if ${SUDO} /bin/systemctl reload nginx; then reloaded=1; fi
      fi
      if [ "$reloaded" -eq 0 ] && [ -x /usr/bin/systemctl ]; then
        if ${SUDO} /usr/bin/systemctl reload nginx; then reloaded=1; fi
      fi
      if [ "$reloaded" -eq 0 ]; then
        if ${SUDO} systemctl reload nginx; then reloaded=1; fi
      fi
    fi

    # Fallback: nginx signal reload.
    if [ "$reloaded" -eq 0 ]; then
      if [ -n "${NGINX_BIN:-}" ] && command -v "${NGINX_BIN}" >/dev/null 2>&1; then
        if ${SUDO} "${NGINX_BIN}" -s reload; then reloaded=1; fi
      fi
    fi

    if [ "$reloaded" -eq 1 ]; then
      echo "✅ nginx reloaded"
      return 0
    fi

    # In this repo's release model, switching the <base>/current symlink updates static files immediately.
    # Reloading nginx is only required when nginx config changes (which is not part of a release bundle).
    echo "⚠️  nginx reload failed (often due to sudoers command/arg mismatch)."
    echo "   Continuing without rollback because current symlink is already switched."
    echo "   To make this step passwordless, allow one of these commands in sudoers:"
    echo "     /bin/systemctl reload nginx"
    echo "     /usr/bin/systemctl reload nginx"
    echo "     /usr/sbin/nginx -t"
    echo "     /usr/sbin/nginx -s reload"
    if [ "$strict" = "1" ]; then
      echo "❌ DEPLOY_STRICT_NGINX_RELOAD=1: failing deploy due to nginx reload failure"
      return 1
    fi
    return 0
  }

  if [ "$RELOAD_NGINX" = "1" ]; then
    _reload_nginx
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
_wait_http_ok "$HEALTH_URL" "backend" 180 1
hc1=$?
_wait_http_ok "$FRONTEND_URL" "frontend" 60 1
hc2=$?

# Extra: verify landing assets are served as WebP (not SPA index.html fallback).
_wait_http_header_contains "${FRONTEND_URL}zero2x/ui/act2_geogpt.webp" "frontend asset act2_geogpt.webp" '^[Cc]ontent-[Tt]ype:.*image/webp' 60 1
hc3=$?
_wait_http_header_contains "${FRONTEND_URL}zero2x/ui/act2_astronomy.webp" "frontend asset act2_astronomy.webp" '^[Cc]ontent-[Tt]ype:.*image/webp' 60 1
hc4=$?
_wait_http_header_contains "${FRONTEND_URL}zero2x/ui/act3_genos.webp" "frontend asset act3_genos.webp" '^[Cc]ontent-[Tt]ype:.*image/webp' 60 1
hc5=$?
_wait_http_header_contains "${FRONTEND_URL}zero2x/ui/act3_oneporous.webp" "frontend asset act3_oneporous.webp" '^[Cc]ontent-[Tt]ype:.*image/webp' 60 1
hc6=$?
set -e

if [ "$hc1" -ne 0 ] || [ "$hc2" -ne 0 ] || [ "$hc3" -ne 0 ] || [ "$hc4" -ne 0 ] || [ "$hc5" -ne 0 ] || [ "$hc6" -ne 0 ]; then
  echo "❌ Health checks failed; rolling back"
  _rollback || true
  exit 1
fi

_echo_step "Deployment succeeded"
_prune_old_releases "$KEEP_RELEASES"

echo "✅ current -> $(readlink -f "$CURRENT_LINK")"
