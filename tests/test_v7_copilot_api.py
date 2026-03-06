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
    assert len(data) >= 14
    ids = {p.get("id") for p in data}
    assert "demo:amazon_cluster" in ids
    assert "demo:global_wind_glsl" in ids
    assert "demo:wormhole_micro" in ids


def test_v7_tools_list() -> None:
    client = _client()
    r = client.get("/api/v7/tools")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    names = {t.get("name") for t in data}
    assert "camera_fly_to" in names
    assert "switch_scale" in names
    # v7.1 UI-oriented tools
    assert "write_to_editor" in names
    assert "execute_editor_code" in names
    assert "generate_report" in names
    # Phase 1 artifacts tools
    assert "add_cesium_imagery" in names
    assert "add_cesium_vector" in names
    assert "show_chart" in names
    assert "render_bivariate_map" in names


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


def test_v7_execute_code_gen_demo_writes_editor() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "用 GLSL 写 GFS 全球风场渲染代码"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    assert any(e.get("type") == "tool_call" and e.get("tool") == "write_to_editor" for e in events)


def _event_tools(events: list[dict]) -> list[str | None]:
    return [e.get("tool") for e in events if e.get("type") == "tool_call"]


def test_v7_demo1_yuhang_emits_imagery_and_report() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 1 余杭 城建 审计"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "add_cesium_imagery" in tools
    assert "generate_report" in tools


def test_v7_demo2_amazon_emits_vector_and_report() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 2 亚马逊 零样本聚类 k=6"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "add_cesium_vector" in tools
    assert "generate_report" in tools


def test_v7_demo3_maowusu_emits_imagery_and_report() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 3 毛乌素 余弦 相似度"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "add_cesium_imagery" in tools
    assert "generate_report" in tools


def test_v7_poyang_emits_imagery_and_report() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "鄱阳湖 水网 脉动 2024 vs 2022"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "add_cesium_imagery" in tools
    assert "generate_report" in tools


def test_v7_nyc_emits_charts_tools() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "纽约 热岛 Pearson correlation income"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "show_chart" in tools
    assert "render_bivariate_map" in tools
