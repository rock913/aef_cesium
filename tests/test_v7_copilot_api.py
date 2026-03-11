from __future__ import annotations

import os
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
    assert len(data) >= 13
    ids = {p.get("id") for p in data}
    assert "demo:amazon_cluster" in ids
    assert "demo:webgpu_particles_wgsl" in ids
    assert "demo:wormhole_micro" in ids
    assert "demo:global_wind_glsl" not in ids


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
    assert "add_cesium_water_polygon" in names
    assert "set_scene_mode" in names
    assert "play_czml_animation" in names
    assert "set_globe_transparency" in names
    assert "add_subsurface_model" in names
    assert "trigger_gsap_wormhole" in names

    # v7.2 twin spatial mode tools
    assert "enable_swipe_mode" in names
    assert "set_swipe_position" in names
    assert "disable_swipe_mode" in names

    # v7.2 WebGPU / subsurface demo tools
    assert "enable_subsurface_mode" in names
    assert "disable_subsurface_mode" in names
    assert "execute_dynamic_wgsl" in names
    assert "destroy_webgpu_sandbox" in names


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
    # WGSL-first wind demo should also attempt to execute via WebGPU overlay.
    assert any(e.get("type") == "tool_call" and e.get("tool") == "execute_dynamic_wgsl" for e in events)


def test_v7_execute_webgpu_demo_emits_wgsl_tool_calls() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 13 WebGPU WGSL 粒子沙盒"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "fly_to" in tools
    assert "write_to_editor" in tools
    assert "execute_dynamic_wgsl" in tools


def test_v7_execute_pilbara_emits_subsurface_and_anchor() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "皮尔巴拉 地下 矿脉 解译"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "enable_subsurface_mode" in tools
    assert "fly_to" in tools
    assert "add_subsurface_model" in tools


def test_v7_execute_demo6_talatan_emits_extruded_and_chart() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 6 塔拉滩 光伏 面积"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "add_cesium_extruded_polygons" in tools
    assert "show_chart" in tools


def test_v7_execute_demo7_everest_emits_terrain_tiles_and_water() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 7 珠峰 冰川湖 溃决 预警"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "enable_3d_terrain" in tools
    assert "add_cesium_3d_tiles" in tools
    assert "add_cesium_water_polygon" in tools


def test_v7_execute_demo8_mauna_loa_emits_custom_shader_chain() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 8 冒纳罗亚 火山 InSAR 形变 热异常"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "fetch_insar_displacement" in tools
    assert "fetch_lst_anomaly" in tools
    assert "apply_custom_shader" in tools
    assert "generate_cesium_custom_shader" in tools


def test_v7_execute_demo9_congo_emits_extruded_and_chart() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 9 刚果 碳汇 三维 估算"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "estimate_carbon_stock" in tools
    assert "add_cesium_extruded_polygons" in tools
    assert "show_chart" in tools


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
    # v7.2: Demo 1 may auto-enter swipe compare mode
    assert "enable_swipe_mode" in tools


def test_v7_demo2_amazon_emits_vector_and_report() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 2 亚马逊 零样本聚类 k=6"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "add_cesium_vector" in tools
    assert "generate_report" in tools


def test_v7_hybrid_router_flag_safe_without_key() -> None:
    client = _client()
    old = os.environ.get("V7_HYBRID_ROUTER")
    os.environ["V7_HYBRID_ROUTER"] = "1"
    try:
        r = client.post("/api/v7/copilot/execute", json={"prompt": "Demo 1 余杭 城建 审计"})
        assert r.status_code == 200
        events = (r.json() or {}).get("events")
        assert isinstance(events, list)
        assert any(e.get("type") == "final" for e in events)
    finally:
        if old is None:
            os.environ.pop("V7_HYBRID_ROUTER", None)
        else:
            os.environ["V7_HYBRID_ROUTER"] = old


def test_v7_hybrid_router_unknown_prompt_safe_without_key() -> None:
    client = _client()
    old = os.environ.get("V7_HYBRID_ROUTER")
    os.environ["V7_HYBRID_ROUTER"] = "1"
    try:
        r = client.post("/api/v7/copilot/execute", json={"prompt": "帮我对比一下这两年的变化"})
        assert r.status_code == 200
        events = (r.json() or {}).get("events")
        assert isinstance(events, list)
        assert any(e.get("type") == "final" for e in events)
    finally:
        if old is None:
            os.environ.pop("V7_HYBRID_ROUTER", None)
        else:
            os.environ["V7_HYBRID_ROUTER"] = old


def test_v7_hybrid_router_explore_filters_tool_calls_offline() -> None:
    old_flag = os.environ.get("V7_HYBRID_ROUTER")
    old_key = os.environ.get("LLM_API_KEY")
    os.environ["V7_HYBRID_ROUTER"] = "1"
    os.environ["LLM_API_KEY"] = "test-key"

    try:
        # Create a fresh client so backend/config picks up LLM_API_KEY.
        backend_path = Path(__file__).parent.parent / "backend"
        sys.path.insert(0, str(backend_path))
        if "ee" not in sys.modules:
            fake_ee = types.ModuleType("ee")
            fake_ee.Geometry = types.SimpleNamespace(Point=lambda *a, **k: None)
            sys.modules["ee"] = fake_ee
        for m in ["main", "config", "v7_copilot", "llm_service"]:
            sys.modules.pop(m, None)
        import main as main_module  # noqa: WPS433

        client = TestClient(main_module.app)

        import llm_service  # noqa: WPS433

        async def _fake_plan_tool_calls_openai_compatible(**_kwargs):
            return {
                "content": "mock-plan",
                "tool_calls": [
                    {
                        "name": "enable_swipe_mode",
                        "arguments": '{"left_layer_id":"gee-heatmap","right_layer_id":"anomaly-mask","position":0.25,"evil":1}',
                    },
                    {"name": "delete_all", "arguments": "{}"},
                    {
                        "name": "camera_fly_to",
                        "arguments": '{"lat":10,"lon":20,"height":1000,"duration_s":1.0,"oops":"x"}',
                    },
                ],
            }

        llm_service.plan_tool_calls_openai_compatible = _fake_plan_tool_calls_openai_compatible

        r = client.post("/api/v7/copilot/execute", json={"prompt": "随便探索一下，不要命中 Demo"})
        assert r.status_code == 200
        events = (r.json() or {}).get("events")
        assert isinstance(events, list)

        tools = _event_tools(events)
        assert "enable_swipe_mode" in tools
        assert "camera_fly_to" in tools
        assert "delete_all" not in tools

        swipe_calls = [e for e in events if e.get("type") == "tool_call" and e.get("tool") == "enable_swipe_mode"]
        assert len(swipe_calls) == 1
        swipe_args = swipe_calls[0].get("args")
        assert isinstance(swipe_args, dict)
        assert swipe_args.get("left_layer_id") == "gee-heatmap"
        assert swipe_args.get("right_layer_id") == "anomaly-mask"
        assert "evil" not in swipe_args

        fly_calls = [e for e in events if e.get("type") == "tool_call" and e.get("tool") == "camera_fly_to"]
        assert len(fly_calls) == 1
        fly_args = fly_calls[0].get("args")
        assert isinstance(fly_args, dict)
        assert fly_args.get("lat") == 10
        assert fly_args.get("lon") == 20
        assert "oops" not in fly_args

        assert any(e.get("type") == "final" for e in events)
    finally:
        if old_flag is None:
            os.environ.pop("V7_HYBRID_ROUTER", None)
        else:
            os.environ["V7_HYBRID_ROUTER"] = old_flag
        if old_key is None:
            os.environ.pop("LLM_API_KEY", None)
        else:
            os.environ["LLM_API_KEY"] = old_key


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

    calls = [e for e in events if e.get("type") == "tool_call" and e.get("tool") == "render_bivariate_map"]
    assert calls, "expected render_bivariate_map tool_call"
    args = calls[0].get("args")
    assert isinstance(args, dict)
    data = args.get("data")
    assert isinstance(data, dict)
    grid = data.get("grid")
    assert isinstance(grid, list)
    assert len(grid) > 0
    bounds = data.get("bounds")
    assert isinstance(bounds, dict)
    for k in ["west", "east", "south", "north"]:
        assert k in bounds
    dims = data.get("dims")
    assert isinstance(dims, dict)
    assert int(dims.get("cols")) > 0
    assert int(dims.get("rows")) > 0


def test_v7_demo6_talatan_emits_vector_extruded_and_chart() -> None:
    client = _client()
    r = client.post("/api/v7/copilot/execute", json={"prompt": "塔拉滩 光伏 共现"})
    assert r.status_code == 200
    events = (r.json() or {}).get("events")
    assert isinstance(events, list)
    tools = _event_tools(events)
    assert "add_cesium_vector" in tools
    assert "add_cesium_extruded_polygons" in tools
    assert "show_chart" in tools

    extruded_calls = [e for e in events if e.get("type") == "tool_call" and e.get("tool") == "add_cesium_extruded_polygons"]
    assert extruded_calls
    args = extruded_calls[0].get("args")
    assert isinstance(args, dict)
    geojson = args.get("geojson")
    assert isinstance(geojson, dict)
    feats = geojson.get("features")
    assert isinstance(feats, list)
    assert len(feats) >= 1


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
    assert "add_cesium_vector" in tools

    czml_calls = [e for e in events if e.get("type") == "tool_call" and e.get("tool") == "play_czml_animation"]
    assert czml_calls
    args = czml_calls[0].get("args")
    assert isinstance(args, dict)
    czml = args.get("czml")
    assert isinstance(czml, list)
    assert len(czml) >= 2


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
