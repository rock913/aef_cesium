#!/usr/bin/env python3
"""
CH9 绍兴真实 InSAR 瓦片生成：sx_* raw（EPSG:4326 速度/相干性）→ XYZ PNG 瓦片金字塔

基于 ch9_convert_insar_shaoxing.py 合成的真实 InSAR 栅格，生成 Web Mercator XYZ
RGBA PNG 瓦片（Zoom 8~15），供后端 /api/tiles/local_ch9_insar 直连，替代 GEE 仿真。

诚实口径：真实单对干涉相干性偏低，QC 阈值放低到 γ≥0.25、|v|≥2 mm/yr，
仅过滤最差噪点；输出为 LOS 向相对形变，未经 ERA5 大气校正。
"""
import math
import shutil
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
import warnings

warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)

DATA_DIR = Path("/mnt/data/hyf/aef_cesium/data/insar_hyp3")
OUT_DIR = Path("/mnt/data/hyf/aef_cesium/data/tiles/ch9_insar")

COH_THRESHOLD = 0.25
VEL_THRESHOLD = 2.0  # mm/yr


def deg2num(lat_deg, lon_deg, zoom):
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(math.radians(lat_deg))) / math.pi) / 2.0 * n)
    return xtile, ytile


def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_deg = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ytile / n))))
    return lat_deg, lon_deg


def tile_bounds(x, y, z):
    north, west = num2deg(x, y, z)
    south, east = num2deg(x + 1, y + 1, z)
    return west, south, east, north


def main():
    import json
    meta = json.loads((DATA_DIR / "sx_raster_meta.json").read_text(encoding="utf-8"))
    w, h = meta["width"], meta["height"]
    west, south, east, north = meta["bounds"]

    vel = np.fromfile(DATA_DIR / "sx_velocity_real.raw", dtype="<f4").reshape(h, w).astype(np.float32)
    coh = np.fromfile(DATA_DIR / "sx_coherence_real.raw", dtype="<f4").reshape(h, w).astype(np.float32)
    src_transform = from_bounds(west, south, east, north, w, h)
    print(f"📡 载入真实绍兴 InSAR 栅格 {w}x{h}, bounds {meta['bounds']}")

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    for z in range(8, 16):
        x_min, y_min = deg2num(north, west, z)
        x_max, y_max = deg2num(south, east, z)
        saved = 0
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                tw, ts, te, tn = tile_bounds(x, y, z)
                dst_trans = from_bounds(tw, ts, te, tn, 256, 256)
                v_tile = np.full((256, 256), np.nan, dtype=np.float32)
                c_tile = np.full((256, 256), np.nan, dtype=np.float32)
                reproject(vel, v_tile, src_transform=src_transform, src_crs="EPSG:4326",
                          dst_transform=dst_trans, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
                reproject(coh, c_tile, src_transform=src_transform, src_crs="EPSG:4326",
                          dst_transform=dst_trans, dst_crs="EPSG:4326", resampling=Resampling.bilinear)

                valid = (np.isfinite(v_tile) & np.isfinite(c_tile)
                         & (c_tile >= COH_THRESHOLD)
                         & (np.abs(v_tile) >= VEL_THRESHOLD)
                         & (np.abs(v_tile) < 60.0))
                if valid.sum() == 0:
                    continue

                r = np.zeros((256, 256), np.uint8)
                g = np.zeros((256, 256), np.uint8)
                b = np.zeros((256, 256), np.uint8)
                a = np.zeros((256, 256), np.uint8)

                # 沉降 (v <= -2): 红→橙
                sub = (v_tile <= -2.0) & valid
                f = np.clip((-v_tile[sub] - 2.0) / 18.0, 0, 1)
                r[sub] = 255
                g[sub] = (30 + f * 130).astype(np.uint8)
                b[sub] = 30
                # 抬升 (v >= 2): 蓝→青
                up = (v_tile >= 2.0) & valid
                f2 = np.clip((v_tile[up] - 2.0) / 18.0, 0, 1)
                r[up] = (30 - f2 * 30).astype(np.uint8)
                g[up] = (150 + f2 * 80).astype(np.uint8)
                b[up] = 255

                a[valid] = 200

                p = OUT_DIR / str(z) / str(x) / f"{y}.png"
                p.parent.mkdir(parents=True, exist_ok=True)
                with rasterio.open(str(p), "w", driver="PNG", width=256, height=256,
                                   count=4, dtype="uint8") as dst:
                    dst.write(np.stack([r, g, b, a], axis=0))
                saved += 1
        total += saved
        print(f"🌍 Zoom {z}: 保存 {saved} 块")
    print(f"🎉 完成：共 {total} 块真实 InSAR 瓦片 → {OUT_DIR}")


if __name__ == "__main__":
    main()
