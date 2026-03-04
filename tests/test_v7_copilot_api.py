from __future__ import annotations

import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient


def _client() -> TestClient:
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    # Keep unit tests offline/fast.
    if "ee" not in sys.modules:
        fake_ee = types.ModuleType("ee")
        fake_ee.Geometry = types.SimpleNamespace(Point=lambda *a, **k: None)
        sys.modules["ee"] = fake_ee

    sys.modules.pop("main", None)
    import main as main_module  # noqa: WPS433
    return TestClient(main_module.app)


def test_v7_prompts_list() -> None:
    client = _client()
    r = client.get("/api/v7/prompts")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(p.get("id") == "demo:amazon_cluster" for p in data)


def test_v7_tools_list() -> None:
    client = _client()
    r = client.get("/api/v7/tools")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    names = {t.get("name") for t in data}
    assert "camera_fly_to" in names
    assert "switch_scale" in names


def test_v7_execute_returns_events() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "亚马逊 零样本聚类 k=6"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    events = data.get("events")
    assert isinstance(events, list)
    assert any(e.get("type") == "tool_call" for e in events)
    assert any(e.get("tool") == "aef_kmeans_cluster" for e in events)
