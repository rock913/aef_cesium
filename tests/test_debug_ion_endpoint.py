"""TDD: runtime Ion diagnostics endpoint.

Goal
----
`/api/debug/ion` should quickly answer:
- can backend reach Ion API from server network?
- is auth valid (200) or invalid (401)?
- what is the latency?

Security
--------
The endpoint must never return the token.
"""

from __future__ import annotations

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
    import main as main_module  # noqa: WPS433
    return TestClient(main_module.app), main_module


def test_debug_ion_uses_request_authorization_header(client_and_main):
    client, main = client_and_main

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/me")
        assert request.headers.get("authorization") == "Bearer req-token"
        return httpx.Response(200, json={"id": 1, "username": "x"})

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/debug/ion", headers={"Authorization": "Bearer req-token"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["upstream"]["status"] == 200
    assert data["ion"]["auth_source"] == "request"
    # token must not be present anywhere
    assert "req-token" not in resp.text


def test_debug_ion_falls_back_to_env_token_when_missing_header(client_and_main, monkeypatch: pytest.MonkeyPatch):
    client, main = client_and_main

    monkeypatch.setenv("ION_ACCESS_TOKEN", "env-token")
    # refresh module-level cached token
    main._ION_ACCESS_TOKEN = "env-token"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == "Bearer env-token"
        return httpx.Response(200, json={"id": 2})

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/debug/ion")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["ion"]["auth_source"] == "env"
    assert "env-token" not in resp.text


def test_debug_ion_reports_401_cleanly(client_and_main):
    client, main = client_and_main

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    main.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resp = client.get("/api/debug/ion", headers={"Authorization": "Bearer bad"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["upstream"]["status"] == 401
