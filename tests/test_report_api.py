"""TDD tests for V6 report generation endpoint.

V6 roadmap:
- Feed zonal statistics JSON into LLM to generate a monitoring brief.
- Always include a deterministic template fallback (demo robustness).
- Template includes the mandatory "【共识印证】" section.
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

    import main as main_module  # noqa: WPS433
    main_module.init_earth_engine = lambda: None
    main_module.gee_initialized = True
    return TestClient(main_module.app)


class TestReportEndpoint:
    def test_report_rejects_unknown_mission(self, client: TestClient):
        resp = client.post(
            "/api/report",
            json={
                "mission_id": "unknown",
                "stats": {"total_area_km2": 100.0, "anomaly_pct": 12.4},
            },
        )
        assert resp.status_code == 400

    def test_report_template_fallback_works_without_gee(self, client: TestClient):
        resp = client.post(
            "/api/report",
            json={
                "mission_id": "ch1_yuhang",
                "stats": {
                    "total_area_km2": 8452.0,
                    "anomaly_area_km2": 1049.0,
                    "anomaly_pct": 12.4,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["mission_id"] == "ch1_yuhang"
        assert data["generated_by"] in ("template", "llm")
        assert isinstance(data["report"], str) and len(data["report"]) > 30
        assert "余杭" in data["report"]
        assert "12.4" in data["report"]
        assert "【共识印证】" in data["report"]

    def test_report_ch5_includes_esa_evidence_appendix(self, client: TestClient):
        resp = client.post(
            "/api/report",
            json={
                "mission_id": "ch5_yancheng",
                # Provide stats explicitly so the endpoint works offline.
                "stats": {
                    "total_area_km2": 1234.0,
                    "anomaly_area_km2": None,
                    "anomaly_pct": None,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mission_id"] == "ch5_yancheng"
        assert "ESA" in data["report"]
        assert "WorldCover" in data["report"]
        assert "JRC" in data["report"]
        assert "occurrence" in data["report"]
        assert "V8.1" in data["report"]
        assert "focal_mode" in data["report"]
        assert "img.updateMask(img.neq(3).And(img.neq(0)))" in data["report"]

    def test_report_uses_llm_when_configured(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        import main  # noqa: WPS433

        monkeypatch.setattr(main.settings, "llm_api_key", "test-key", raising=False)

        async def _fake_llm(**_kwargs):
            return "LLM 简报：建议核查异常区域并形成闭环。"

        monkeypatch.setattr(main, "generate_monitoring_brief_openai_compatible", _fake_llm)

        resp = client.post(
            "/api/report",
            json={
                "mission_id": "ch1_yuhang",
                "stats": {
                    "total_area_km2": 8452.0,
                    "anomaly_area_km2": 1049.0,
                    "anomaly_pct": 12.4,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["generated_by"] == "llm"
        assert "LLM 简报" in data["report"]

    def test_report_falls_back_to_template_on_llm_error(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        import main  # noqa: WPS433

        monkeypatch.setattr(main.settings, "llm_api_key", "test-key", raising=False)

        async def _fake_llm(**_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(main, "generate_monitoring_brief_openai_compatible", _fake_llm)

        resp = client.post(
            "/api/report",
            json={
                "mission_id": "ch1_yuhang",
                "stats": {
                    "total_area_km2": 8452.0,
                    "anomaly_area_km2": 1049.0,
                    "anomaly_pct": 12.4,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["generated_by"] == "template"
        assert "余杭" in data["report"]
        assert "【共识印证】" in data["report"]
