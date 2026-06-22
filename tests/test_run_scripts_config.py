from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def _run(script_name: str, env: dict[str, str] | None = None) -> str:
    script_path = REPO_ROOT / script_name
    assert script_path.exists(), f"Missing script: {script_path}"

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    proc = subprocess.run(
        [str(script_path), "--print-config"],
        cwd=str(REPO_ROOT),
        env=merged_env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.stdout


def test_backend_defaults_to_v6_profile_and_ports():
    out = _run("run_backend.sh", env={"ONEEARTH_PROFILE": "v6"})
    assert "ONEEARTH_PROFILE=v6" in out
    assert "API_PORT=8405" in out


def test_frontend_defaults_to_v6_profile_and_ports():
    out = _run("run_frontend.sh", env={"ONEEARTH_PROFILE": "v6"})
    assert "ONEEARTH_PROFILE=v6" in out
    assert "FRONTEND_PORT=8404" in out


def test_env_file_override_is_honored(tmp_path: Path):
    env_file = tmp_path / "custom.env"
    env_file.write_text(
        "API_HOST=127.0.0.1\nAPI_PORT=9999\nFRONTEND_PORT=9998\n",
        encoding="utf-8",
    )

    out_backend = _run(
        "run_backend.sh",
        env={"ONEEARTH_PROFILE": "v6", "ENV_FILE": str(env_file)},
    )
    assert f"ENV_PATH={env_file}" in out_backend
    assert "API_PORT=9999" in out_backend

    out_frontend = _run(
        "run_frontend.sh",
        env={"ONEEARTH_PROFILE": "v6", "ENV_FILE": str(env_file)},
    )
    assert f"ENV_PATH={env_file}" in out_frontend
    assert "FRONTEND_PORT=9998" in out_frontend


def test_v6_profile_forces_default_ports_on_dotenv_fallback(tmp_path: Path):
    """Regression: avoid accidental v5 port leakage from a generic .env.

    This situation commonly happens on servers that already have a v5 `.env`.
    Users then open :8504/:8505 but the scripts started on :8502/:8503, and a
    different service (often nginx) responds with 502.
    """

    dotenv_path = REPO_ROOT / ".env"
    had_existing = dotenv_path.exists()
    old_content = dotenv_path.read_text(encoding="utf-8") if had_existing else ""

    try:
        dotenv_path.write_text(
            "API_PORT=8503\nFRONTEND_PORT=8502\nGEE_USER_PATH=users/example/aef_demo\n",
            encoding="utf-8",
        )

        out_backend = _run("run_backend.sh", env={"ONEEARTH_PROFILE": "v6"})
        assert "ENV_SOURCE_KIND=fallback" in out_backend
        assert "API_PORT=8405" in out_backend

        out_frontend = _run("run_frontend.sh", env={"ONEEARTH_PROFILE": "v6"})
        assert "ENV_SOURCE_KIND=fallback" in out_frontend
        assert "FRONTEND_PORT=8404" in out_frontend
    finally:
        if had_existing:
            dotenv_path.write_text(old_content, encoding="utf-8")
        else:
            try:
                dotenv_path.unlink()
            except FileNotFoundError:
                pass
