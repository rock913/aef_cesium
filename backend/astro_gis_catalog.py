"""Astro-GIS catalog service.

Phase 3 goal: provide catalog point sources (e.g. SIMBAD) for the sky viewer.

Design constraints:
- Unit tests and offline/dev environments must work without external network.
- Default behavior is deterministic fixture data based on query params.
- Online lookups are available behind an env flag and must be safe to fail.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import csv
import hashlib
import io
import math
import os
import random
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


CATALOG_MODE_ENV = "ASTRO_GIS_CATALOG_MODE"  # fixture | online

SIMBAD_TAP_SYNC_URL_ENV = "ASTRO_GIS_SIMBAD_TAP_SYNC_URL"
VIZIER_TAP_SYNC_URL_ENV = "ASTRO_GIS_VIZIER_TAP_SYNC_URL"
VIZIER_ALLOWED_CATALOGS_ENV = "ASTRO_GIS_VIZIER_ALLOWED_CATALOGS"  # comma-separated allowlist for online mode
CATALOG_ONLINE_TIMEOUT_S_ENV = "ASTRO_GIS_CATALOG_ONLINE_TIMEOUT_S"
CATALOG_ONLINE_FALLBACK_ENV = "ASTRO_GIS_CATALOG_ONLINE_FALLBACK"  # 1|0
CATALOG_CACHE_TTL_S_ENV = "ASTRO_GIS_CATALOG_CACHE_TTL_S"
CATALOG_CACHE_MAX_ITEMS_ENV = "ASTRO_GIS_CATALOG_CACHE_MAX_ITEMS"

_DEFAULT_SIMBAD_TAP_SYNC_URL = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
_DEFAULT_VIZIER_TAP_SYNC_URL = "https://tapvizier.u-strasbg.fr/TAPVizieR/tap/sync"

_cache_lock = threading.Lock()
_cache: "OrderedDict[str, tuple[float, Dict[str, Any]]]" = OrderedDict()


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _normalize_ra_deg(ra: float) -> float:
    # Normalize into [0, 360)
    x = float(ra) % 360.0
    if x < 0:
        x += 360.0
    return x


def _validate_dec_deg(dec: float) -> float:
    d = float(dec)
    if d < -90.0 or d > 90.0:
        raise ValueError("dec out of range [-90, 90]")
    return d


def _validate_radius_deg(radius: float) -> float:
    r = float(radius)
    if not math.isfinite(r) or r <= 0:
        raise ValueError("radius must be > 0")
    # Keep within a sane sky-cap.
    if r > 90.0:
        raise ValueError("radius must be <= 90")
    return r


def _seed_for_query(*, ra: float, dec: float, radius: float, max_rows: int) -> int:
    msg = f"ra={ra:.6f};dec={dec:.6f};radius={radius:.6f};max_rows={int(max_rows)}"
    h = hashlib.sha256(msg.encode("utf-8")).hexdigest()
    # Use 64 bits of entropy -> python int.
    return int(h[:16], 16)


def _sample_on_cap(
    rng: random.Random,
    *,
    ra0_deg: float,
    dec0_deg: float,
    radius_deg: float,
) -> Tuple[float, float]:
    """Uniformly sample a point within a spherical cap (radius_deg) around (ra0, dec0)."""

    ra0 = math.radians(ra0_deg)
    dec0 = math.radians(dec0_deg)
    cap = math.radians(radius_deg)

    # Sample angular distance with area-uniform distribution:
    # cos(theta) is uniform in [cos(cap), 1]
    u = rng.random()
    cos_theta = (1.0 - u) + u * math.cos(cap)
    theta = math.acos(_clamp(cos_theta, -1.0, 1.0))
    phi = rng.random() * 2.0 * math.pi

    # Convert from local tangent frame around center.
    # See: rotation of vector on sphere.
    sin_dec0 = math.sin(dec0)
    cos_dec0 = math.cos(dec0)

    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)

    dec = math.asin(_clamp(sin_dec0 * cos_theta + cos_dec0 * sin_theta * cos_phi, -1.0, 1.0))

    y = sin_phi * sin_theta
    x = cos_dec0 * cos_theta - sin_dec0 * sin_theta * cos_phi
    ra = ra0 + math.atan2(y, x)

    ra_deg = _normalize_ra_deg(math.degrees(ra))
    dec_deg = math.degrees(dec)
    return ra_deg, dec_deg


@dataclass(frozen=True)
class CatalogQuery:
    ra_deg: float
    dec_deg: float
    radius_deg: float
    max_rows: int


def _env_float(name: str, default: float) -> float:
    try:
        v = float(os.getenv(name, str(default)))
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        v = int(os.getenv(name, str(default)))
        return v
    except Exception:
        return default


def _env_bool(name: str, default: bool) -> bool:
    s = str(os.getenv(name, ""))
    if not s:
        return default
    return s.strip().lower() not in ("0", "false", "no", "off")


def _cache_key(provider: str, q: CatalogQuery) -> str:
    return f"{provider}|{q.ra_deg:.6f}|{q.dec_deg:.6f}|{q.radius_deg:.6f}|{int(q.max_rows)}"


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    now = time.time()
    with _cache_lock:
        item = _cache.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= now:
            try:
                _cache.pop(key, None)
            except Exception:
                pass
            return None
        # refresh LRU
        _cache.move_to_end(key)
        return value


def _cache_set(key: str, value: Dict[str, Any]) -> None:
    ttl_s = max(0.0, _env_float(CATALOG_CACHE_TTL_S_ENV, 30.0))
    max_items = max(1, _env_int(CATALOG_CACHE_MAX_ITEMS_ENV, 256))
    expires_at = time.time() + ttl_s
    with _cache_lock:
        _cache[key] = (expires_at, value)
        _cache.move_to_end(key)
        while len(_cache) > max_items:
            try:
                _cache.popitem(last=False)
            except Exception:
                break


def _build_simbad_tap_adql(q: CatalogQuery) -> str:
    # SIMBAD TAP ADQL: basic table provides main_id/ra/dec/otype; flux provides per-band magnitudes.
    # NOTE: TAP CIRCLE radius is in degrees.
    ra = float(q.ra_deg)
    dec = float(q.dec_deg)
    radius = float(q.radius_deg)
    top = int(q.max_rows)

    return (
        "SELECT TOP {top} "
        "  b.main_id AS main_id, "
        "  b.ra AS ra_deg, "
        "  b.dec AS dec_deg, "
        "  b.otype AS otype, "
        "  f.flux AS mag_v "
        "FROM basic AS b "
        "LEFT OUTER JOIN flux AS f ON f.oidref = b.oid AND f.filter = 'V' "
        "WHERE 1=CONTAINS( "
        "  POINT('ICRS', b.ra, b.dec), "
        "  CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, {radius:.6f}) "
        ")"
    ).format(top=top, ra=ra, dec=dec, radius=radius)


def _query_simbad_online(q: CatalogQuery) -> Dict[str, Any]:
    try:
        import httpx  # type: ignore
    except Exception as e:
        raise RuntimeError("httpx_not_available") from e

    url = str(os.getenv(SIMBAD_TAP_SYNC_URL_ENV, _DEFAULT_SIMBAD_TAP_SYNC_URL) or _DEFAULT_SIMBAD_TAP_SYNC_URL).strip()
    if not url:
        url = _DEFAULT_SIMBAD_TAP_SYNC_URL
    timeout_s = max(0.5, _env_float(CATALOG_ONLINE_TIMEOUT_S_ENV, 8.0))

    adql = _build_simbad_tap_adql(q)

    headers = {
        "user-agent": "Zero2x-OneAstronomy/7.5 (Astro-GIS catalog)",
        "accept": "text/csv, text/plain, */*",
    }

    # TAP sync requests are typically form-encoded.
    payload = {
        "request": "doQuery",
        "lang": "adql",
        "format": "csv",
        "query": adql,
    }

    with httpx.Client(timeout=timeout_s, headers=headers, follow_redirects=True) as client:
        resp = client.post(url, data=payload)
        resp.raise_for_status()
        text = resp.text or ""

    # Parse CSV.
    sources: List[Dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader):
        if i >= q.max_rows:
            break

        name = str((row.get("main_id") or "")).strip()
        if not name:
            continue
        try:
            ra = _normalize_ra_deg(float(row.get("ra_deg") or 0.0))
            dec = float(row.get("dec_deg") or 0.0)
        except Exception:
            continue

        otype = str((row.get("otype") or "Unknown")).strip() or "Unknown"
        mag_raw = row.get("mag_v")
        try:
            mag_v = float(mag_raw) if mag_raw not in (None, "") else 12.0
        except Exception:
            mag_v = 12.0

        sources.append(
            {
                "id": f"SIMBAD:{name}",
                "name": name,
                "ra_deg": float(ra),
                "dec_deg": float(dec),
                "mag_v": float(_clamp(mag_v, -1.0, 40.0)),
                "otype": otype,
            }
        )

    return {
        "meta": {
            "provider": "simbad",
            "mode": "online",
            "upstream": {"kind": "tap", "url": url},
            "query": {
                "ra_deg": float(q.ra_deg),
                "dec_deg": float(q.dec_deg),
                "radius_deg": float(q.radius_deg),
                "max_rows": int(q.max_rows),
            },
        },
        "sources": sources,
    }


def query_simbad_catalog(
    *,
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    max_rows: int,
) -> Dict[str, Any]:
    """Query a SIMBAD-like catalog.

    Default mode is offline deterministic fixture data.
    """

    mode = str(os.getenv(CATALOG_MODE_ENV, "fixture") or "fixture").strip().lower()
    if mode not in ("fixture", "online"):
        mode = "fixture"

    ra = _normalize_ra_deg(ra_deg)
    dec = _validate_dec_deg(dec_deg)
    radius = _validate_radius_deg(radius_deg)
    max_rows_i = int(max_rows)
    if max_rows_i < 1:
        raise ValueError("maxRows must be >= 1")

    # Hard cap to prevent abuse.
    max_rows_i = min(max_rows_i, 2000)

    q = CatalogQuery(ra_deg=float(ra), dec_deg=float(dec), radius_deg=float(radius), max_rows=int(max_rows_i))

    if mode == "online":
        key = _cache_key("simbad", q)
        cached = _cache_get(key)
        if cached is not None:
            try:
                cached_meta = cached.get("meta") if isinstance(cached, dict) else None
                if isinstance(cached_meta, dict):
                    cached_meta["cached"] = True
            except Exception:
                pass
            return cached

        fallback = _env_bool(CATALOG_ONLINE_FALLBACK_ENV, True)
        try:
            out = _query_simbad_online(q)
            try:
                out_meta = out.get("meta") if isinstance(out, dict) else None
                if isinstance(out_meta, dict):
                    out_meta["cached"] = False
            except Exception:
                pass
            _cache_set(key, out)
            return out
        except Exception as e:
            if not fallback:
                raise
            # Safe fallback to deterministic fixtures.
            mode = "fixture"
            requested_mode = "online"
            fallback_reason = f"{type(e).__name__}"

    seed = _seed_for_query(ra=ra, dec=dec, radius=radius, max_rows=max_rows_i)
    rng = random.Random(seed)

    # Generate a plausible number of sources: scale with search area.
    # Area fraction ~ (1 - cos(cap))/2
    cap = math.radians(radius)
    area_frac = (1.0 - math.cos(cap)) / 2.0
    expected = int(_clamp(4000.0 * area_frac, 10.0, float(max_rows_i)))
    n = int(_clamp(expected + rng.randint(-3, 3), 1.0, float(max_rows_i)))

    types = ["Star", "Galaxy", "Quasar", "Nebula", "Cluster"]

    sources: List[Dict[str, Any]] = []
    for i in range(n):
        sra, sdec = _sample_on_cap(rng, ra0_deg=ra, dec0_deg=dec, radius_deg=radius)

        # Brighter objects are rarer: bias magnitudes.
        mag_v = _clamp(rng.gauss(12.5, 2.8), -1.0, 22.0)

        sources.append(
            {
                "id": f"SIMBAD:FIX:{seed:x}:{i}",
                "name": f"MockObject-{(seed + i) % 100000:05d}",
                "ra_deg": float(sra),
                "dec_deg": float(sdec),
                "mag_v": float(mag_v),
                "otype": rng.choice(types),
            }
        )

    meta: Dict[str, Any] = {
        "provider": "simbad",
        "mode": mode,
        "query": {
            "ra_deg": float(ra),
            "dec_deg": float(dec),
            "radius_deg": float(radius),
            "max_rows": int(max_rows_i),
        },
    }
    if mode == "fixture" and "requested_mode" in locals():
        meta["requested_mode"] = requested_mode
        meta["fallback_reason"] = fallback_reason

    return {
        "meta": {
            **meta,
        },
        "sources": sources,
    }


# --- VizieR (provider expansion, Phase 2.7) ---


_VIZIER_CATALOG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,80}$")


def _validate_vizier_catalog_id(catalog: str) -> str:
    c = str(catalog or "").strip()
    if not c:
        raise ValueError("catalog is required")
    if not _VIZIER_CATALOG_RE.match(c):
        raise ValueError("invalid catalog id")
    return c


def _vizier_online_allowlist() -> set[str]:
    raw = str(os.getenv(VIZIER_ALLOWED_CATALOGS_ENV, "") or "").strip()
    if not raw:
        # Default is deliberately narrow for safety.
        return {"I/239/hip_main"}
    out: set[str] = set()
    for part in raw.split(","):
        c = str(part or "").strip()
        if not c:
            continue
        if _VIZIER_CATALOG_RE.match(c):
            out.add(c)
    return out or {"I/239/hip_main"}


def _seed_for_vizier_query(*, catalog: str, ra: float, dec: float, radius: float, max_rows: int) -> int:
    msg = f"catalog={catalog};ra={ra:.6f};dec={dec:.6f};radius={radius:.6f};max_rows={int(max_rows)}"
    h = hashlib.sha256(msg.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


@dataclass(frozen=True)
class VizierCatalogQuery:
    catalog: str
    ra_deg: float
    dec_deg: float
    radius_deg: float
    max_rows: int


def _cache_key_vizier(q: VizierCatalogQuery) -> str:
    return f"vizier|{q.catalog}|{q.ra_deg:.6f}|{q.dec_deg:.6f}|{q.radius_deg:.6f}|{int(q.max_rows)}"


def _build_vizier_tap_adql(q: VizierCatalogQuery) -> str:
    # TAP CIRCLE radius is in degrees. Keep the query strictly parameterized.
    ra = float(q.ra_deg)
    dec = float(q.dec_deg)
    radius = float(q.radius_deg)
    top = int(q.max_rows)

    # Phase 2.8: multi-catalog online support behind an explicit allowlist.
    # Default allowlist remains narrow; deployments can expand it via env.
    #
    # We keep the ADQL strictly parameterized: only the table id is interpolated
    # (and it is validated + allowlisted).
    if q.catalog == "I/239/hip_main":
        # Hipparcos main table (stable, well-known columns).
        # Columns: RA_ICRS, DE_ICRS, Vmag, HIP
        return (
            "SELECT TOP {top} "
            "  HIP AS hip_id, "
            "  RA_ICRS AS ra_deg, "
            "  DE_ICRS AS dec_deg, "
            "  Vmag AS mag_v "
            "FROM \"{table}\" "
            "WHERE 1=CONTAINS( "
            "  POINT('ICRS', RA_ICRS, DE_ICRS), "
            "  CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, {radius:.6f}) "
            ")"
        ).format(top=top, table=q.catalog, ra=ra, dec=dec, radius=radius)

    # Best-effort generic query path: assumes RAJ2000/DEJ2000 exist.
    # If the chosen table does not have these columns, the request may fail and
    # (optionally) fall back to deterministic fixtures.
    return (
        "SELECT TOP {top} * "
        "FROM \"{table}\" "
        "WHERE 1=CONTAINS( "
        "  POINT('ICRS', RAJ2000, DEJ2000), "
        "  CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, {radius:.6f}) "
        ")"
    ).format(top=top, table=q.catalog, ra=ra, dec=dec, radius=radius)


def _query_vizier_online(q: VizierCatalogQuery) -> Dict[str, Any]:
    try:
        import httpx  # type: ignore
    except Exception as e:
        raise RuntimeError("httpx_not_available") from e

    url = str(os.getenv(VIZIER_TAP_SYNC_URL_ENV, _DEFAULT_VIZIER_TAP_SYNC_URL) or _DEFAULT_VIZIER_TAP_SYNC_URL).strip()
    if not url:
        url = _DEFAULT_VIZIER_TAP_SYNC_URL

    timeout_s = max(0.5, _env_float(CATALOG_ONLINE_TIMEOUT_S_ENV, 10.0))
    adql = _build_vizier_tap_adql(q)

    headers = {
        "user-agent": "Zero2x-OneAstronomy/7.5 (Astro-GIS catalog)",
        "accept": "text/csv, text/plain, */*",
    }

    payload = {
        "request": "doQuery",
        "lang": "adql",
        "format": "csv",
        "query": adql,
    }

    with httpx.Client(timeout=timeout_s, headers=headers, follow_redirects=True) as client:
        resp = client.post(url, data=payload)
        resp.raise_for_status()
        text = resp.text or ""

    def _pick_first(row: dict, keys: list[str]) -> Optional[str]:
        for k in keys:
            if k in row and row.get(k) not in (None, ""):
                return str(row.get(k))
            # Some TAP exports normalize header case.
            lk = k.lower()
            if lk in row and row.get(lk) not in (None, ""):
                return str(row.get(lk))
            uk = k.upper()
            if uk in row and row.get(uk) not in (None, ""):
                return str(row.get(uk))
        return None

    sources: List[Dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader):
        if i >= q.max_rows:
            break

        ra_raw = _pick_first(row, ["ra_deg", "RA_ICRS", "RAJ2000", "_RAJ2000"])
        dec_raw = _pick_first(row, ["dec_deg", "DE_ICRS", "DEJ2000", "_DEJ2000"])
        if ra_raw is None or dec_raw is None:
            continue

        try:
            ra = _normalize_ra_deg(float(ra_raw))
            dec = float(dec_raw)
        except Exception:
            continue

        mag_raw = _pick_first(row, ["mag_v", "Vmag", "VTmag", "Gmag", "Rmag", "Jmag", "Hmag", "Kmag"])
        try:
            mag_v = float(mag_raw) if mag_raw not in (None, "") else 10.0
        except Exception:
            mag_v = 10.0

        obj_id = (_pick_first(row, ["hip_id", "HIP", "Source", "source_id", "TYC", "Tyc", "Gaia", "2MASS"]) or "").strip()
        if not obj_id:
            obj_id = f"ROW{i}"

        otype = (_pick_first(row, ["otype", "OTYPE", "class", "Class", "SpType", "sptype"]) or "Star").strip() or "Star"

        sources.append(
            {
                "id": f"VIZIER:{q.catalog}:{obj_id}",
                "name": f"{obj_id}" if q.catalog != "I/239/hip_main" else f"HIP {obj_id.replace('HIP', '').strip() or obj_id}",
                "ra_deg": float(ra),
                "dec_deg": float(dec),
                "mag_v": float(_clamp(mag_v, -1.0, 40.0)),
                "otype": otype,
            }
        )

    return {
        "meta": {
            "provider": "vizier",
            "catalog": q.catalog,
            "mode": "online",
            "upstream": {"kind": "tap", "url": url},
            "query": {
                "catalog": q.catalog,
                "ra_deg": float(q.ra_deg),
                "dec_deg": float(q.dec_deg),
                "radius_deg": float(q.radius_deg),
                "max_rows": int(q.max_rows),
            },
        },
        "sources": sources,
    }


def query_vizier_catalog(
    *,
    catalog: str,
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    max_rows: int,
) -> Dict[str, Any]:
    """Query a VizieR-like catalog.

    Default mode is offline deterministic fixture data.
    Online queries are opt-in and safe-to-fail.
    """

    mode = str(os.getenv(CATALOG_MODE_ENV, "fixture") or "fixture").strip().lower()
    if mode not in ("fixture", "online"):
        mode = "fixture"

    cat = _validate_vizier_catalog_id(catalog)
    ra = _normalize_ra_deg(ra_deg)
    dec = _validate_dec_deg(dec_deg)
    radius = _validate_radius_deg(radius_deg)
    max_rows_i = int(max_rows)
    if max_rows_i < 1:
        raise ValueError("maxRows must be >= 1")
    max_rows_i = min(max_rows_i, 2000)

    q = VizierCatalogQuery(
        catalog=cat,
        ra_deg=float(ra),
        dec_deg=float(dec),
        radius_deg=float(radius),
        max_rows=int(max_rows_i),
    )

    if mode == "online":
        allowed = _vizier_online_allowlist()
        if cat not in allowed:
            raise ValueError("catalog not allowed for online mode")

        key = _cache_key_vizier(q)
        cached = _cache_get(key)
        if cached is not None:
            try:
                cached_meta = cached.get("meta") if isinstance(cached, dict) else None
                if isinstance(cached_meta, dict):
                    cached_meta["cached"] = True
            except Exception:
                pass
            return cached

        fallback = _env_bool(CATALOG_ONLINE_FALLBACK_ENV, True)
        try:
            out = _query_vizier_online(q)
            try:
                out_meta = out.get("meta") if isinstance(out, dict) else None
                if isinstance(out_meta, dict):
                    out_meta["cached"] = False
            except Exception:
                pass
            _cache_set(key, out)
            return out
        except Exception as e:
            if not fallback:
                raise
            mode = "fixture"
            requested_mode = "online"
            fallback_reason = f"{type(e).__name__}"

    seed = _seed_for_vizier_query(catalog=cat, ra=ra, dec=dec, radius=radius, max_rows=max_rows_i)
    rng = random.Random(seed)

    cap = math.radians(radius)
    area_frac = (1.0 - math.cos(cap)) / 2.0
    expected = int(_clamp(3500.0 * area_frac, 10.0, float(max_rows_i)))
    n = int(_clamp(expected + rng.randint(-3, 3), 1.0, float(max_rows_i)))

    sources: List[Dict[str, Any]] = []
    for i in range(n):
        sra, sdec = _sample_on_cap(rng, ra0_deg=ra, dec0_deg=dec, radius_deg=radius)
        mag_v = _clamp(rng.gauss(11.0, 2.4), -1.0, 22.0)
        sources.append(
            {
                "id": f"VIZIER:FIX:{cat}:{seed:x}:{i}",
                "name": f"MockCatalog-{cat}-{(seed + i) % 100000:05d}",
                "ra_deg": float(sra),
                "dec_deg": float(sdec),
                "mag_v": float(mag_v),
                "otype": "Star",
            }
        )

    meta: Dict[str, Any] = {
        "provider": "vizier",
        "catalog": cat,
        "mode": mode,
        "query": {
            "catalog": cat,
            "ra_deg": float(ra),
            "dec_deg": float(dec),
            "radius_deg": float(radius),
            "max_rows": int(max_rows_i),
        },
    }
    if mode == "fixture" and "requested_mode" in locals():
        meta["requested_mode"] = requested_mode
        meta["fallback_reason"] = fallback_reason

    return {
        "meta": {**meta},
        "sources": sources,
    }
