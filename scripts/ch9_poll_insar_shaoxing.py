#!/usr/bin/env python3
"""
CH9 绍兴真实 InSAR · HyP3 任务轮询 + 成果下载

读取 data/insar_hyp3/ch9_jobs.json，轮询 HyP3 任务状态；
对 SUCCEEDED 任务下载解缠相位 + 相干性 + LOS 位移 + DEM 到
data/insar_hyp3/products/，供后续合成速度场。

用法：
  EARTHDATA_USERNAME=xx EARTHDATA_PASSWORD=xx python3 scripts/ch9_poll_insar_shaoxing.py [--download]
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from hyp3_sdk import HyP3

JOBS_FILE = "/mnt/data/hyf/aef_cesium/data/insar_hyp3/ch9_jobs.json"
OUT_DIR = Path("/mnt/data/hyf/aef_cesium/data/insar_hyp3/products")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="下载 SUCCEEDED 任务的成果")
    args = ap.parse_args()

    username = os.getenv("EARTHDATA_USERNAME")
    password = os.getenv("EARTHDATA_PASSWORD")
    if not username or not password:
        print("❌ 需要 EARTHDATA_USERNAME / EARTHDATA_PASSWORD")
        sys.exit(1)

    jobs = json.loads(Path(JOBS_FILE).read_text(encoding="utf-8"))
    hyp3 = HyP3(username=username, password=password)

    status = Counter()
    succeeded = []
    for j in jobs:
        job = hyp3.get_job_by_id(j["job_id"])
        st = job.status_code
        status[st] += 1
        print(f"  {j['name']}: {st}")
        if st == "SUCCEEDED":
            succeeded.append((j, job))

    print(f"\n📊 状态汇总: {dict(status)}")

    if args.download and succeeded:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for j, job in succeeded:
            try:
                job.download_files(OUT_DIR)
                print(f"  ⬇️ {j['name']}")
            except Exception as e:
                print(f"  ❌ {j['name']} 下载失败: {e}")
        print(f"✅ 已下载 {len(succeeded)} 个任务成果 → {OUT_DIR}")
    elif not args.download:
        print("📌 加 --download 可在任务完成后下载成果。")


if __name__ == "__main__":
    main()
