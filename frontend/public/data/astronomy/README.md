# OneAstronomy public sample data

This folder contains small, deterministic sample datasets that are loaded directly by the frontend demos.

On disk path: `frontend/public/data/astronomy/`

Runtime URL path (served by Vite/Nginx): `/data/astronomy/`

## Files

- `sdss_micro_sample.json`
  - Used by macro scene as a tiny “real-data injection” sample.
  - Supported formats:
    - 2D triples: `[[ra_deg, dec_deg, redshift], ...]`
    - Flat array (recommended for size/perf): `[ra_deg, dec_deg, redshift, ra_deg, dec_deg, redshift, ...]`

- `gotta_transient_event.json`
  - Used by Demo 3 (GOTTA transient capture).
  - Supported formats:
    - Legacy single event object:
      - `eventId` (string)
      - `ra` / `dec` (degrees)
      - `type` (string)
      - `lightcurve.time` / `lightcurve.flux` (arrays)
    - Network schema (recommended):
      - `targetEventId` (string)
      - `events` (array of event objects, each with `eventId`, `ra`, `dec`, optional `type`, optional `lightcurve`)

## Notes

- Keep these datasets small (KBs) so the app stays fast in demos.
- Replace with real datasets by keeping the same JSON schema.

## Replace / generate

1) Keep the filename and schema the same.

2) Put the JSON file under `frontend/public/data/astronomy/`.

3) Hard refresh the browser (or disable cache) to make sure the new file is loaded.
