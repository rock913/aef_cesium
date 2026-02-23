"""Chapter 5 (Yancheng coastline audit) classifier export helper.

V8.0: Multi-Source Consensus Distillation (science-grade).

We retire single-source static landcover labeling as the only supervisor.
Instead we build *consensus* labels by cross-checking two global products:

    - ESA WorldCover (landcover class)
    - JRC Global Surface Water occurrence (0–100, long-term inundation frequency)

Consensus rules (labels are assigned only when the two sources agree under
strict physical constraints):

    - 0 Water: JRC occurrence >= 90% AND ESA says water
    - 1 Tidal flat: 5% < occurrence < 85% AND ESA is NOT built-up
    - 2 Built-up: ESA built-up AND occurrence == 0%
    - 3 Inland: ESA cropland/trees AND occurrence == 0%

Ambiguous pixels are excluded from training.

This yields stable, auditable class IDs by construction:
    0=water, 1=tidal mudflat, 2=built/artificial hardening, 3=inland background.

The backend loads the classifier via ee.Classifier.load(assetId) for fast
inference and stable semantics.

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
    seed = int(os.getenv("CH5_RF_SEED", "42") or "42")
    points_per_class = int(os.getenv("CH5_RF_POINTS_PER_CLASS", "2000") or "2000")
    rf_trees = int(os.getenv("CH5_RF_TREES", "50") or "50")

    # Use recent years for robustness.
    base_img = emb_col.filterDate("2023-01-01", "2025-01-01").mosaic().select(list(range(0, 16))).rename(emb_bands)

    # Dual gold standards (consensus): ESA WorldCover + JRC Global Surface Water.
    esa = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")

    # V8.0 consensus masks.
    # NOTE: use explicit parentheses for EE boolean precedence.
    pure_water = jrc.gte(90).And(esa.eq(80))
    pure_flat = jrc.gt(5).And(jrc.lt(85)).And(esa.neq(50))
    pure_built = esa.eq(50).And(jrc.unmask(0).eq(0))
    pure_inland = (esa.eq(40).Or(esa.eq(10))).And(jrc.unmask(0).eq(0))

    # Build labels inheriting projection from the embedding base to avoid pyramid/projection issues.
    # IMPORTANT: stratifiedSample requires classBand to be *integer typed*.
    labels = base_img.select([0]).multiply(0).toInt().subtract(1)
    labels = labels.where(pure_water, 0)
    labels = labels.where(pure_flat, 1)
    labels = labels.where(pure_built, 2)
    labels = labels.where(pure_inland, 3)
    labels = labels.toInt()

    training_mask = labels.neq(-1)
    gold_labels = labels.updateMask(training_mask).rename("class").toInt()

    training_stack = base_img.addBands(gold_labels)

    # Training region: broader Yancheng box (V7.0 doc).
    training_region = ee.Geometry.Rectangle([119.8, 32.8, 121.5, 34.0])

    training_data = training_stack.stratifiedSample(
        numPoints=points_per_class,
        classBand="class",
        region=training_region,
        scale=scale,
        seed=seed,
        tileScale=4,
        geometries=False,
    )

    classifier = ee.Classifier.smileRandomForest(rf_trees).train(
        features=training_data,
        classProperty="class",
        inputProperties=emb_bands,
    )
    return classifier


def _mode_int(values: list[int]) -> int:
    """Return the most frequent int value (ties: first encountered)."""

    if not values:
        raise ValueError("values must be non-empty")
    counts: dict[int, int] = {}
    for v in values:
        counts[int(v)] = counts.get(int(v), 0) + 1
    best = values[0]
    best_n = -1
    for v in values:
        n = counts.get(int(v), 0)
        if n > best_n:
            best = int(v)
            best_n = n
    return int(best)


def _infer_alignment(asset_id: str) -> Dict[str, str]:
    """Infer a one-time 'blind box alignment' for CH5.

    We classify a few anchor micro-regions and infer which class id corresponds to:
    - inland background (to be masked out)
    - water / mudflat / artificial hardening (to assign stable colors)

    Returns a dict of env-like strings:
    - CH5_INLAND_CLASS_ID
    - CH5_DEEP_SEA_CLASS_ID
    - CH5_PALETTE (comma-separated, 6 colors)
    """

    # 16-D embedding bands (match backend/gee_service.py)
    emb_col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    emb_bands = [f"A{idx:02d}" for idx in range(0, 16)]

    base_img = (
        emb_col.filterDate("2023-01-01", "2025-01-01")
        .mosaic()
        .select(list(range(0, 16)))
        .rename(emb_bands)
    )

    classifier = ee.Classifier.load(asset_id)
    class_img = base_img.classify(classifier)

    scale = int(os.getenv("CH5_RF_SAMPLE_SCALE", "30") or "30")
    # ReduceRegion(mode) is cheaper than sample+hist for tiny buffers.
    reducer = ee.Reducer.mode()

    def _mode_class_for_geom(geom: Any) -> int:
        out = class_img.reduceRegion(
            reducer=reducer,
            geometry=geom,
            scale=scale,
            maxPixels=int(1e7),
        )
        v = out.get("classification")
        # getInfo() returns client-side value.
        return int(ee.Number(v).getInfo())

    # Anchor micro-regions (盐城沿海)
    # NOTE: These are heuristics; if the scene changes drastically, manual override is still possible.
    anchors: dict[str, list[Any]] = {
        # inland: farmland / bare land away from the shoreline
        "inland": [
            ee.Geometry.Point([120.30, 33.65]).buffer(600),
            ee.Geometry.Point([120.20, 33.55]).buffer(600),
            ee.Geometry.Point([120.55, 33.60]).buffer(600),
        ],
        # deep sea: offshore open water (to be masked out)
        "deep_sea": [
            ee.Geometry.Point([121.35, 33.10]).buffer(900),
            ee.Geometry.Point([121.30, 33.05]).buffer(900),
        ],
        # turbid coastal water: nearshore high-suspended sediment water
        "turbid_water": [
            ee.Geometry.Point([120.82, 33.28]).buffer(700),
            ee.Geometry.Point([120.72, 33.48]).buffer(700),
        ],
        # mudflat: typical intertidal mudflat belt
        "mudflat": [
            ee.Geometry.Point([120.88, 33.35]).buffer(400),
            ee.Geometry.Point([120.92, 33.32]).buffer(400),
        ],
        # artificial: port / embankment / aquaculture grids
        "artificial": [
            ee.Geometry.Point([120.78, 33.24]).buffer(500),
            ee.Geometry.Point([120.65, 33.45]).buffer(500),
        ],
    }

    inferred: dict[str, int] = {}
    for key, geoms in anchors.items():
        vals: list[int] = []
        for g in geoms:
            try:
                vals.append(_mode_class_for_geom(g))
            except Exception:
                # Ignore single-point failures; we'll rely on remaining anchors.
                continue
        if vals:
            inferred[key] = _mode_int(vals)

    def _safe_int(v: Any, default: int) -> int:
        try:
            i = int(v)
        except Exception:
            return int(default)
        return i if 0 <= i <= 5 else int(default)

    inland_id = _safe_int(inferred.get("inland"), 5)
    deep_sea_id = _safe_int(inferred.get("deep_sea"), 1)

    # Build a palette of length 6 where index == class id.
    # Default to fully transparent to avoid semantic overflow.
    palette = ["000000"] * 6

    # Assign visible categories where we can infer them.
    # Note: multiple anchors may map to different ids; keep them all consistent.
    for k, color in [
        ("mudflat", "F6C431"),
        ("artificial", "E23D28"),
        ("turbid_water", "1A365D"),
    ]:
        class_id = inferred.get(k)
        if class_id is not None and 0 <= int(class_id) <= 5:
            palette[int(class_id)] = color

    # Always hide inland + deep sea.
    palette[int(inland_id)] = "000000"
    palette[int(deep_sea_id)] = "000000"

    # Any remaining (unknown) non-masked id: keep as blue for safe visibility.
    for i in range(0, 6):
        if i in {int(inland_id), int(deep_sea_id)}:
            continue
        if palette[i] == "000000":
            palette[i] = "1A365D"

    return {
        "CH5_INLAND_CLASS_ID": str(int(inland_id)),
        "CH5_DEEP_SEA_CLASS_ID": str(int(deep_sea_id)),
        "CH5_PALETTE": ",".join(palette),
    }


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
        description="Export_Coastline_RF_V8_Science",
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
    parser = argparse.ArgumentParser(description="Export/ensure CH5 KD RF classifier as a GEE Asset")
    parser.add_argument("--asset-id", default="", help="Override target asset id")
    parser.add_argument("--env-file", default="", help="Load env vars from a file (default: auto-detect repo .env)")
    parser.add_argument("--check", action="store_true", help="Only check whether the asset exists")
    parser.add_argument("--ensure", action="store_true", help="If missing, submit an export task")
    parser.add_argument("--delete", action="store_true", help="Delete the target asset (for retraining); requires --yes")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive actions (used with --delete)")
    parser.add_argument(
        "--align",
        action="store_true",
        help="Infer one-time CH5 palette/mask alignment and print env KEY=VALUE lines",
    )

    args = parser.parse_args()

    loaded_env = _auto_load_env(str(args.env_file).strip())
    asset_id = str(args.asset_id).strip() or _resolve_asset_id()
    if not asset_id:
        if loaded_env:
            print(f"ℹ️  Loaded environment from: {loaded_env}")
        print("⚠️  CH5 RF asset id not configured. Set CH5_RF_ASSET_ID or configure GEE_USER_PATH.")
        return 2

    if args.align:
        _init_ee()
        if not _asset_exists(asset_id):
            print("⚠️  CH5 RF classifier asset does not exist yet; cannot align.")
            return 1
        try:
            aligned = _infer_alignment(asset_id)
        except Exception as e:
            print(f"⚠️  Failed to infer CH5 alignment: {e}")
            return 1

        # Print as KEY=VALUE lines (safe for shell parsing without eval).
        for k in ["CH5_INLAND_CLASS_ID", "CH5_DEEP_SEA_CLASS_ID", "CH5_PALETTE"]:
            if k in aligned:
                print(f"{k}={aligned[k]}")
        return 0

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
