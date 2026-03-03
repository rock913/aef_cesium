"""TDD: Bing tile proxy must be same-origin and allowlisted.

We intentionally do NOT call real virtualearth.net in unit tests.
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


def test_bing_proxy_rejects_non_virtualearth_hosts(client_and_main):
    client, main = client_and_main

    # No network needed: should be rejected before any upstream call.
    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))

    resp = client.get("/api/bing-proxy", params={"url": "https://example.com/tiles/a.jpeg"})
    assert resp.status_code in {400, 403}


def test_bing_proxy_rejects_unexpected_paths(client_and_main):
    client, main = client_and_main

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))

    resp = client.get(
        "/api/bing-proxy",
        params={"url": "https://ecn.t1.tiles.virtualearth.net/not-tiles/a.jpeg?n=z"},
    )
    assert resp.status_code == 403


def test_bing_proxy_proxies_allowed_tile_and_adds_cors_header(client_and_main):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.scheme == "https"
        assert request.url.host.endswith(".tiles.virtualearth.net")
        assert str(request.url.path).startswith("/tiles/")
        return httpx.Response(
            200,
            headers={"Content-Type": "image/jpeg", "Cache-Control": "public, max-age=60"},
            content=b"jpegbytes",
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get(
        "/api/bing-proxy",
        params={"url": "http://ecn.t1.tiles.virtualearth.net/tiles/a21101.jpeg?n=z&g=15485"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"
    assert resp.headers.get("x-aef-basemap") == "bing"
    assert resp.content == b"jpegbytes"


def test_bing_proxy_falls_back_on_non_image_payload(client_and_main):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            content=b"<!doctype html><html><body>upstream error</body></html>",
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get(
        "/api/bing-proxy",
        params={"url": "https://ecn.t1.tiles.virtualearth.net/tiles/a21101.jpeg?n=z&g=15485"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("x-aef-tile-fallback") == "1"
    assert resp.headers.get("x-aef-basemap") == "bing"
    assert resp.headers.get("content-type", "").startswith("image/png")
    assert resp.content.startswith(b"\x89PNG\r\n\x1a\n")
