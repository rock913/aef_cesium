"""Tests for CH8: InSAR 沉降数字孪生系统."""

import pytest
import os
import sys

# --- Mode registration tests (no GEE required) ---

def test_ch8_mode_registered_in_config():
    """Verify ch8_insar_subsidence is registered in config modes."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config import settings

    assert "ch8_insar_subsidence" in settings.modes
    assert "SBAS-InSAR" in settings.modes["ch8_insar_subsidence"]

def test_ch8_locations_registered():
    """Verify guangzhou_nansha and guangzhou_tianhe locations exist."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config import settings

    assert "guangzhou_nansha" in settings.locations
    assert settings.locations["guangzhou_nansha"]["coords"] == [22.72, 113.53, 13]
    assert "guangzhou_tianhe" in settings.locations
    assert settings.locations["guangzhou_tianhe"]["coords"] == [23.115, 113.329, 14]

def test_ch8_missions_registered():
    """Verify ch8 mission cards exist in the missions list."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config import settings

    mission_ids = {m["id"] for m in settings.missions}
    assert "填海区沉降" in mission_ids
    assert "核心区沉降" in mission_ids

    nansha_mission = next(m for m in settings.missions if m["id"] == "填海区沉降")
    assert nansha_mission["api_mode"] == "ch8_insar_subsidence"
    assert nansha_mission["location"] == "guangzhou_nansha"
    assert nansha_mission.get("chapter") == "CH8"

    tianhe_mission = next(m for m in settings.missions if m["id"] == "核心区沉降")
    assert tianhe_mission["api_mode"] == "ch8_insar_subsidence"
    assert tianhe_mission["location"] == "guangzhou_tianhe"
    assert tianhe_mission.get("chapter") == "CH8"

def test_ch8_viewport_buffer():
    """Verify ch8 has a viewport buffer override."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config import settings

    buf = settings.get_viewport_buffer_m_for_mode("ch8_insar_subsidence")
    assert buf == 60000

# --- GEE stub tests (vis/suffix, no real EE) ---

def test_ch8_get_mode_vis_and_suffix_stub():
    """Verify get_mode_vis_and_suffix returns correct vis and suffix for ch8."""
    from unittest.mock import patch

    with patch.dict(os.environ, {"PYTEST_STUB_EE": "1"}):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from gee_service import get_mode_vis_and_suffix

        vis, suffix = get_mode_vis_and_suffix("ch8_insar_subsidence")
        assert suffix == "ch8_urban_subsidence"
        assert vis["min"] == -30
        assert vis["max"] == 10
        assert len(vis["palette"]) == 5
        assert "FF0000" in vis["palette"]
        assert vis.get("format") == "png"

        # Test short keyword
        vis3, suffix3 = get_mode_vis_and_suffix("沉降")
        assert suffix3 == "ch8_urban_subsidence"

def test_ch8_mode_string_matching():
    """Verify the mode string matching logic for ch8."""
    mode_str = "ch8_insar_subsidence (毫米级沉降)"
    assert "ch8_insar_subsidence" in mode_str
    assert "沉降" in mode_str

# --- API endpoint tests ---

def test_ch8_locations_endpoint(client):
    """Verify new locations appear in /api/locations."""
    resp = client.get("/api/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert "guangzhou_nansha" in data
    assert data["guangzhou_nansha"]["name"] == "广州 · 南沙区"

def test_ch8_modes_endpoint(client):
    """Verify ch8 appears in /api/modes."""
    resp = client.get("/api/modes")
    assert resp.status_code == 200
    data = resp.json()
    assert "ch8_insar_subsidence" in data
    assert "SBAS-InSAR" in data["ch8_insar_subsidence"]

def test_ch8_missions_endpoint(client):
    """Verify ch8 missions appear in /api/missions."""
    resp = client.get("/api/missions")
    assert resp.status_code == 200
    data = resp.json()
    mission_ids = {m["id"] for m in data}
    assert "填海区沉降" in mission_ids
    assert "核心区沉降" in mission_ids

from unittest.mock import Mock, patch

@patch('main.ee.Geometry.Point')
@patch('main.smart_load')
@patch('main.get_tile_url')
def test_ch8_layers_endpoint(mock_get_tile, mock_smart_load, mock_point, client):
    """Verify /api/layers returns 200 and correct structure for ch8."""
    mock_viewport = Mock()
    mock_point.return_value.buffer.return_value = mock_viewport
    mock_viewport.bounds.return_value = mock_viewport

    mock_image = Mock()
    mock_vis = {'min': -30, 'max': 10, 'format': 'png'}
    mock_smart_load.return_value = (
        mock_image,
        mock_vis,
        "cached",
        True,
        "asset_id",
        mock_image
    )
    mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/{z}/{x}/{y}"

    resp = client.get("/api/layers?mode=ch8_insar_subsidence&location=guangzhou_nansha")
    assert resp.status_code == 200
    data = resp.json()
    assert "tile_url" in data
    assert data.get("mode") == "ch8_insar_subsidence"
    assert "render_hints" in data
    assert data["render_hints"]["ai_opacity"] == 0.88

@pytest.fixture
def client():
    """Create a FastAPI TestClient with GEE stubs active."""
    os.environ["PYTEST_STUB_EE"] = "1"
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
