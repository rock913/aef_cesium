#!/usr/bin/env python3
"""
CH9 绍兴真实 InSAR 成果合成：HyP3 ZIP → sx_* raw 速度/相干性栅格（地理坐标 EPSG:4326）

从每个 HyP3 干涉对 ZIP 提取 *_los_disp.tif（视线向位移，米）与 *_corr.tif，
统一重投影到绍兴靶区 EPSG:4326 网格，按时间基线合成年均 LOS 速度 (mm/yr)
与平均相干性，写入 data/insar_hyp3/sx_* 供后端自动读取。

诚实口径：单对干涉含大气/解缠噪声，速度未经 ERA5 大气校正与参考点精化，
仅做多对加权平均 + 空间平滑 + 物理限幅，输出为 LOS 向相对形变。
"""
import json
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds

PRODUCTS = Path("/mnt/data/hyf/aef_cesium/data/insar_hyp3/products")
OUT_DIR = Path("/mnt/data/hyf/aef_cesium/data/insar_hyp3")

# 绍兴靶区 EPSG:4326 网格（~80m 分辨率）
DST_BOUNDS = [120.30, 29.70, 121.10, 30.40]  # [left, bottom, right, top]
DST_RES = 0.0008  # ~89m
DST_CRS = "EPSG:4326"


def _dates_from_zipname(name):
    m = re.findall(r'_(\d{8})T', name)
    return (m[0], m[1]) if len(m) >= 2 else (None, None)


def _days_between(d1, d2):
    return abs((datetime.strptime(d2, "%Y%m%d") - datetime.strptime(d1, "%Y%m%d")).days)


def _read_from_zip(zf, suffix):
    member = [n for n in zf.namelist() if n.endswith(suffix) and not n.endswith('.xml')]
    if not member:
        return None, None, None, None
    tmp = tempfile.NamedTemporaryFile(suffix='.tif', delete=False)
    tmp.write(zf.read(member[0]))
    tmp.close()
    try:
        with rasterio.open(tmp.name) as src:
            arr = src.read(1).astype(np.float32)
            if src.nodata is not None:
                arr[arr == src.nodata] = np.nan
            crs = src.crs
            transform = src.transform
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    return arr, transform, crs, member[0].split('/')[-1]


def _box_smooth(arr, k=5):
    """简单均值平滑（降噪），忽略 NaN。"""
    from numpy.lib.stride_tricks import sliding_window_view
    h, w = arr.shape
    out = np.full_like(arr, np.nan)
    # 仅对有限值做均值（用卷积核更稳，此处用滑动窗口近似）
    pad = k // 2
    ap = np.pad(arr, pad, mode='constant', constant_values=np.nan)
    win = sliding_window_view(ap, (k, k))
    with np.errstate(invalid='ignore'):
        out = np.nanmean(win.reshape(h, w, k * k), axis=2)
    return out


def main():
    zips = sorted(PRODUCTS.glob('*.zip'))
    if not zips:
        print("❌ 未找到 ZIP，请先运行 ch9_poll_insar_shaoxing.py --download")
        return

    dst_w = int((DST_BOUNDS[2] - DST_BOUNDS[0]) / DST_RES) + 1
    dst_h = int((DST_BOUNDS[3] - DST_BOUNDS[1]) / DST_RES) + 1
    dst_transform = from_bounds(*DST_BOUNDS, width=dst_w, height=dst_h)

    vel_sum = None
    cor_sum = None
    w_sum = None
    n_used = 0

    for zpath in zips:
        d1, d2 = _dates_from_zipname(zpath.name)
        if not d1 or not d2:
            continue
        dt_yr = _days_between(d1, d2) / 365.25
        if dt_yr == 0:
            continue

        with zipfile.ZipFile(zpath) as zf:
            disp, disp_transform, crs, _ = _read_from_zip(zf, '_los_disp.tif')
            corr, corr_transform, crs2, _ = _read_from_zip(zf, '_corr.tif')
        if disp is None or corr is None or crs is None:
            continue

        # 重投影到统一 EPSG:4326 网格
        v_dst = np.full((dst_h, dst_w), np.nan, dtype=np.float32)
        c_dst = np.full((dst_h, dst_w), np.nan, dtype=np.float32)
        try:
            reproject(disp, v_dst, src_transform=disp_transform, src_crs=crs,
                      dst_transform=dst_transform, dst_crs=DST_CRS,
                      resampling=Resampling.bilinear)
            reproject(corr, c_dst, src_transform=corr_transform, src_crs=crs2 or crs,
                      dst_transform=dst_transform, dst_crs=DST_CRS,
                      resampling=Resampling.bilinear)
        except Exception as e:
            print(f"  ⚠️ {zpath.name} 重投影失败: {e}")
            continue

        vel = v_dst * 1000.0 / dt_yr  # mm/yr
        w = np.nan_to_num(c_dst, nan=0.0).clip(0.0, 1.0)
        vel = np.where(np.isfinite(vel), vel, np.nan)
        corr2 = np.where(np.isfinite(c_dst), c_dst, np.nan)
        # 相干性加权累加
        vw = np.nan_to_num(vel, nan=0.0) * w
        cw = np.nan_to_num(corr2, nan=0.0) * w
        if vel_sum is None:
            vel_sum, cor_sum, w_sum = vw, cw, w
        else:
            vel_sum += vw
            cor_sum += cw
            w_sum += w
        n_used += 1

    if n_used == 0:
        print("❌ 无有效干涉对。")
        return

    with np.errstate(invalid='ignore', divide='ignore'):
        velocity = np.where(w_sum > 0.01, vel_sum / w_sum, np.nan)
        coherence = np.where(w_sum > 0.01, cor_sum / w_sum, np.nan)

    # 空间平滑 + 物理限幅（LOS 年速率，mm/yr）
    velocity = _box_smooth(np.nan_to_num(velocity, nan=0.0), k=5)
    velocity = np.clip(velocity, -50.0, 50.0).astype(np.float32)
    coherence = np.nan_to_num(coherence, nan=0.0).astype(np.float32)

    meta = {
        "width": dst_w, "height": dst_h,
        "bounds": DST_BOUNDS,
        "crs": DST_CRS,
        "source": "ASF HyP3 INSAR_GAMMA (Sentinel-1 relativeOrbit 171)",
        "n_interferograms": n_used,
        "note": "LOS 向相对形变 (mm/yr)，未做 ERA5 大气校正，多对加权平均+平滑+限幅",
    }
    (OUT_DIR / "sx_velocity_real.raw").write_bytes(velocity.tobytes())
    (OUT_DIR / "sx_coherence_real.raw").write_bytes(coherence.tobytes())
    (OUT_DIR / "sx_raster_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    fin = np.isfinite(velocity)
    print(f"✅ 合成完成：{n_used} 个干涉对 → sx_* raw ({dst_w}x{dst_h})")
    print(f"   velocity 范围 {velocity[velocity != 0].min():.2f}~{velocity.max():.2f} mm/yr, "
          f"coherence 均值 {coherence.mean():.3f}")


if __name__ == "__main__":
    main()
