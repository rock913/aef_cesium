"""TDD tests for V6 mission-driven narrative API.

V6 引入四章体 Missions（任务驱动）作为演示主线：
- 第一章 觉醒：余杭（欧氏距离）
- 第二章 护盾：塔拉滩（特定通道提取）
- 第三章 脉搏：咸海（余弦相似度）
- 第四章 共识：亚马逊（零样本聚类）

这些测试固定 `/api/missions` 的返回结构，确保前后端契约稳定。
"""

from __future__ import annotations

import sys
from pathlib import Path
import types

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

    import main as main_module  # noqa: WPS433 (test import)
    main_module.init_earth_engine = lambda: None
    main_module.gee_initialized = True
    return TestClient(main_module.app)


class TestMissionsEndpoint:
    def test_missions_endpoint_exists(self, client: TestClient):
        resp = client.get("/api/missions")
        assert resp.status_code == 200

    def test_missions_schema_and_references_are_valid(self, client: TestClient):
        # Load reference sets
        modes = client.get("/api/modes").json()
        locations = client.get("/api/locations").json()

        resp = client.get("/api/missions")
        assert resp.status_code == 200
        data = resp.json()

        assert isinstance(data, list)
        assert len(data) >= 6

        required_keys = {
            "id",
            "name",
            "api_mode",
            "location",
            "title",
            "narrative",
            "formula",
            "camera",
        }

        for m in data:
            assert isinstance(m, dict)
            assert required_keys.issubset(m.keys())

            assert isinstance(m["id"], str) and m["id"]
            assert isinstance(m["name"], str) and m["name"]
            assert isinstance(m["api_mode"], str) and m["api_mode"]
            assert isinstance(m["location"], str) and m["location"]

            assert m["api_mode"] in modes, f"Unknown api_mode: {m['api_mode']}"
            assert m["location"] in locations, f"Unknown location: {m['location']}"

            cam = m["camera"]
            assert isinstance(cam, dict)
            for k in ("lat", "lon", "height", "duration_s"):
                assert k in cam
            assert isinstance(cam["lat"], (int, float))
            assert isinstance(cam["lon"], (int, float))
            assert isinstance(cam["height"], (int, float))
            assert isinstance(cam["duration_s"], (int, float))

            # Optional camera orientation (forward-compatible)
            if "heading_deg" in cam:
                assert isinstance(cam["heading_deg"], (int, float))
            if "pitch_deg" in cam:
                assert isinstance(cam["pitch_deg"], (int, float))

    def test_missions_have_stable_order(self, client: TestClient):
        resp = client.get("/api/missions")
        ids = [m["id"] for m in resp.json()]

        assert ids[:6] == [
            "ch1_yuhang",
            "ch2_maowusu",
            "ch3_zhoukou",
            "ch4_amazon",
            "ch5_yancheng",
            "ch6_poyang",
        ]
