.PHONY: help test test-fast test-contract test-integration test-backend-api lint \
	docker-dev-up docker-dev-down docker-dev-logs docker-dev-ps docker-dev-pytest docker-dev-vitest docker-dev-check

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

# --- Docker Dev (optional) ---
# Keeps external ports consistent with the repo default: frontend 8504, backend 8505.
# Uses .env.v6 if present, otherwise falls back to .env.

_DEV_ENV_FILE := $(shell if [ -f .env.v6 ]; then echo .env.v6; else echo .env; fi)

_docker_dev_ports_free:
	@if command -v ss >/dev/null 2>&1; then \
		if ss -ltnp 2>/dev/null | egrep -q ':(8504|8505)\b'; then \
			echo "❌ Port 8504/8505 already in use. Stop local dev processes first."; \
			ss -ltnp 2>/dev/null | egrep ':(8504|8505)\b' || true; \
			exit 2; \
		fi; \
	fi

docker-dev-up:
	@echo "Using env file: $(_DEV_ENV_FILE)"
	@if [ ! -f "$(_DEV_ENV_FILE)" ]; then \
		echo "❌ Missing env file: $(_DEV_ENV_FILE)"; \
		echo "   Create one of: .env.v6 or .env (see .env.example)"; \
		exit 2; \
	fi
	@$(MAKE) _docker_dev_ports_free
	docker compose --env-file $(_DEV_ENV_FILE) -f compose/docker-compose.dev.yml up -d --build

docker-dev-down:
	docker compose -f compose/docker-compose.dev.yml down

docker-dev-logs:
	docker compose -f compose/docker-compose.dev.yml logs -f --tail=200

docker-dev-ps:
	docker compose -f compose/docker-compose.dev.yml ps

docker-dev-pytest:
	docker compose -f compose/docker-compose.dev.yml run --rm backend_test

docker-dev-vitest:
	docker compose -f compose/docker-compose.dev.yml run --rm frontend_test

docker-dev-check:
	@echo "==> Smoke: backend /health"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
		if curl -fsS http://127.0.0.1:8505/health >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ backend /health not ready"; exit 1; fi
	@echo "==> Smoke: frontend / (vite)"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
		if curl -fsS http://127.0.0.1:8504/ >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ frontend / not ready"; exit 1; fi
	@echo "==> Smoke: frontend /api/locations (proxy -> backend)"
	@ok=0; for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
		if curl -fsS http://127.0.0.1:8504/api/locations >/dev/null 2>&1; then ok=1; break; fi; \
		sleep 0.3; \
	done; \
	if [ $$ok -ne 1 ]; then echo "❌ frontend /api/locations proxy not ready"; exit 1; fi
	@echo "==> Tests: pytest + vitest in containers"
	@$(MAKE) docker-dev-pytest
	@$(MAKE) docker-dev-vitest
	@echo "✅ docker-dev-check OK"
