#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSETS_DIR="$ROOT/frontend/public/assets"
URL="${ESO_MILKYWAY_URL:-https://cdn.eso.org/images/large/eso0932a.jpg}"

SRC="$ASSETS_DIR/eso_milkyway_source.jpg"
OUT="$ASSETS_DIR/eso_milkyway_8k.jpg"

mkdir -p "$ASSETS_DIR"

echo "[1/3] Downloading ESO panorama..."
curl -fL --retry 3 --retry-delay 1 "$URL" -o "$SRC"

magic_hex="$(head -c 2 "$SRC" | od -An -tx1 | tr -d ' \n')"
if [[ "$magic_hex" != "ffd8" ]]; then
  echo "ERROR: Downloaded file does not look like a JPEG (magic=$magic_hex)" >&2
  echo "       Source saved at: $SRC" >&2
  exit 1
fi

echo "[2/3] Ensuring frontend dependencies..."
if [[ ! -d "$ROOT/frontend/node_modules/sharp" ]]; then
  (cd "$ROOT/frontend" && npm install)
fi

echo "[3/3] Resizing to 8192x4096 (power-of-two)..."
node "$ROOT/frontend/scripts/prepare_eso_milkyway_8k.mjs" \
  --src "$SRC" \
  --out "$OUT" \
  --width 8192 \
  --height 4096 \
  --quality 90 \
  --min-bytes 1000000 \
  --clean-source 1

ls -lh "$OUT"
