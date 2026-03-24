"""Contract tests for Astro-GIS Phase 3 catalog endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create FastAPI TestClient with EE stubbed out."""

    import sys
    from pathlib import Path
    import types

    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    # Unit tests should not import the real Earth Engine SDK.
    sys.modules.setdefault("ee", types.ModuleType("ee"))

    # Ensure we import this repo's backend/main.py (not some other workspace module).
    sys.modules.pop("main", None)

    import main as main_module  # pyright: ignore[reportMissingImports]

    # Avoid real EE init during FastAPI startup.
    main_module.init_earth_engine = lambda: None
    main_module.gee_initialized = True

    return TestClient(main_module.app)


def _assert_source_shape(s: dict):
    assert isinstance(s.get("id"), str) and s["id"]
    assert isinstance(s.get("name"), str) and s["name"]

    ra = s.get("ra_deg")
    dec = s.get("dec_deg")
    assert isinstance(ra, (int, float))
    assert isinstance(dec, (int, float))
    assert 0.0 <= float(ra) < 360.0
    assert -90.0 <= float(dec) <= 90.0

    mag = s.get("mag_v")
    assert isinstance(mag, (int, float))

    otype = s.get("otype")
    assert isinstance(otype, str) and otype


class TestAstroGisCatalogSimbad:
    def test_returns_fixture_schema(self, test_client: TestClient):
        resp = test_client.get(
            "/api/astro-gis/catalog/simbad",
            params={"ra": 150.1, "dec": 2.22, "radius": 12.5, "maxRows": 25},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert isinstance(data, dict)
        assert "meta" in data
        assert "sources" in data

        meta = data["meta"]
        assert meta.get("provider") == "simbad"
        assert meta.get("mode") in ("fixture", "online")

        q = meta.get("query")
        assert isinstance(q, dict)
        assert set(q.keys()) >= {"ra_deg", "dec_deg", "radius_deg", "max_rows"}

        sources = data["sources"]
        assert isinstance(sources, list)
        assert 1 <= len(sources) <= 25
        for s in sources[:5]:
            _assert_source_shape(s)

    def test_deterministic_for_same_query(self, test_client: TestClient):
        params = {"ra": 10.5, "dec": -20.25, "radius": 5.0, "maxRows": 50}
        resp1 = test_client.get("/api/astro-gis/catalog/simbad", params=params)
        resp2 = test_client.get("/api/astro-gis/catalog/simbad", params=params)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()

    @pytest.mark.parametrize(
        "params",
        [
            {"ra": 0, "dec": 91, "radius": 5, "maxRows": 10},
            {"ra": 0, "dec": -91, "radius": 5, "maxRows": 10},
            {"ra": 0, "dec": 0, "radius": 0, "maxRows": 10},
            {"ra": 0, "dec": 0, "radius": 100, "maxRows": 10},
            {"ra": 0, "dec": 0, "radius": 5, "maxRows": 0},
        ],
    )
    def test_invalid_params_400(self, test_client: TestClient, params: dict):
        resp = test_client.get("/api/astro-gis/catalog/simbad", params=params)
        assert resp.status_code == 400


class TestAstroGisCatalogVizier:
    def test_returns_fixture_schema(self, test_client: TestClient):
        resp = test_client.get(
            "/api/astro-gis/catalog/vizier",
            params={"catalog": "I/239/hip_main", "ra": 150.1, "dec": 2.22, "radius": 12.5, "maxRows": 25},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert isinstance(data, dict)
        assert "meta" in data
        assert "sources" in data

        meta = data["meta"]
        assert meta.get("provider") == "vizier"
        assert meta.get("mode") in ("fixture", "online")
        assert meta.get("catalog") == "I/239/hip_main"

        q = meta.get("query")
        assert isinstance(q, dict)
        assert set(q.keys()) >= {"catalog", "ra_deg", "dec_deg", "radius_deg", "max_rows"}
        assert q.get("catalog") == "I/239/hip_main"

        sources = data["sources"]
        assert isinstance(sources, list)
        assert 1 <= len(sources) <= 25
        for s in sources[:5]:
            _assert_source_shape(s)

    def test_deterministic_for_same_query(self, test_client: TestClient):
        params = {"catalog": "I/239/hip_main", "ra": 10.5, "dec": -20.25, "radius": 5.0, "maxRows": 50}
        resp1 = test_client.get("/api/astro-gis/catalog/vizier", params=params)
        resp2 = test_client.get("/api/astro-gis/catalog/vizier", params=params)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()

    @pytest.mark.parametrize(
        "params",
        [
            {"catalog": "I/239/hip_main", "ra": 0, "dec": 91, "radius": 5, "maxRows": 10},
            {"catalog": "I/239/hip_main", "ra": 0, "dec": -91, "radius": 5, "maxRows": 10},
            {"catalog": "I/239/hip_main", "ra": 0, "dec": 0, "radius": 0, "maxRows": 10},
            {"catalog": "I/239/hip_main", "ra": 0, "dec": 0, "radius": 100, "maxRows": 10},
            {"catalog": "I/239/hip_main", "ra": 0, "dec": 0, "radius": 5, "maxRows": 0},
            {"catalog": "bad catalog", "ra": 0, "dec": 0, "radius": 5, "maxRows": 10},
            {"catalog": "\"I/239/hip_main\"", "ra": 0, "dec": 0, "radius": 5, "maxRows": 10},
        ],
    )
    def test_invalid_params_400(self, test_client: TestClient, params: dict):
        resp = test_client.get("/api/astro-gis/catalog/vizier", params=params)
        assert resp.status_code == 400

    def test_online_mode_rejects_unlisted_catalogs_without_network(self, test_client: TestClient, monkeypatch: pytest.MonkeyPatch):
        # Enforce allowlist before any network attempt.
        monkeypatch.setenv('ASTRO_GIS_CATALOG_MODE', 'online')
        monkeypatch.setenv('ASTRO_GIS_CATALOG_ONLINE_FALLBACK', '0')
        monkeypatch.setenv('ASTRO_GIS_VIZIER_ALLOWED_CATALOGS', 'I/239/hip_main')

        resp = test_client.get(
            "/api/astro-gis/catalog/vizier",
            params={"catalog": "I/999/not_allowed", "ra": 10.5, "dec": 0.1, "radius": 2.0, "maxRows": 10},
        )
        assert resp.status_code == 400
