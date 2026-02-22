"""TDD tests for V6 agent analysis endpoint.

Roadmap:
- Provide an /api/analyze endpoint for the right-side "analysis console".
- Use Qwen (OpenAI-compatible) when configured.
- Always provide a deterministic template fallback for demo robustness.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    from main import app  # noqa: WPS433

    return TestClient(app)


class TestAnalyzeEndpoint:
    def test_analyze_rejects_unknown_mission(self, client: TestClient):
        resp = client.post(
            "/api/analyze",
            json={
                "mission_id": "unknown",
                "stats": {"total_area_km2": 100.0, "anomaly_pct": 12.4},
            },
        )
        assert resp.status_code == 400

    def test_analyze_template_fallback_works_without_gee(self, client: TestClient):
        resp = client.post(
            "/api/analyze",
            json={
                "mission_id": "ch2_maowusu",
                "stats": {
                    "total_area_km2": 8452.0,
                    "anomaly_area_km2": 1049.0,
                    "anomaly_pct": 12.4,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["mission_id"] == "ch2_maowusu"
        assert data["generated_by"] in ("template", "llm")
        assert isinstance(data["analysis"], str) and len(data["analysis"]) > 60
        assert "【异动感知" in data["analysis"]
        assert "【行动规划" in data["analysis"]
        assert "【共识印证" in data["analysis"]

    def test_analyze_uses_llm_when_configured(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        import main  # noqa: WPS433

        monkeypatch.setattr(main.settings, "llm_api_key", "test-key", raising=False)

        async def _fake_llm(**_kwargs):
            return "【异动感知 Observation】\n- LLM 分析示例\n\n【行动规划 Plan】\n- 步骤1\n\n【共识印证 Consensus】\n- 证据锚点\n"

        monkeypatch.setattr(main, "generate_agent_analysis_openai_compatible", _fake_llm)

        resp = client.post(
            "/api/analyze",
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
        assert "LLM 分析示例" in data["analysis"]

    def test_analyze_falls_back_to_template_on_llm_error(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        import main  # noqa: WPS433

        monkeypatch.setattr(main.settings, "llm_api_key", "test-key", raising=False)

        async def _fake_llm(**_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(main, "generate_agent_analysis_openai_compatible", _fake_llm)

        resp = client.post(
            "/api/analyze",
            json={
                "mission_id": "ch4_amazon",
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
        assert "【共识印证" in data["analysis"]
