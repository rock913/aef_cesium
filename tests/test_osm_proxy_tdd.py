"""TDD: OSM tile proxy must never return non-image payloads.

If upstream returns HTML/JSON with 200 status, Cesium may throw
`InvalidStateError: The source image could not be decoded` and stop rendering.
The proxy should fall back to a transparent PNG instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

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


def test_osm_proxy_falls_back_on_non_image_payload(client_and_main):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            content=b"<!doctype html><html><body>upstream error</body></html>",
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/basemap/osm/1/1/1.png")
    assert resp.status_code == 200
    assert resp.headers.get("x-aef-tile-fallback") == "1"
    assert resp.headers.get("x-aef-basemap") == "osm"
    assert resp.headers.get("content-type", "").startswith("image/png")
    assert resp.content.startswith(b"\x89PNG\r\n\x1a\n")
