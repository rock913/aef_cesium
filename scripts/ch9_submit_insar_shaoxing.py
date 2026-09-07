#!/usr/bin/env python3
"""
CH9 绍兴真实 InSAR · HyP3 任务提交（OAuth2 via hyp3_sdk）

提交 INSAR_GAMMA 小基线干涉对任务，生成真实解缠相位/相干性/LOS 位移。
产出任务清单 data/insar_hyp3/ch9_jobs.json，供后续轮询+下载+合成速度场。

用法：
  EARTHDATA_USERNAME=xx EARTHDATA_PASSWORD=xx python3 scripts/ch9_submit_insar_shaoxing.py
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

from hyp3_sdk import HyP3

ASF_SEARCH = "https://api.daac.asf.alaska.edu/services/search/param"
AOI_BBOX = [120.2, 29.7, 121.1, 30.4]
RELATIVE_ORBIT = 171
FRAME = 96
# 每 step 景取 1 景作参考 → ~24 天基线（step=2）跨全年
STEP = 2


def search_granules():
    url = (
        f"{ASF_SEARCH}?platform=Sentinel-1&processingLevel=SLC"
        f"&bbox={AOI_BBOX[0]},{AOI_BBOX[1]},{AOI_BBOX[2]},{AOI_BBOX[3]}"
        f"&start=2023-01-01&end=2024-06-01&output=json"
    )
    with urllib.request.urlopen(url, timeout=90) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    items = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], list) else raw
    out = []
    for g in items:
        if str(g.get("relativeOrbit")) == str(RELATIVE_ORBIT) and str(g.get("frameNumber")) == str(FRAME):
            out.append((g.get("startTime", "")[:10], g.get("granuleName")))
    out.sort()
    return [n for _, n in out]


def main():
    username = os.getenv("EARTHDATA_USERNAME")
    password = os.getenv("EARTHDATA_PASSWORD")
    if not username or not password:
        print("❌ 需要 EARTHDATA_USERNAME / EARTHDATA_PASSWORD")
        sys.exit(1)

    hyp3 = HyP3(username=username, password=password)
    try:
        credits = hyp3.check_credits()
        print(f"✅ HyP3 已连接，剩余 credits: {credits}")
    except Exception as e:
        print(f"⚠️ credits 查询失败（忽略）: {e}")

    granules = search_granules()
    print(f"✅ 检索到 {len(granules)} 景 SLC (relativeOrbit {RELATIVE_ORBIT}, frame {FRAME})")

    refs = granules[::STEP]
    pairs = [(refs[i], refs[i + 1]) for i in range(len(refs) - 1)]
    print(f"📌 将提交 {len(pairs)} 个 INSAR_GAMMA 干涉对（~{12*STEP} 天基线）")

    submitted = []
    for i, (ref, sec) in enumerate(pairs):
        name = f"ch9-shaoxing-{i:03d}"
        try:
            batch = hyp3.submit_insar_job(
                ref, sec,
                name=name,
                looks="20x4",
                include_los_displacement=True,
                include_inc_map=False,
                include_dem=True,
                apply_water_mask=True,
            )
            jid = batch.jobs[0].job_id if getattr(batch, "jobs", None) else batch.job_id
            submitted.append({"name": name, "job_id": jid, "reference": ref, "secondary": sec})
            print(f"  ✅ {name}: {jid}  ({ref[:20]} × {sec[:20]})")
        except Exception as e:
            print(f"  ❌ {name} 提交失败: {e}")

    out = Path("/mnt/data/hyf/aef_cesium/data/insar_hyp3/ch9_jobs.json")
    out.write_text(json.dumps(submitted, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 已提交 {len(submitted)} 个任务 → {out}")
    print("📌 任务云端处理约 15~30 分钟/个（并行），稍后用 ch9_poll_insar_shaoxing.py 轮询下载。")


if __name__ == "__main__":
    main()
