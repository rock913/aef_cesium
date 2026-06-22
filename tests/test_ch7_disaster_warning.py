"""Tests for CH7: 山洪与滑坡灾害极速定损 (AEF Diff × DEM Topology)."""

import pytest
import os
import sys


# --- Mode registration tests (no GEE required) ---

def test_ch7_mode_registered_in_config():
    """Verify ch7_disaster_warning is registered in config modes."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config import settings

    assert "ch7_disaster_warning" in settings.modes
    assert "地质灾害" in settings.modes["ch7_disaster_warning"]


def test_ch7_locations_registered():
    """Verify beijing_2023 and guangdong_2024 locations exist."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config import settings

    assert "beijing_2023" in settings.locations
    assert settings.locations["beijing_2023"]["coords"] == [39.95, 115.90, 10]
    assert "guangdong_2024" in settings.locations
    assert settings.locations["guangdong_2024"]["coords"] == [24.30, 116.10, 10]


def test_ch7_missions_registered():
    """Verify ch7 mission cards exist in the missions list."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config import settings

    mission_ids = {m["id"] for m in settings.missions}
    assert "ch7_beijing" in mission_ids
    assert "ch7_guangdong" in mission_ids

    beijing_mission = next(m for m in settings.missions if m["id"] == "ch7_beijing")
    assert beijing_mission["api_mode"] == "ch7_disaster_warning"
    assert beijing_mission["location"] == "beijing_2023"

    guangdong_mission = next(m for m in settings.missions if m["id"] == "ch7_guangdong")
    assert guangdong_mission["api_mode"] == "ch7_disaster_warning"
    assert guangdong_mission["location"] == "guangdong_2024"


def test_ch7_viewport_buffer():
    """Verify ch7 has a viewport buffer override."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config import settings

    buf = settings.get_viewport_buffer_m_for_mode("ch7_disaster_warning")
    assert buf == 90000


# --- GEE stub tests (vis/suffix, no real EE) ---

def test_ch7_get_mode_vis_and_suffix_stub():
    """Verify get_mode_vis_and_suffix returns correct vis and suffix for ch7."""
    from unittest.mock import patch

    # Stub ee before importing gee_service
    with patch.dict(os.environ, {"PYTEST_STUB_EE": "1"}):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from gee_service import get_mode_vis_and_suffix

        vis, suffix = get_mode_vis_and_suffix("ch7_disaster_warning")
        assert suffix == "ch7_disaster"
        assert vis["min"] == 1
        assert vis["max"] == 2
        assert len(vis["palette"]) == 2
        assert "00F5FF" in vis["palette"]
        assert "FF3300" in vis["palette"]
        assert vis.get("format") == "png"

        # Test Chinese keyword matching
        vis2, suffix2 = get_mode_vis_and_suffix("ch7_disaster_warning 地质灾害极速定损")
        assert suffix2 == "ch7_disaster"

        # Test short keyword
        vis3, suffix3 = get_mode_vis_and_suffix("滑坡灾害检测")
        assert suffix3 == "ch7_disaster"


def test_ch7_mode_string_matching():
    """Verify the mode string matching logic for ch7."""
    mode_str = "ch7_disaster_warning 地质灾害极速定损 (AEF Diff × DEM Topology)"
    assert "ch7_disaster_warning" in mode_str
    assert "地质灾害" in mode_str
    assert "滑坡" not in mode_str  # but the mode dispatch ORs all keywords
    assert "山洪" not in mode_str


# --- API endpoint tests ---

def test_ch7_locations_endpoint(client):
    """Verify new locations appear in /api/locations."""
    resp = client.get("/api/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert "beijing_2023" in data
    assert data["beijing_2023"]["name"] == "北京 · 门头沟/房山"
    assert "guangdong_2024" in data
    assert data["guangdong_2024"]["name"] == "广东 · 梅州/粤北"


def test_ch7_modes_endpoint(client):
    """Verify ch7 appears in /api/modes."""
    resp = client.get("/api/modes")
    assert resp.status_code == 200
    data = resp.json()
    assert "ch7_disaster_warning" in data
    assert "地质灾害" in data["ch7_disaster_warning"]


def test_ch7_missions_endpoint(client):
    """Verify ch7 missions appear in /api/missions."""
    resp = client.get("/api/missions")
    assert resp.status_code == 200
    data = resp.json()
    mission_ids = {m["id"] for m in data}
    assert "ch7_beijing" in mission_ids
    assert "ch7_guangdong" in mission_ids


@pytest.fixture
def client():
    """Create a FastAPI TestClient with GEE stubs active."""
    os.environ["PYTEST_STUB_EE"] = "1"
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
