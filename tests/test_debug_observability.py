"""TDD: observability & debug endpoints.

These tests lock in the debugging contract used to locate 502/504 issues in
field deployments (public IP + dev-proxy or reverse proxy).
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a FastAPI test client for this repo's backend/main.py."""
    import sys
    from pathlib import Path
    import types

    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    # Keep tests fast/offline: stub out the heavy Earth Engine SDK.
    sys.modules.setdefault("ee", types.ModuleType("ee"))

    # Ensure we import the correct module in a shared pytest interpreter.
    sys.modules.pop("main", None)

    import main as main_module

    # Avoid real EE init during FastAPI startup.
    main_module.init_earth_engine = lambda: None
    main_module.gee_initialized = True
    return TestClient(main_module.app)


def test_health_includes_request_id_header(test_client: TestClient):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-AEF-Request-Id")


def test_debug_config_exists_and_is_safe(test_client: TestClient):
    resp = test_client.get("/api/debug/config")
    assert resp.status_code == 200
    payload = resp.json()

    assert "tile_proxy" in payload
    assert "counters" in payload

    # Basic shape checks (avoid leaking templates/tokens)
    assert "tile_registry" in payload["tile_proxy"]
    assert "tile_lru" in payload["tile_proxy"]


def test_debug_tile_unknown_id_returns_registered_false(test_client: TestClient):
    resp = test_client.get("/api/debug/tiles/ffffffffffffffffffffffff")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["tile_id"] == "ffffffffffffffffffffffff"
    assert payload["registered"] is False


def test_tiles_unknown_id_includes_debug_headers(test_client: TestClient):
    resp = test_client.get("/api/tiles/ffffffffffffffffffffffff/3/4/4")
    assert resp.status_code == 200
    assert resp.headers.get("X-AEF-Request-Id")
    # Default policy is transparent fallback
    assert resp.headers.get("X-AEF-Tile-Fallback") == "1"
    assert resp.headers.get("X-AEF-Tile-Reason")
    assert resp.headers.get("X-AEF-Tile-Cache") in ("FALLBACK", "HIT")


def test_debug_version_reports_runtime_env(test_client: TestClient):
    resp = test_client.get("/api/debug/version")
    assert resp.status_code == 200
    payload = resp.json()

    assert "python" in payload
    assert payload["python"].get("executable")
    assert "deps" in payload
    assert payload["deps"].get("httpx")
    # httpcore may be missing in some minimal envs, but in this repo it should exist.
    assert "backend" in payload
    assert payload["backend"].get("main_file")
