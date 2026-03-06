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
    assert len(data) >= 15
    ids = {p.get("id") for p in data}
    assert "demo:amazon_cluster" in ids
    assert "demo:global_wind_glsl" in ids
    assert "demo:wormhole_micro" in ids
    assert "demo:terminator_shield" in ids


def test_v7_tools_list() -> None:
    client = _client()
    r = client.get("/api/v7/tools")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    names = {t.get("name") for t in data}
    assert "camera_fly_to" in names
    assert "fly_to" in names
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

    # Phase 3 visualization tools (MVR)
    assert "enable_3d_terrain" in names
    assert "add_cesium_3d_tiles" in names
    assert "apply_custom_shader" in names
    assert "generate_cesium_custom_shader" in names
    assert "add_cesium_extruded_polygons" in names
    assert "set_scene_mode" in names
    assert "play_czml_animation" in names
    assert "set_globe_transparency" in names
    assert "add_subsurface_model" in names
    assert "trigger_gsap_wormhole" in names
    assert "show_terminator_shield" in names
    assert "spin_macro_camera" in names


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


def test_v7_demo7_everest_emits_terrain_and_3dtiles() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "珠峰 冰川湖 GLOF"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "enable_3d_terrain" in tools
    assert "add_cesium_3d_tiles" in tools


def test_v7_demo11_malacca_emits_night_and_czml() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "马六甲 油污 AIS"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "set_scene_mode" in tools
    assert "play_czml_animation" in tools


def test_v7_demo14_wormhole_emits_transition_and_micro() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "虫洞 micro SiO2"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "trigger_gsap_wormhole" in tools
    assert "switch_scale" in tools
    assert "generate_molecular_lattice" in tools


def test_v7_demo15_terminator_shield_emits_macro_tools() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 15 terminator shield magnetosphere"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "switch_scale" in tools
    assert "show_terminator_shield" in tools
    assert "spin_macro_camera" in tools
