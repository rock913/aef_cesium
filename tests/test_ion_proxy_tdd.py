"""TDD: Cesium Ion proxy must work behind same-origin.

Why this exists
--------------
Frontend in China may not reach `api.cesium.com` / `assets.cesium.com` directly.
The backend provides `/api/ion/*` + `/api/ion-assets/*` + `/api/google-tiles/*`.

Critical behaviors:
- Forward auth header to Ion upstream (otherwise 401 and blank 3D tiles).
- Rewrite JSON URLs so the browser stays same-origin.
- Preserve Range requests for large 3D tile payloads.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_and_main(monkeypatch: pytest.MonkeyPatch):
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))
    sys.modules.pop("main", None)

    import main as main_module  # noqa: WPS433 (test import)

    # Ensure no real network calls: replace shared http client.
    return TestClient(main_module.app), main_module


def test_ion_proxy_forwards_authorization_header(client_and_main, monkeypatch: pytest.MonkeyPatch):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        # The proxy must forward Authorization for Ion API.
        assert request.headers.get("authorization") == "Bearer test-token"
        payload = {"hello": "world"}
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            content=json.dumps(payload).encode("utf-8"),
        )

    transport = httpx.MockTransport(handler)
    main.http_client = httpx.AsyncClient(transport=transport)

    resp = client.get(
        "/api/ion/v1/assets/1/endpoint",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200


def test_ion_proxy_rewrites_assets_and_google_tiles_urls(client_and_main, monkeypatch: pytest.MonkeyPatch):
    client, main = client_and_main

    upstream = {
        "assetUrl": "https://assets.cesium.com/123/tileset.json?access_token=abc",
        "nested": {
            "google": "https://tile.googleapis.com/v1/3dtiles/root.json?key=xyz",
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json; charset=utf-8"},
            content=json.dumps(upstream).encode("utf-8"),
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/ion/v1/assets/123/endpoint", headers={"Authorization": "Bearer t"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["assetUrl"].startswith("/api/ion-assets/")
    assert "assets.cesium.com" not in data["assetUrl"]
    assert data["nested"]["google"].startswith("/api/google-tiles/")
    assert "tile.googleapis.com" not in data["nested"]["google"]


def test_ion_assets_proxy_preserves_range_header(client_and_main, monkeypatch: pytest.MonkeyPatch):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("range") == "bytes=0-1023"
        # Return a partial content response typical for 3D tiles.
        return httpx.Response(
            206,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Range": "bytes 0-1023/2048",
                "Accept-Ranges": "bytes",
            },
            content=b"x" * 1024,
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get(
        "/api/ion-assets/123/some.b3dm",
        headers={"Range": "bytes=0-1023"},
    )
    assert resp.status_code == 206
    assert resp.headers.get("content-range")
    assert len(resp.content) == 1024


def test_streaming_proxy_strips_content_length_to_avoid_mismatch(client_and_main):
    client, main = client_and_main

    body = b"x" * 1024

    def handler(request: httpx.Request) -> httpx.Response:
        # Even if upstream provides a Content-Length, our StreamingResponse should not forward it.
        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(body)),
            },
            content=body,
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/ion-assets/123/some.bin")
    assert resp.status_code == 200
    # Avoid browser-side net::ERR_CONTENT_LENGTH_MISMATCH by not forwarding Content-Length on streamed bodies.
    assert "content-length" not in {k.lower() for k in resp.headers.keys()}
    assert resp.content == body


def test_google_tiles_root_json_uses_buffered_proxy_mode(client_and_main):
    client, main = client_and_main

    payload = {
        "hello": "tiles",
        # Absolute-path URIs must be rewritten to stay within /api/google-tiles.
        "content": {"uri": "/v1/3dtiles/datasets/AAA/files/BBB.glb?key=xyz"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "tile.googleapis.com" in str(request.url)
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            content=json.dumps(payload).encode("utf-8"),
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/google-tiles/v1/3dtiles/root.json?key=xyz")
    assert resp.status_code == 200
    assert resp.headers.get("x-oneearth-proxy-mode") == "buffered-json-rewrite"

    data = resp.json()
    assert data["hello"] == "tiles"
    assert data["content"]["uri"].startswith("/api/google-tiles/v1/3dtiles/")
