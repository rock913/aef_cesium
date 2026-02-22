from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent


def _run_bash(cmd: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env={**os.environ, **env},
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def _parse_kv(output: str) -> dict[str, str]:
    kv: dict[str, str] = {}
    for line in output.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            if k and v is not None:
                kv[k] = v
    return kv


def test_run_backend_print_config_respects_env_file(tmp_path: Path):
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "API_HOST=0.0.0.0\nAPI_PORT=19999\n",
        encoding="utf-8",
    )

    out = _run_bash(
        ["bash", "./run_backend.sh", "--print-config"],
        {"ONEEARTH_PROFILE": "v6", "ENV_FILE": str(env_file)},
    )
    kv = _parse_kv(out)

    assert kv.get("ONEEARTH_PROFILE") == "v6"
    assert kv.get("API_HOST") == "0.0.0.0"
    assert kv.get("API_PORT") == "19999"


def test_run_frontend_print_config_respects_env_file(tmp_path: Path):
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "FRONTEND_PORT=18888\n",
        encoding="utf-8",
    )

    out = _run_bash(
        ["bash", "./run_frontend.sh", "--print-config"],
        {"ONEEARTH_PROFILE": "v6", "ENV_FILE": str(env_file)},
    )
    kv = _parse_kv(out)

    assert kv.get("ONEEARTH_PROFILE") == "v6"
    assert kv.get("FRONTEND_PORT") == "18888"


def test_start_sh_is_not_hardcoded_to_legacy_ports():
    content = (REPO_ROOT / "start.sh").read_text(encoding="utf-8")

    # start.sh should not hardcode specific ports; it must derive them via
    # run_backend.sh/run_frontend.sh --print-config.
    assert "8502" not in content
    assert "8503" not in content
