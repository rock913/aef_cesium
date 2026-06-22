# Astro‑GIS (Phase 1/2/3) End‑to‑End Test Playbook

This repo’s Astro‑GIS work is designed to be testable **offline** and in CI.

- Phase 1: layer store authority (`astroStore.astroGis.layers`)
- Phase 2: HiPS underlay (Aladin Lite v3) + FOV sync
- Phase 3: catalog overlay (SIMBAD) via backend API (offline deterministic fixtures by default)

## 1) Local unit/contract tests

### Backend (pytest)

From repo root:

- Full suite (unit/contract; integration remains opt‑in):
  - `make test`
- Just the Astro‑GIS catalog contract:
  - `.venv/bin/python -m pytest -q tests/test_astro_gis_catalog_api.py`

What it covers:
- `GET /api/astro-gis/catalog/simbad` returns stable JSON schema
- `maxRows` is respected/capped
- Identical query → identical response (fixture determinism)
- Invalid params return `400`

### Frontend (vitest)

From `frontend/`:

- `npm test`

What it covers (Astro‑GIS relevant gates):
- Store behavior (`astroGisLayerStore.test.js`)
- No‑DOM safety for Aladin adapter (`aladinLiteAdapter.test.js`)
- Wiring gate for ThreeTwin (includes HiPS + catalog overlay keywords)

## 2) Docker dev E2E gate (recommended)

From repo root:

1) Bring up dev stack:
- `make docker-dev-up`

2) Run the end‑to‑end check:
- `make docker-dev-check`

This now includes smoke checks for:
- Backend health: `http://127.0.0.1:8405/health`
- Frontend Vite: `http://127.0.0.1:8404/`
- Frontend → backend proxy: `http://127.0.0.1:8404/api/locations`
- Astro‑GIS catalog proxy: `http://127.0.0.1:8404/api/astro-gis/catalog/simbad?...`

## 3) Manual visual validation (browser)

With dev stack running (`make docker-dev-up`):

1) Open the workbench:
- `http://127.0.0.1:8404/#/workbench`

2) Phase 1 (layer authority):
- In the LayerTree under **SKY**, toggle layers like:
  - `Macro SDSS (Cosmic Web)`
  - `Demo CSST`, `Demo GOTTA`, `Demo Inpaint`
- Confirm visibility/opacity changes affect the Three scene.

3) Phase 2 (HiPS underlay):
- Toggle **HiPS Background** ON
- Confirm an underlay sky image appears behind WebGL
- Toggle **FOV sync** ON and orbit the camera; underlay should follow view

Notes:
- HiPS uses a dynamic loader; if external CDS resources are blocked, the underlay may no‑op.
- This should not crash the app (adapter is best‑effort).

4) Phase 3 (catalog overlay):
- Toggle **Catalog: SIMBAD** ON
- Move/orbit the macro camera; you should see cyan points on the sky sphere
- In DevTools → Network, confirm requests like:
  - `/api/astro-gis/catalog/simbad?ra=...&dec=...&radius=...&maxRows=...`

Notes:
- Backend defaults to **offline deterministic fixtures**; it does not require internet.
- `maxRows` in LayerTree should change the result density.

## 4) API contract (Phase 3)

`GET /api/astro-gis/catalog/simbad`

Query params:
- `ra` (deg) – normalized into `[0, 360)`
- `dec` (deg) – must be in `[-90, 90]`
- `radius` (deg) – must be in `(0, 90]`
- `maxRows` (int) – must be `>= 1` (server caps at `2000`)

Response shape:
- `meta.provider = "simbad"`
- `meta.mode = "fixture"` (default)
- `meta.query` echoes normalized query values
- `sources[]` list with:
  - `id`, `name`, `ra_deg`, `dec_deg`, `mag_v`, `otype`
