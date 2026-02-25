from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_and_main():
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))
    sys.modules.pop("main", None)

    import main as main_module  # noqa: WPS433 (test import)

    return TestClient(main_module.app), main_module


def test_debug_gee_endpoint_exposes_state(client_and_main):
    client, main = client_and_main

    main.gee_initialized = False
    resp = client.get("/api/debug/gee")
    assert resp.status_code == 200
    data = resp.json()

    assert "gee_initialized" in data
    assert "init_in_progress" in data
    assert "last_error" in data
    assert "init_timeout_s" in data
