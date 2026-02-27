"""Contract tests: Google Map Tiles API createSession proxy.

These tests are offline/fast and rely on httpx.MockTransport.
They ensure we can create a session via POST and that backend key-injection
behaves as expected.
"""

from __future__ import annotations

import sys
from pathlib import Path
import json

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_and_main():
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))
    sys.modules.pop("main", None)

    import main as main_module  # noqa: WPS433 (test import)

    return TestClient(main_module.app), main_module


def test_create_session_missing_key_returns_400(client_and_main):
    client, main = client_and_main

    # Ensure no server-side key is set for this test.
    old = getattr(main, "_GOOGLE_MAPS_API_KEY", "")
    main._GOOGLE_MAPS_API_KEY = ""
    try:
        resp = client.post("/api/google-tiles/v1/createSession", json={"mapType": "satellite"})
        assert resp.status_code == 400
        assert "missing" in (resp.text or "").lower()
    finally:
        main._GOOGLE_MAPS_API_KEY = old


def test_create_session_proxies_post_and_injects_key(client_and_main):
    client, main = client_and_main

    seen = {"method": None, "url": None, "json": None}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        try:
            seen["json"] = json.loads((request.content or b"{}").decode("utf-8"))
        except Exception:
            seen["json"] = None

        assert request.method == "POST"
        assert request.url.host == "tile.googleapis.com"
        assert request.url.path == "/v1/createSession"
        assert request.url.params.get("key") == "server-key"

        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={"session": "sess-123", "expiry": "2099-01-01T00:00:00Z"},
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    old = getattr(main, "_GOOGLE_MAPS_API_KEY", "")
    main._GOOGLE_MAPS_API_KEY = "server-key"
    try:
        resp = client.post(
            "/api/google-tiles/v1/createSession",
            json={"mapType": "satellite", "language": "zh-CN", "region": "CN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("session") == "sess-123"
        assert seen["json"]["mapType"] == "satellite"
    finally:
        main._GOOGLE_MAPS_API_KEY = old


def test_create_session_upstream_timeout_returns_504(client_and_main):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout", request=request)

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    old = getattr(main, "_GOOGLE_MAPS_API_KEY", "")
    main._GOOGLE_MAPS_API_KEY = "server-key"
    try:
        resp = client.post("/api/google-tiles/v1/createSession", json={"mapType": "satellite"})
        assert resp.status_code == 504
        assert resp.headers.get("content-type", "").lower().startswith("application/json")
        assert "timeout" in (resp.text or "").lower()
    finally:
        main._GOOGLE_MAPS_API_KEY = old


def test_google_tiles_get_injects_key_when_missing(client_and_main):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        # Ensure proxy injects key when client doesn't send it.
        assert request.url.params.get("key") == "server-key"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={"content": {"uri": "/v1/3dtiles/root.json"}},
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    old = getattr(main, "_GOOGLE_MAPS_API_KEY", "")
    main._GOOGLE_MAPS_API_KEY = "server-key"
    try:
        resp = client.get("/api/google-tiles/v1/3dtiles/root.json")
        assert resp.status_code == 200
    finally:
        main._GOOGLE_MAPS_API_KEY = old
