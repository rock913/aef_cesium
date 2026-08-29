#!/usr/bin/env python3
"""
AlphaEarth CH8: 自动轮询 HyP3 任务、下载解缠成果并合成真实 InSAR 速率场
"""
import os
import sys
import glob
import zipfile
import shutil
import time
from pathlib import Path
import numpy as np

def run():
    from hyp3_sdk import HyP3

    username = os.getenv("EARTHDATA_USERNAME", "rocky913")
    password = os.getenv("EARTHDATA_PASSWORD", "%d7uUZykd&Mk^Ck")
    output_dir = Path("/app/data/insar_hyp3")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to HyP3 as {username}...")
    hyp3 = HyP3(username=username, password=password)

    jobs = hyp3.find_jobs()
    print(f"Total jobs found: {len(jobs)}")

    status_counts = {}
    for j in jobs:
        st = j.status_code
        status_counts[st] = status_counts.get(st, 0) + 1
    print(f"Current Status: {status_counts}")

    # Check if any job is complete
    succeeded_jobs = [j for j in jobs if j.succeeded()]
    print(f"Succeeded jobs: {len(succeeded_jobs)} / {len(jobs)}")

    if not succeeded_jobs:
        print("⏳ All jobs are currently pending/running in ASF cloud. Please wait...")
        return False

    print(f"Downloading {len(succeeded_jobs)} completed InSAR products to {output_dir}...")
    for j in succeeded_jobs:
        try:
            print(f"Downloading job {j.job_id}...")
            j.download_files(output_dir)
        except Exception as e:
            print(f"Download error for {j.job_id}: {e}")

    # Unzip all downloaded zips
    zips = list(output_dir.glob("*.zip"))
    print(f"Extracting {len(zips)} zip files...")
    extracted_dirs = []
    for z in zips:
        dest = output_dir / z.stem
        if not dest.exists():
            with zipfile.ZipFile(z, 'r') as zip_ref:
                zip_ref.extractall(dest)
        extracted_dirs.append(dest)

    print("✅ Finished extraction!")
    return True

if __name__ == "__main__":
    run()
