"""Contract tests: Google Photorealistic 3D tiles proxy.

Goal
----
Ensure `/api/google-tiles/*` never crashes with 500 on upstream timeout,
and that upstream HTTP status codes (e.g. 403) are preserved.

These tests must be offline/fast: use httpx.MockTransport.
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


def test_google_tiles_stream_timeout_returns_504_json_not_500(client_and_main):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout", request=request)

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/google-tiles/v1/3dtiles/datasets/AAA/files/BBB.glb?key=xyz")
    assert resp.status_code == 504
    # FastAPI's HTTPException produces a JSON response body.
    assert resp.headers.get("content-type", "").lower().startswith("application/json")
    assert "timeout" in (resp.text or "").lower()


def test_google_tiles_root_json_timeout_returns_504_json_not_500(client_and_main):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout", request=request)

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/google-tiles/v1/3dtiles/root.json?key=xyz")
    assert resp.status_code == 504
    assert resp.headers.get("content-type", "").lower().startswith("application/json")
    assert "timeout" in (resp.text or "").lower()


def test_google_tiles_root_json_preserves_403_status(client_and_main):
    client, main = client_and_main

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"Content-Type": "application/json"},
            content=b"{\"error\":\"forbidden\"}",
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/google-tiles/v1/3dtiles/root.json?key=bad")
    assert resp.status_code == 403
    # For non-200, JSON rewrite path returns buffered pass-through.
    assert resp.headers.get("x-oneearth-proxy-mode") == "buffered"


def test_google_tiles_stream_preserves_403_status(client_and_main):
    client, main = client_and_main

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"Content-Type": "application/octet-stream"},
            content=b"forbidden",
        )

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/google-tiles/v1/3dtiles/datasets/AAA/files/BBB.glb?key=bad")
    assert resp.status_code == 403
    assert resp.headers.get("x-oneearth-proxy-mode") == "stream"
    assert resp.content == b"forbidden"
