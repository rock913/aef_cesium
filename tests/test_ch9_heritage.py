"""Tests for CH9: 古建筑天地一体预防性保护数字孪生系统."""

import pytest
import os
import sys
from urllib.parse import quote

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')


def _import_config():
    sys.path.insert(0, BACKEND_DIR)
    from config import settings
    return settings


# --- Mode / location / mission registration (no GEE) ---

def test_ch9_modes_registered():
    settings = _import_config()
    for m in ("ch9_heritage_deformation", "ch9_heritage_wind_risk",
              "ch9_heritage_aef_discovery", "ch9_heritage_change"):
        assert m in settings.modes


def test_ch9_locations_registered():
    settings = _import_config()
    assert settings.locations["dongyang_luzhai"]["coords"] == [29.2832, 120.2410, 16]
    assert settings.locations["shaoxing_yuecheng"]["coords"] == [30.0023, 120.5810, 14]
    assert settings.locations["shanxi_pingyao"]["coords"] == [37.2010, 112.1750, 13]


def test_ch9_missions_registered():
    settings = _import_config()
    ids = {m["id"] for m in settings.missions}
    assert "卢宅风险" in ids
    assert "越城体检" in ids
    assert "跨省发现" in ids

    wind = next(m for m in settings.missions if m["id"] == "卢宅风险")
    assert wind["api_mode"] == "ch9_heritage_wind_risk"
    assert wind["location"] == "dongyang_luzhai"
    assert wind["chapter"] == "CH9"

    deform = next(m for m in settings.missions if m["id"] == "越城体检")
    assert deform["api_mode"] == "ch9_heritage_deformation"
    assert deform["location"] == "shaoxing_yuecheng"


def test_ch9_viewport_buffer():
    settings = _import_config()
    assert settings.get_viewport_buffer_m_for_mode("ch9_heritage_deformation") == 60000
    assert settings.get_viewport_buffer_m_for_mode("ch9_heritage_wind_risk") == 30000


# --- GEE stub tests (vis/suffix, no real EE) ---

def test_ch9_get_mode_vis_and_suffix_stub():
    with patch.dict(os.environ, {"PYTEST_STUB_EE": "1"}):
        sys.path.insert(0, BACKEND_DIR)
        from gee_service import get_mode_vis_and_suffix

        vis, suffix = get_mode_vis_and_suffix("ch9_heritage_deformation")
        assert suffix == "ch9_heritage_deformation"
        assert vis["min"] == -20 and vis["max"] == 6
        assert vis.get("format") == "png"

        vis2, suffix2 = get_mode_vis_and_suffix("ch9_heritage_wind_risk")
        assert suffix2 == "ch9_heritage_wind_risk"

        vis3, suffix3 = get_mode_vis_and_suffix("ch9_heritage_aef_discovery")
        assert suffix3 == "ch9_heritage_aef_discovery"

        vis4, suffix4 = get_mode_vis_and_suffix("ch9_heritage_change")
        assert suffix4 == "ch9_heritage_change"


def test_ch9_deformation_not_colliding_with_ch8():
    """ch9_heritage_deformation 含 '形变'/'insar' 字样，但必须命中 CH9 而非 CH8。"""
    with patch.dict(os.environ, {"PYTEST_STUB_EE": "1"}):
        sys.path.insert(0, BACKEND_DIR)
        from gee_service import get_mode_vis_and_suffix
        mode_str = "ch9_heritage_deformation 古建单体形变体检 (SBAS-InSAR + 五指标归因)"
        _vis, suffix = get_mode_vis_and_suffix(mode_str)
        assert suffix == "ch9_heritage_deformation"


# --- API endpoint tests ---

def test_ch9_locations_endpoint(client):
    resp = client.get("/api/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert "shaoxing_yuecheng" in data
    assert data["shaoxing_yuecheng"]["name"] == "绍兴 · 越城历史城区"


def test_ch9_modes_endpoint(client):
    resp = client.get("/api/modes")
    assert resp.status_code == 200
    data = resp.json()
    assert "ch9_heritage_deformation" in data


def test_ch9_missions_endpoint(client):
    resp = client.get("/api/missions")
    assert resp.status_code == 200
    ids = {m["id"] for m in resp.json()}
    assert {"卢宅风险", "越城体检", "跨省发现"} <= ids


from unittest.mock import Mock, patch


@patch('main.ee.Geometry.Point')
@patch('main.smart_load')
@patch('main.get_tile_url')
def test_ch9_layers_endpoint(mock_get_tile, mock_smart_load, mock_point, client):
    mock_viewport = Mock()
    mock_point.return_value.buffer.return_value = mock_viewport
    mock_viewport.bounds.return_value = mock_viewport

    mock_image = Mock()
    mock_vis = {'min': -20, 'max': 6, 'format': 'png'}
    mock_smart_load.return_value = (mock_image, mock_vis, "cached", True, "asset_id", mock_image)
    mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/{z}/{x}/{y}"

    resp = client.get("/api/layers?mode=ch9_heritage_deformation&location=shaoxing_yuecheng")
    assert resp.status_code == 200
    data = resp.json()
    assert "tile_url" in data
    assert data.get("mode") == "ch9_heritage_deformation"
    assert data["render_hints"]["ai_opacity"] == 0.88


# --- CH9 heritage endpoints (pure Python, no GEE) ---

def test_heritage_buildings_list(client):
    resp = client.get("/api/heritage/buildings/shaoxing_yuecheng")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["count"] >= 5
    names = {b["name"] for b in data["buildings"]}
    assert "恒济台门" in names


def test_heritage_buildings_invalid_location(client):
    resp = client.get("/api/heritage/buildings/does_not_exist")
    assert resp.status_code == 400


def test_heritage_building_detail(client):
    resp = client.get("/api/heritage/building/SX-YC-ZP-08")
    assert resp.status_code == 200
    b = resp.json()
    assert b["name"] == "恒济台门"
    assert b["layers"]["L3_deformation"]["risk_level"] == "unstable"
    assert b["layers"]["L3_deformation"]["beta_ratio"] == "1/280"
    assert b["layers"]["L4_defect"]["image"] == "072500002AAaa.jpg"
    assert b["layers"]["L5_structural"]["fea_panorama"] == "FEA云图_全景.png"
    assert b["fusion"]["coupled_risk_level"] == "Ⅲ（优先处置）"
    assert b["data_track"] == "demo_sandbox"


def test_heritage_building_not_found(client):
    resp = client.get("/api/heritage/building/NOPE")
    assert resp.status_code == 404


def test_heritage_wind_assessment(client):
    resp = client.post(
        "/api/heritage/wind_assessment",
        json={"building_ids": ["JH-DY-LZ-001"], "typhoon": {"name": "示例"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["review"]["required"] is True
    assert data["review"]["reviewer_role"] == "古建院专家"
    assert len(data["buildings"]) == 1
    assert data["buildings"][0]["building_id"] == "JH-DY-LZ-001"
    assert data["buildings"][0]["risk_level"] == "Ⅲ"
    assert any(w["level"] == "severe" for w in data["buildings"][0]["weak_components"])


def test_heritage_wind_assessment_empty(client):
    resp = client.post("/api/heritage/wind_assessment", json={"building_ids": []})
    assert resp.status_code == 400


def test_heritage_assets_ascii(client):
    resp = client.get("/api/heritage/assets/072500002AAaa.jpg")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"


def test_heritage_assets_chinese(client):
    resp = client.get("/api/heritage/assets/" + quote("FEA云图_全景.png"))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_heritage_assets_not_found(client):
    resp = client.get("/api/heritage/assets/does_not_exist.png")
    assert resp.status_code == 404


def test_heritage_assets_no_traversal(client):
    resp = client.get("/api/heritage/assets/..%2Fconfig.py")
    assert resp.status_code in (400, 404)


# --- CH9 真实开放数据点位 (Wikidata 国保/世界遗产 + OSM) ---

def test_heritage_points_china(client):
    resp = client.get("/api/heritage/points?scope=china")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data_track"] == "real_open_data"
    assert data["count"] > 1000  # 全国重点文物保护单位 ~5678
    assert "sources" in data and data["sources"].get("wikidata_guobao", 0) > 1000
    p = data["points"][0]
    assert {"id", "name", "lon", "lat", "level"} <= set(p.keys())


def test_heritage_points_global(client):
    resp = client.get("/api/heritage/points?scope=global")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] > 1000  # 世界遗产 ~3643
    assert data["points"][0]["level"] == "world_heritage"


def test_heritage_points_local(client):
    resp = client.get("/api/heritage/points?scope=local&location=shaoxing_yuecheng")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["count"] > 0


def test_heritage_points_invalid_scope(client):
    resp = client.get("/api/heritage/points?scope=bogus")
    assert resp.status_code == 400


def test_heritage_points_local_requires_location(client):
    resp = client.get("/api/heritage/points?scope=local")
    assert resp.status_code == 400


@pytest.fixture
def client():
    """Create a FastAPI TestClient with GEE stubs active."""
    os.environ["PYTEST_STUB_EE"] = "1"
    sys.path.insert(0, BACKEND_DIR)
    from main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
