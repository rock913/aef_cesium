"""Chapter 5 (Yancheng coastline audit) supervised classifier export helper.

This follows the upgrade playbook in docs/江苏盐城案例案例升级.md:
- Sample AEF 16-D annual embedding features over a few representative polygons
- Train a lightweight Random Forest classifier
- Export it to a persistent GEE Asset

The backend can then load it via ee.Classifier.load(assetId) for millisecond inference.

Usage:
  python backend/ch5_rf_export.py --check
  python backend/ch5_rf_export.py --ensure

Environment:
  - CH5_RF_ASSET_ID: target Asset ID to load/export (preferred)
  - GEE_USER_PATH: used to derive a default asset path when CH5_RF_ASSET_ID is not set
  - EE_SERVICE_ACCOUNT / EE_PRIVATE_KEY_FILE: optional service account auth

Notes:
  - "--ensure" submits an export task; it does NOT wait for completion.
  - Monitor tasks at https://code.earthengine.google.com/tasks
"""

from __future__ import annotations

import argparse
import os
from typing import Any

import ee


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


def _build_classifier_graph() -> Any:
    emb_col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    emb_bands = [f"A{idx:02d}" for idx in range(0, 16)]

    # Use recent years for robustness (as per playbook)
    base_img = emb_col.filterDate("2023-01-01", "2025-01-01").mosaic().select(list(range(0, 16))).rename(emb_bands)

    # Representative polygons (multi-pixel regions are more robust than points)
    # Class 0: water
    water_clear = ee.Feature(ee.Geometry.Rectangle([122.3, 30.8, 122.6, 31.2]), {"class": 0})
    water_turbid = ee.Feature(ee.Geometry.Rectangle([121.8, 31.3, 122.0, 31.5]), {"class": 0})

    # Class 1: natural mudflat
    mudflat = ee.Feature(ee.Geometry.Rectangle([120.8, 33.4, 121.0, 33.6]), {"class": 1})

    # Class 2: artificial hardening / reclamation
    urban = ee.Feature(ee.Geometry.Rectangle([121.4, 31.1, 121.6, 31.3]), {"class": 2})
    reclamation = ee.Feature(ee.Geometry.Rectangle([121.85, 30.85, 121.95, 30.95]), {"class": 2})

    training_regions = ee.FeatureCollection([water_clear, water_turbid, mudflat, urban, reclamation])

    training_data = base_img.sampleRegions(
        collection=training_regions,
        properties=["class"],
        scale=30,
        tileScale=4,
    )

    classifier = ee.Classifier.smileRandomForest(10).train(
        features=training_data,
        classProperty="class",
        inputProperties=emb_bands,
    )
    return classifier


def _submit_export(asset_id: str) -> str:
    classifier = _build_classifier_graph()
    task = ee.batch.Export.classifier.toAsset(
        classifier=classifier,
        description="Export_Coastline_RF_Classifier",
        assetId=asset_id,
    )
    task.start()
    return str(getattr(task, "id", "")) or "<unknown>"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export/ensure CH5 supervised RF classifier as a GEE Asset")
    parser.add_argument("--asset-id", default="", help="Override target asset id")
    parser.add_argument("--check", action="store_true", help="Only check whether the asset exists")
    parser.add_argument("--ensure", action="store_true", help="If missing, submit an export task")

    args = parser.parse_args()

    asset_id = str(args.asset_id).strip() or _resolve_asset_id()
    if not asset_id:
        print("⚠️  CH5 RF asset id not configured. Set CH5_RF_ASSET_ID or configure GEE_USER_PATH.")
        return 2

    try:
        _init_ee()
    except Exception as e:
        print(f"⚠️  Earth Engine init failed: {e}")
        return 3

    exists = _asset_exists(asset_id)
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
