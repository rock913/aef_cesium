#!/usr/bin/env python3
"""
scripts/generate_real_insar_tiles.py
基于 7 组 Sentinel-1 真实星载解算成果（gz_velocity_real.tif 与 gz_coherence_real.tif），
离线全量生成符合 Web Mercator XYZ 标准规格（256x256 RGBA PNG）的真实瓦片金字塔（Zoom 10 ~ 15）。
彻底摒弃任何数学圆形/椭圆插值，100% 忠实还原星载微波雷达天然永久散射体（PS）与地表形变斑块。
"""

import math
import time
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
from pathlib import Path
import warnings

warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def tile_bounds(x, y, z):
    north, west = num2deg(x, y, z)
    south, east = num2deg(x + 1, y + 1, z)
    return west, south, east, north


def generate_all_tiles():
    data_dir = Path("/app/data/insar_hyp3")
    vel_path = data_dir / "gz_velocity_real.tif"
    coh_path = data_dir / "gz_coherence_real.tif"
    out_dir = Path("/app/data/tiles/ch8_insar")

    if not vel_path.exists():
        data_dir = Path("/mnt/data/hyf/aef_cesium/data/insar_hyp3")
        vel_path = data_dir / "gz_velocity_real.tif"
        coh_path = data_dir / "gz_coherence_real.tif"
        out_dir = Path("/mnt/data/hyf/aef_cesium/data/tiles/ch8_insar")

    import shutil
    if out_dir.exists():
        print(f"🧹 彻底清理旧切片缓存目录: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📡 载入真实雷达形变栅格: {vel_path}")
    t0 = time.time()
    with rasterio.open(vel_path) as src_v:
        v_crs = src_v.crs
        v_transform = src_v.transform
        v_data = src_v.read(1)

    with rasterio.open(coh_path) as src_c:
        c_data = src_c.read(1)

    print(f"✅ 栅格内存载入耗时: {time.time() - t0:.2f}s")

    west, south, east, north = 113.10, 22.50, 113.75, 23.35
    total_saved = 0

    # 包含从高空俯瞰到近地巡检全量层级 (Zoom 8 ~ 15)
    for z in range(8, 16):
        z_t0 = time.time()
        x_min, y_min = deg2num(north, west, z)
        x_max, y_max = deg2num(south, east, z)
        z_count = (x_max - x_min + 1) * (y_max - y_min + 1)
        z_saved = 0

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                tb_w, tb_s, tb_e, tb_n = tile_bounds(x, y, z)
                dst_trans = from_bounds(tb_w, tb_s, tb_e, tb_n, 256, 256)

                v_tile = np.full((256, 256), np.nan, dtype=np.float32)
                c_tile = np.full((256, 256), np.nan, dtype=np.float32)

                reproject(
                    v_data,
                    v_tile,
                    src_transform=v_transform,
                    src_crs=v_crs,
                    dst_transform=dst_trans,
                    dst_crs="EPSG:4326",
                    resampling=Resampling.bilinear,
                )
                reproject(
                    c_data,
                    c_tile,
                    src_transform=v_transform,
                    src_crs=v_crs,
                    dst_transform=dst_trans,
                    dst_crs="EPSG:4326",
                    resampling=Resampling.bilinear,
                )

                # 质量控制标准 (QC):
                # 1. 相干性 >= 0.60 (剔除水体与浓密植被噪点)
                # 2. 异常沉降 (|v| >= 5.0 mm/yr)
                # 3. 剔除严重解缠相位跳变飞点 (|v| <= 150.0 mm/yr)
                valid = (
                    np.isfinite(v_tile)
                    & np.isfinite(c_tile)
                    & (c_tile >= 0.60)
                    & ((v_tile < -5.0) | (v_tile > 5.0))
                    & (np.abs(v_tile) < 150.0)
                )

                if np.sum(valid) == 0:
                    continue

                r = np.zeros((256, 256), dtype=np.uint8)
                g = np.zeros((256, 256), dtype=np.uint8)
                b = np.zeros((256, 256), dtype=np.uint8)
                a = np.zeros((256, 256), dtype=np.uint8)

                # 发散式热力色表:
                # 严重沉降 (v <= -25 mm/yr): 深红 [255, 0, 0]
                m_crit = (v_tile <= -25.0) & valid
                r[m_crit] = 255
                g[m_crit] = 0
                b[m_crit] = 0

                # 显著沉降 (-25 < v <= -15 mm/yr): 红橙 [255, 90, 0]
                m_sig = (v_tile > -25.0) & (v_tile <= -15.0) & valid
                f_sig = (v_tile[m_sig] - (-25.0)) / 10.0
                r[m_sig] = 255
                g[m_sig] = (f_sig * 90).astype(np.uint8)
                b[m_sig] = 0

                # 中度沉降 (-15 < v <= -8 mm/yr): 橙黄 [255, 180, 0]
                m_mod = (v_tile > -15.0) & (v_tile <= -8.0) & valid
                f_mod = (v_tile[m_mod] - (-15.0)) / 7.0
                r[m_mod] = 255
                g[m_mod] = (90 + f_mod * 90).astype(np.uint8)
                b[m_mod] = 0

                # 轻微沉降 (-8 < v <= -5 mm/yr): 柠檬黄 [255, 255, 0]
                m_low = (v_tile > -8.0) & (v_tile <= -5.0) & valid
                f_low = (v_tile[m_low] - (-8.0)) / 3.0
                r[m_low] = 255
                g[m_low] = (180 + f_low * 75).astype(np.uint8)
                b[m_low] = 0

                # 抬升 (v > 5 mm/yr): 天蓝到宝蓝 [0, 150, 255]
                m_up = (v_tile > 5.0) & valid
                f_up = np.clip((v_tile[m_up] - 5.0) / 10.0, 0.0, 1.0)
                r[m_up] = 0
                g[m_up] = ((1.0 - f_up) * 180).astype(np.uint8)
                b[m_up] = (160 + f_up * 95).astype(np.uint8)

                # 不透明度设为 215 (约 84% alpha)，保留底图建筑白模透视
                a[valid] = 215

                tile_path = out_dir / str(z) / str(x) / f"{y}.png"
                tile_path.parent.mkdir(parents=True, exist_ok=True)

                rgba = np.stack([r, g, b, a], axis=0)
                with rasterio.open(
                    str(tile_path),
                    "w",
                    driver="PNG",
                    width=256,
                    height=256,
                    count=4,
                    dtype="uint8",
                ) as dst:
                    dst.write(rgba)

                z_saved += 1

        total_saved += z_saved
        print(
            f"🌍 Zoom {z} 切片完毕: 遍历 {z_count} 块, 保存非空实测瓦片 {z_saved} 块, 耗时 {time.time() - z_t0:.2f}s"
        )

    print(f"🎉 全部金字塔瓦片生成完毕！总计保存真实 InSAR 瓦片: {total_saved} 块, 总耗时: {time.time() - t0:.2f}s")


if __name__ == "__main__":
    generate_all_tiles()
