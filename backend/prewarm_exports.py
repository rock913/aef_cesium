"""Prewarm export submitter for Alpha Earth Foundation (AEF).

Run this the night before a demo to solidify heavy GEE computations into Assets.
It submits `/api/cache/export` for the configured mission set.

Usage:
  python prewarm_exports.py
  python prewarm_exports.py --api-base http://127.0.0.1:8503 --sleep 2

Notes:
- This script only submits export tasks; monitor progress in the GEE Code Editor Tasks panel.
- It does not require importing/initializing Earth Engine locally.
"""

from __future__ import annotations

import argparse
import os
import time
from typing import List, Dict

import requests


def _default_tasks_from_settings() -> List[Dict[str, str]]:
    # Importing config loads `.env` but does not initialize GEE.
    from config import settings

    tasks: List[Dict[str, str]] = []
    for m in settings.missions:
        mode = m.get("api_mode")
        location = m.get("location")
        if not mode or not location:
            continue
        tasks.append({"mode": str(mode), "location": str(location), "mission_id": str(m.get("id", ""))})
    return tasks


def _parse_task(s: str) -> Dict[str, str]:
    # format: mode:location
    if ":" not in s:
        raise ValueError(f"Invalid task '{s}', expected mode:location")
    mode, location = s.split(":", 1)
    mode = mode.strip()
    location = location.strip()
    if not mode or not location:
        raise ValueError(f"Invalid task '{s}', expected mode:location")
    return {"mode": mode, "location": location}


def trigger_all_exports(api_base_url: str, tasks: List[Dict[str, str]], sleep_s: float) -> int:
    print("==================================================")
    print("🚀 AlphaEarth 全域缓存固化程序启动")
    print("==================================================")
    print(f"API: {api_base_url}")
    print(f"Tasks: {len(tasks)}")
    print("--------------------------------------------------")

    ok = 0
    for idx, task in enumerate(tasks, start=1):
        mode = task["mode"]
        loc = task["location"]
        mission_id = task.get("mission_id", "")
        label = f"{mission_id} " if mission_id else ""
        print(f"[{idx}/{len(tasks)}] 提交 -> {label}location={loc}, mode={mode}")

        try:
            r = requests.post(
                f"{api_base_url.rstrip('/')}/api/cache/export",
                json={"mode": mode, "location": loc},
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                ok += 1
                print("✅ 提交成功")
                print(f"   - task_id: {data.get('task_id')}")
                print(f"   - asset_id: {data.get('asset_id')}")
            else:
                print(f"❌ 提交失败: HTTP {r.status_code}")
                try:
                    print(f"   - detail: {r.json()}")
                except Exception:
                    print(f"   - body: {r.text[:500]}")
        except Exception as e:
            print(f"❌ 请求异常: {e}")

        time.sleep(max(0.0, sleep_s))

    print("==================================================")
    print(f"🎯 任务提交完毕：{ok}/{len(tasks)}")
    print("请前往 https://code.earthengine.google.com/ 的 Tasks 面板查看进度。")
    print("==================================================")
    return 0 if ok == len(tasks) else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit GEE export cache tasks via backend API")
    parser.add_argument(
        "--api-base",
        default=os.getenv("API_BASE_URL", "http://127.0.0.1:8503"),
        help="Backend base URL, default: http://127.0.0.1:8503",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=float(os.getenv("EXPORT_THROTTLE_S", "2")),
        help="Seconds to sleep between submissions (default: 2)",
    )
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help="Override tasks, repeatable. Format: mode:location",
    )

    args = parser.parse_args()

    if args.task:
        tasks = [_parse_task(s) for s in args.task]
    else:
        tasks = _default_tasks_from_settings()

    if not tasks:
        print("No tasks found.")
        return 2

    return trigger_all_exports(args.api_base, tasks, args.sleep)


if __name__ == "__main__":
    raise SystemExit(main())
