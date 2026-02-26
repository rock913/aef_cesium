.PHONY: help test test-fast test-contract test-integration test-backend-api lint

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
