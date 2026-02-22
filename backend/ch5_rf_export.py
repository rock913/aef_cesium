"""Chapter 5 (Yancheng coastline audit) supervised classifier export helper.

This follows the upgrade playbook in docs/江苏盐城案例案例升级.md:
- Sample AEF 16-D annual embedding features over a few representative polygons
- Train a lightweight Random Forest classifier
- Export it to a persistent GEE Asset

The backend can then load it via ee.Classifier.load(assetId) for millisecond inference.

Usage:
  python backend/ch5_rf_export.py --check
  python backend/ch5_rf_export.py --ensure
    python backend/ch5_rf_export.py --delete --yes

Environment:
  - CH5_RF_ASSET_ID: target Asset ID to load/export (preferred)
  - GEE_USER_PATH: used to derive a default asset path when CH5_RF_ASSET_ID is not set
  - EE_SERVICE_ACCOUNT / EE_PRIVATE_KEY_FILE: optional service account auth

Notes:
  - "--ensure" submits an export task; it does NOT wait for completion.
  - Monitor tasks at https://code.earthengine.google.com/tasks
    - "--delete" removes the classifier asset (useful for retraining). It requires --yes.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import time
from typing import Any, Dict, Iterable

import ee


def _maybe_setenv(key: str, value: str) -> None:
    if key not in os.environ or os.environ.get(key, "") == "":
        os.environ[key] = value


def _load_env_file(path: Path) -> None:
    """Minimal .env loader (no external deps).

    - Ignores comments and empty lines
    - Supports KEY=VALUE
    - Does not override existing os.environ
    """

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()
        if not key:
            continue
        # Strip optional quotes.
        if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
            val = val[1:-1]
        _maybe_setenv(key, val)


def _auto_load_env(env_file: str = "") -> str:
    """Load environment from repo-level .env files for standalone execution.

    Returns the path loaded (or empty string if none).
    """

    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent

    if env_file:
        p = Path(env_file).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if p.exists() and p.is_file():
            _load_env_file(p)
            return str(p)
        return ""

    # Mirror run_backend.sh behavior loosely.
    profile = str(os.getenv("ONEEARTH_PROFILE", "v6")).strip() or "v6"
    candidates = [repo_root / f".env.{profile}", repo_root / ".env"]
    for p in candidates:
        if p.exists() and p.is_file():
            _load_env_file(p)
            return str(p)
    return ""


def _resolve_asset_id() -> str:
    explicit = str(os.getenv("CH5_RF_ASSET_ID", "")).strip()
    if explicit:
        return explicit

    gee_user_path = str(os.getenv("GEE_USER_PATH", "")).strip()
    if gee_user_path and gee_user_path != "users/default/aef_demo":
        return f"{gee_user_path.rstrip('/')}/classifiers/ch5_coastline_rf_v1"

    return ""


def _init_ee() -> None:
    service_account = str(os.getenv("EE_SERVICE_ACCOUNT", "")).strip()
    private_key_file = str(os.getenv("EE_PRIVATE_KEY_FILE", "")).strip()

    if service_account and private_key_file:
        creds = ee.ServiceAccountCredentials(service_account, private_key_file)
        ee.Initialize(creds)
    else:
        ee.Initialize()


def _asset_exists(asset_id: str) -> bool:
    # Prefer ee.data.getAsset (fast metadata call) over attempting to load classifier.
    try:
        ee.data.getAsset(asset_id)
        return True
    except Exception:
        return False


def _asset_root_prefix_len(asset_id: str) -> int:
    parts = [p for p in asset_id.split("/") if p]
    if not parts:
        return 0

    # Common formats:
    # - users/<username>/...
    # - projects/<project-id>/assets/...
    if parts[0] == "users":
        return 2 if len(parts) >= 2 else 1
    if parts[0] == "projects":
        if len(parts) >= 3 and parts[2] == "assets":
            return 3
        return 2
    return 0


def _iter_parent_folders(folder_id: str) -> Iterable[str]:
    parts = [p for p in folder_id.split("/") if p]
    base_len = _asset_root_prefix_len(folder_id)
    # Start creating from the first folder after the root.
    for i in range(base_len + 1, len(parts) + 1):
        yield "/".join(parts[:i])


def _ensure_asset_folders_exist(asset_id: str) -> None:
    parent = asset_id.rsplit("/", 1)[0] if "/" in asset_id else ""
    if not parent:
        return

    for folder_id in _iter_parent_folders(parent):
        try:
            ee.data.getAsset(folder_id)
            continue
        except Exception:
            pass

        try:
            ee.data.createAsset({"type": "FOLDER"}, folder_id)
        except Exception as e:
            msg = str(e)
            raise RuntimeError(
                "Failed to create required asset folder. "
                f"folder_id={folder_id}. Error: {msg}. "
                "Fix: ensure you have write permission to this asset path, or set CH5_RF_ASSET_ID to a path you own "
                "(e.g. users/<username>/aef_demo/classifiers/ch5_coastline_rf_v1), or create the folder in the GEE Code Editor Assets panel."
            ) from e


def _build_classifier_graph() -> Any:
    emb_col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    emb_bands = [f"A{idx:02d}" for idx in range(0, 16)]

    scale = int(os.getenv("CH5_RF_SAMPLE_SCALE", "30") or "30")
    points_per_class = int(os.getenv("CH5_RF_POINTS_PER_CLASS", "1000") or "1000")
    seed = int(os.getenv("CH5_RF_SEED", "42") or "42")

    # Use recent years for robustness (as per playbook)
    base_img = emb_col.filterDate("2023-01-01", "2025-01-01").mosaic().select(list(range(0, 16))).rename(emb_bands)

    # ---------------------------------------------------------
    # Micro-Anchors + targeted debiasing
    #
    # Why:
    # - Large buffers in a narrow coastal transition zone inevitably mix classes,
    #   contaminating labels and causing semantic overflow.
    # - Aquaculture areas are a "water + embankment grid" mixture; we treat it
    #   as Class 2 (artificial hardening/reclamation) for stable semantics.
    #
    # Strategy:
    # - Shrink buffers to 200m–500m for purity
    # - Add explicit anchors for the observed failure zones (port + aquaculture)
    # ---------------------------------------------------------

    # Class 0: Water
    w_clear = ee.Geometry.Point([122.50, 31.00]).buffer(500)
    w_turbid_1 = ee.Geometry.Point([120.82, 33.28]).buffer(300)
    w_turbid_2 = ee.Geometry.Point([120.72, 33.48]).buffer(300)
    w_turbid_3 = ee.Geometry.Point([121.90, 31.40]).buffer(500)

    # Class 1: Natural mudflat
    m_flat_1 = ee.Geometry.Point([120.88, 33.35]).buffer(200)
    m_flat_2 = ee.Geometry.Point([121.95, 30.90]).buffer(200)

    # Class 2: Artificial hardening / reclamation (port + aquaculture + urban)
    a_port = ee.Geometry.Point([120.78, 33.24]).buffer(300)
    a_aqua = ee.Geometry.Point([120.65, 33.45]).buffer(400)
    a_urban = ee.Geometry.Point([121.48, 31.23]).buffer(500)

    # Class 3: Inland background mask class (must be diverse)
    b_farm_1 = ee.Geometry.Point([120.50, 33.40]).buffer(500)
    b_farm_2 = ee.Geometry.Point([120.20, 33.20]).buffer(500)
    b_bare = ee.Geometry.Point([120.40, 33.50]).buffer(500)
    b_water = ee.Geometry.Point([120.10, 31.20]).buffer(500)

    def _sample_class(geom: Any, class_id: int, class_seed_offset: int) -> Any:
        return (
            base_img.sample(
                region=geom,
                scale=scale,
                numPixels=points_per_class,
                seed=seed + class_seed_offset,
                geometries=False,
                tileScale=4,
            )
            .map(lambda f: ee.Feature(f).set("class", class_id))
        )

    training_data = (
        _sample_class(w_clear, 0, 0)
        .merge(_sample_class(w_turbid_1, 0, 1))
        .merge(_sample_class(w_turbid_2, 0, 2))
        .merge(_sample_class(w_turbid_3, 0, 3))
        .merge(_sample_class(m_flat_1, 1, 4))
        .merge(_sample_class(m_flat_2, 1, 5))
        .merge(_sample_class(a_port, 2, 6))
        .merge(_sample_class(a_aqua, 2, 7))
        .merge(_sample_class(a_urban, 2, 8))
        .merge(_sample_class(b_farm_1, 3, 9))
        .merge(_sample_class(b_farm_2, 3, 10))
        .merge(_sample_class(b_bare, 3, 11))
        .merge(_sample_class(b_water, 3, 12))
    )

    classifier = ee.Classifier.smileRandomForest(numberOfTrees=50, minLeafPopulation=5).train(
        features=training_data,
        classProperty="class",
        inputProperties=emb_bands,
    )
    return classifier


def _task_status(task: Any) -> Dict[str, Any]:
    try:
        status = task.status()  # type: ignore[attr-defined]
        return status if isinstance(status, dict) else {"raw": status}
    except Exception as e:
        return {"error": str(e)}


def _submit_export(asset_id: str) -> str:
    _ensure_asset_folders_exist(asset_id)
    classifier = _build_classifier_graph()
    task = ee.batch.Export.classifier.toAsset(
        classifier=classifier,
        description="Export_Coastline_RF_Classifier",
        assetId=asset_id,
    )
    task.start()

    # Surface immediate failures (e.g. missing parent folders / permission) as early as possible.
    time.sleep(0.5)
    status = _task_status(task)
    state = str(status.get("state", "")).upper()
    if state in {"FAILED", "CANCELLED"}:
        err = status.get("error_message") or status.get("error") or status
        raise RuntimeError(f"Export task {state}: {err}")

    return str(getattr(task, "id", "")) or "<unknown>"


def _delete_asset(asset_id: str) -> None:
    try:
        ee.data.deleteAsset(asset_id)
    except Exception as e:
        raise RuntimeError(f"Failed to delete asset: {asset_id}. Error: {e}") from e


def main() -> int:
    parser = argparse.ArgumentParser(description="Export/ensure CH5 supervised RF classifier as a GEE Asset")
    parser.add_argument("--asset-id", default="", help="Override target asset id")
    parser.add_argument("--env-file", default="", help="Load env vars from a file (default: auto-detect repo .env)")
    parser.add_argument("--check", action="store_true", help="Only check whether the asset exists")
    parser.add_argument("--ensure", action="store_true", help="If missing, submit an export task")
    parser.add_argument("--delete", action="store_true", help="Delete the target asset (for retraining); requires --yes")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive actions (used with --delete)")

    args = parser.parse_args()

    loaded_env = _auto_load_env(str(args.env_file).strip())
    asset_id = str(args.asset_id).strip() or _resolve_asset_id()
    if not asset_id:
        if loaded_env:
            print(f"ℹ️  Loaded environment from: {loaded_env}")
        print("⚠️  CH5 RF asset id not configured. Set CH5_RF_ASSET_ID or configure GEE_USER_PATH.")
        return 2

    try:
        _init_ee()
    except Exception as e:
        print(f"⚠️  Earth Engine init failed: {e}")
        return 3

    exists = _asset_exists(asset_id)

    if args.delete:
        print(f"CH5_RF_ASSET_ID={asset_id}")
        if not exists:
            print("ℹ️  Asset does not exist; nothing to delete")
            return 0
        if not args.yes:
            print("❌ Refusing to delete without --yes")
            return 6
        try:
            _delete_asset(asset_id)
            print(f"✅ Deleted asset: {asset_id}")
            return 0
        except Exception as e:
            print(f"❌ Failed to delete asset: {e}")
            return 7
    if args.check and not args.ensure:
        print(f"CH5_RF_ASSET_ID={asset_id}")
        print("✅ Asset exists" if exists else "❌ Asset missing")
        return 0 if exists else 4

    if exists:
        print(f"✅ Asset already exists: {asset_id}")
        return 0

    if not args.ensure:
        print(f"❌ Asset missing: {asset_id}")
        print("Set --ensure to submit an export task.")
        return 4

    try:
        task_id = _submit_export(asset_id)
        print(f"✅ Export task submitted. asset_id={asset_id}")
        print(f"   task_id={task_id}")
        print("   Monitor: https://code.earthengine.google.com/tasks")
        return 0
    except Exception as e:
        print(f"❌ Failed to submit export task: {e}")
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
