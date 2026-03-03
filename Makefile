
.PHONY: help test test-fast test-contract test-integration test-backend-api lint \
	docker-dev-up docker-dev-down docker-dev-logs docker-dev-ps docker-dev-pytest docker-dev-vitest docker-dev-check \
	docker-prod-up docker-prod-down docker-prod-logs docker-prod-ps docker-prod-check

# Prefer local workspace virtualenv if present.
PYTHON ?= python3
VENV_PY := $(if $(wildcard .venv/bin/python),.venv/bin/python,$(PYTHON))
PYTEST := $(VENV_PY) -m pytest

help:
	@echo "Targets:"
	@echo "  make test              - Run full pytest suite (fast stubs on by default)"
	@echo "  make test-fast         - Same as test, explicitly enforces fast stubs"
	@echo "  make test-contract     - Run tile/PNG HTTP contract tests only"
	@echo "  make test-backend-api  - Run backend API unit tests (TestClient-based)"
	@echo "  make test-integration  - Run integration/diagnostic tests (real EE/backend)"
	@echo ""
	@echo "Env toggles:"
	@echo "  PYTEST_STUB_EE=0        - Disable ee/llm stubs for unit tests"
	@echo "  RUN_INTEGRATION_TESTS=1 - Enable opt-in integration tests"

# Full suite (unit/contract). Integration tests remain skipped unless opted in.
# Default: PYTEST_STUB_EE=1 (see tests/conftest.py)

test:
	$(PYTEST) -q

test-fast:
	PYTEST_STUB_EE=1 $(PYTEST) -q

test-contract:
	PYTEST_STUB_EE=1 $(PYTEST) -q tests/test_tile_png_contract.py

test-backend-api:
	PYTEST_STUB_EE=1 $(PYTEST) -q tests/test_backend_api.py

# Opt-in: runs integration diagnostics (may call real EE and local backend).
# You can still disable stubs explicitly if your shell exports PYTEST_STUB_EE=1.

test-integration:
	RUN_INTEGRATION_TESTS=1 PYTEST_STUB_EE=0 $(PYTEST) -q tests/test_gee_tile_diagnostics.py

# --- Docker Dev/Prod (021 ports) ---
# Dev:  frontend 8404, backend 8405 (vite + uvicorn reload)
# Prod: frontend 8406, backend 8407 (static nginx + uvicorn)
#
# Uses .env.dev / .env.prod when present, otherwise falls back to .env.

_DEV_ENV_FILE := $(shell if [ -f .env.dev ]; then echo .env.dev; else echo .env; fi)
_PROD_ENV_FILE := $(shell if [ -f .env.prod ]; then echo .env.prod; else echo .env; fi)

_GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "")

_DEV_COMPOSE := ONEEARTH_ENV_FILE=../$(_DEV_ENV_FILE) ONEEARTH_RELEASE_SHA=$(_GIT_SHA) docker compose --env-file $(_DEV_ENV_FILE) -f compose/docker-compose.dev.yml
_PROD_COMPOSE := ONEEARTH_ENV_FILE=../$(_PROD_ENV_FILE) ONEEARTH_RELEASE_SHA=$(_GIT_SHA) docker compose --env-file $(_PROD_ENV_FILE) -f compose/docker-compose.prod.yml

_docker_dev_ports_free:
	@if command -v ss >/dev/null 2>&1; then \
		if ss -ltnp 2>/dev/null | egrep -q ':(8404|8405)\b'; then \
			echo "❌ Port 8404/8405 already in use. Stop local dev processes first."; \
			ss -ltnp 2>/dev/null | egrep ':(8404|8405)\b' || true; \
			exit 2; \
		fi; \
	fi

_docker_prod_ports_free:
	@if command -v ss >/dev/null 2>&1; then \
		if ss -ltnp 2>/dev/null | egrep -q ':(8406|8407)\b'; then \
			echo "❌ Port 8406/8407 already in use. Stop local prod processes first."; \
			ss -ltnp 2>/dev/null | egrep ':(8406|8407)\b' || true; \
			exit 2; \
		fi; \
	fi

docker-dev-up:
	@echo "Using env file: $(_DEV_ENV_FILE)"
	@if [ ! -f "$(_DEV_ENV_FILE)" ]; then \
		echo "❌ Missing env file: $(_DEV_ENV_FILE)"; \
		echo "   Create one of: .env.dev or .env (see .env.example)"; \
		exit 2; \
	fi
	@$(MAKE) _docker_dev_ports_free
	$(_DEV_COMPOSE) up -d --build

docker-dev-down:
	$(_DEV_COMPOSE) down

docker-dev-logs:
	$(_DEV_COMPOSE) logs -f --tail=200

docker-dev-ps:
	$(_DEV_COMPOSE) ps

docker-dev-pytest:
	$(_DEV_COMPOSE) run --rm backend_test

docker-dev-vitest:
	$(_DEV_COMPOSE) run --rm frontend_test

docker-dev-check:
	@echo "==> Smoke: backend /health"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60; do \
		if curl -fsS http://127.0.0.1:8405/health >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ backend /health not ready"; exit 1; fi
	@echo "==> Smoke: frontend / (vite)"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60; do \
		if curl -fsS http://127.0.0.1:8404/ >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ frontend / not ready"; exit 1; fi
	@echo "==> Smoke: frontend /api/locations (proxy -> backend)"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60; do \
		if curl -fsS http://127.0.0.1:8404/api/locations >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ frontend /api/locations proxy not ready"; exit 1; fi
	@echo "==> Smoke: static assets (posters)"
	@if ! curl -fsSI http://127.0.0.1:8404/zero2x/ui/act2_geogpt.webp | tr -d '\r' | grep -Eqi 'content-type:.*image/webp'; then \
		echo "❌ missing/incorrect content-type: /zero2x/ui/act2_geogpt.webp"; exit 1; \
	fi
	@if ! curl -fsSI http://127.0.0.1:8404/zero2x/ui/act2_astronomy.webp | tr -d '\r' | grep -Eqi 'content-type:.*image/webp'; then \
		echo "❌ missing/incorrect content-type: /zero2x/ui/act2_astronomy.webp"; exit 1; \
	fi
	@if ! curl -fsSI http://127.0.0.1:8404/zero2x/ui/act3_genos.webp | tr -d '\r' | grep -Eqi 'content-type:.*image/webp'; then \
		echo "❌ missing/incorrect content-type: /zero2x/ui/act3_genos.webp"; exit 1; \
	fi
	@if ! curl -fsSI http://127.0.0.1:8404/zero2x/ui/act3_oneporous.webp | tr -d '\r' | grep -Eqi 'content-type:.*image/webp'; then \
		echo "❌ missing/incorrect content-type: /zero2x/ui/act3_oneporous.webp"; exit 1; \
	fi
	@echo "==> Tests: pytest + vitest in containers"
	@$(MAKE) docker-dev-pytest
	@$(MAKE) docker-dev-vitest
	@echo "✅ docker-dev-check OK"


# --- Docker Prod (8406/8407) ---

docker-prod-up:
	@echo "Using env file: $(_PROD_ENV_FILE)"
	@if [ ! -f "$(_PROD_ENV_FILE)" ]; then \
		echo "❌ Missing env file: $(_PROD_ENV_FILE)"; \
		echo "   Create one of: .env.prod or .env (see .env.example)"; \
		exit 2; \
	fi
	@$(MAKE) _docker_prod_ports_free
	$(_PROD_COMPOSE) up -d --build

docker-prod-down:
	$(_PROD_COMPOSE) down

docker-prod-logs:
	$(_PROD_COMPOSE) logs -f --tail=200

docker-prod-ps:
	$(_PROD_COMPOSE) ps

docker-prod-check:
	@echo "==> Smoke: prod backend /health"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60; do \
		if curl -fsS http://127.0.0.1:8407/health >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ prod backend /health not ready"; exit 1; fi
	@echo "==> Smoke: prod frontend / (nginx)"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60; do \
		if curl -fsS http://127.0.0.1:8406/ >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ prod frontend / not ready"; exit 1; fi
	@echo "==> Smoke: prod frontend /api/locations (proxy -> backend)"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60; do \
		if curl -fsS http://127.0.0.1:8406/api/locations >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ prod frontend /api/locations proxy not ready"; exit 1; fi
	@echo "==> Smoke: prod static assets (posters)"
	@if ! curl -fsSI http://127.0.0.1:8406/zero2x/ui/act2_geogpt.webp | tr -d '\r' | grep -Eqi 'content-type:.*image/webp'; then \
		echo "❌ missing/incorrect content-type: /zero2x/ui/act2_geogpt.webp"; exit 1; \
	fi
	@if ! curl -fsSI http://127.0.0.1:8406/zero2x/ui/act2_astronomy.webp | tr -d '\r' | grep -Eqi 'content-type:.*image/webp'; then \
		echo "❌ missing/incorrect content-type: /zero2x/ui/act2_astronomy.webp"; exit 1; \
	fi
	@if ! curl -fsSI http://127.0.0.1:8406/zero2x/ui/act3_genos.webp | tr -d '\r' | grep -Eqi 'content-type:.*image/webp'; then \
		echo "❌ missing/incorrect content-type: /zero2x/ui/act3_genos.webp"; exit 1; \
	fi
	@if ! curl -fsSI http://127.0.0.1:8406/zero2x/ui/act3_oneporous.webp | tr -d '\r' | grep -Eqi 'content-type:.*image/webp'; then \
		echo "❌ missing/incorrect content-type: /zero2x/ui/act3_oneporous.webp"; exit 1; \
	fi
	@echo "✅ docker-prod-check OK"
