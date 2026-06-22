"""TDD tests for V6 Dynamic Zonal Statistics API.

Whitepaper requirement:
- Replace HUD mockStats with real GEE reduceRegion results.

We keep these tests unit-level by mocking the expensive GEE calls.
"""

from __future__ import annotations

import sys
from pathlib import Path
import types
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    # Keep unit tests offline/fast.
    if "ee" not in sys.modules:
        fake_ee = types.ModuleType("ee")
        fake_ee.Geometry = types.SimpleNamespace(Point=lambda *a, **k: None)
        sys.modules["ee"] = fake_ee

    sys.modules.pop("main", None)

    import main as main_module  # noqa: WPS433
    main_module.init_earth_engine = lambda: None
    main_module.gee_initialized = True
    return TestClient(main_module.app)


class TestStatsEndpoint:
    def test_stats_rejects_invalid_mode(self, client: TestClient):
        resp = client.post("/api/stats", json={"mode": "nope", "location": "yuhang"})
        assert resp.status_code == 400

    def test_stats_rejects_invalid_location(self, client: TestClient):
        resp = client.post("/api/stats", json={"mode": "ch1_yuhang_faceid", "location": "nope"})
        assert resp.status_code == 400

    @patch("main.ee.Geometry.Point")
    @patch("main.get_layer_logic")
    @patch("main.compute_zonal_stats")
    def test_stats_happy_path(
        self,
        mock_compute: Mock,
        mock_get_layer_logic: Mock,
        mock_point: Mock,
        client: TestClient,
    ):
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_img = Mock()
        mock_get_layer_logic.return_value = (mock_img, {"min": 0, "max": 1}, "ch1_faceid")

        mock_compute.return_value = {
            "total_area_km2": 100.0,
            "anomaly_area_km2": 12.4,
            "anomaly_pct": 12.4,
        }

        resp = client.post("/api/stats", json={"mode": "ch2_maowusu_shield", "location": "yuhang"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["mode"] == "ch2_maowusu_shield"
        assert data["location"] == "yuhang"
        assert "stats" in data
        assert data["stats"]["total_area_km2"] == 100.0
        assert data["stats"]["anomaly_pct"] == 12.4

        mock_compute.assert_called_once()

    def test_stats_requires_json_body(self, client: TestClient):
        resp = client.post("/api/stats")
        assert resp.status_code in (400, 422)
