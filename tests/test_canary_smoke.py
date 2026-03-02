"""Opt-in smoke tests for Canary ports (8508/8509).

These tests are intentionally skipped by default because they require
`docker compose -f compose/docker-compose.canary.yml up` to be running.

Run:
  make canary-up
  RUN_CANARY_SMOKE=1 pytest -q tests/test_canary_smoke.py
"""

import os

import pytest
import httpx


@pytest.mark.skipif(os.getenv("RUN_CANARY_SMOKE") != "1", reason="RUN_CANARY_SMOKE=1 required")
def test_canary_backend_health():
    r = httpx.get("http://127.0.0.1:8509/health", timeout=5)
    assert r.status_code == 200


@pytest.mark.skipif(os.getenv("RUN_CANARY_SMOKE") != "1", reason="RUN_CANARY_SMOKE=1 required")
def test_canary_frontend_serves_index():
    r = httpx.get("http://127.0.0.1:8508/", timeout=10)
    assert r.status_code == 200
    assert "<html" in r.text.lower()


@pytest.mark.skipif(os.getenv("RUN_CANARY_SMOKE") != "1", reason="RUN_CANARY_SMOKE=1 required")
def test_canary_frontend_proxies_api_locations():
    r = httpx.get("http://127.0.0.1:8508/api/locations", timeout=10)
    assert r.status_code == 200
    payload = r.json()
    assert isinstance(payload, dict)


@pytest.mark.skipif(os.getenv("RUN_CANARY_SMOKE") != "1", reason="RUN_CANARY_SMOKE=1 required")
def test_canary_debug_version_has_deployment_marker():
    r = httpx.get("http://127.0.0.1:8509/api/debug/version", timeout=10)
    assert r.status_code == 200
    payload = r.json()
    assert payload.get("release", {}).get("deployment") == "canary"
