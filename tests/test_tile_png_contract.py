import asyncio
import struct
import sys
import types
import zlib
from pathlib import Path


# Match existing tests: import backend modules by adding backend/ to sys.path.
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


def _install_fast_import_stubs() -> None:
    """Keep this suite fast/offline by stubbing heavy optional dependencies."""

    # Earth Engine SDK import can be slow and may try to read auth/config.
    if "ee" not in sys.modules:
        sys.modules["ee"] = types.ModuleType("ee")

    # backend/main.py imports llm_service at import-time.
    if "llm_service" not in sys.modules:
        m = types.ModuleType("llm_service")

        async def _noop_async(*_args, **_kwargs):
            return ""

        m.generate_monitoring_brief_openai_compatible = _noop_async
        m.generate_agent_analysis_openai_compatible = _noop_async
        sys.modules["llm_service"] = m


_install_fast_import_stubs()


def _parse_png_chunks(png: bytes):
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    i = 8
    chunks = []
    while i < len(png):
        if i + 8 > len(png):
            raise AssertionError("Truncated PNG")
        length = struct.unpack(">I", png[i : i + 4])[0]
        ctype = png[i + 4 : i + 8]
        data_start = i + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(png):
            raise AssertionError("Truncated PNG chunk")
        data = png[data_start:data_end]
        chunks.append((ctype, data))
        i = crc_end
        if ctype == b"IEND":
            break
    return chunks


def test_ai_modes_request_png_format():
    from gee_service import get_mode_vis_and_suffix

    for mode in [
        "ch1_yuhang_faceid",
        "ch2_maowusu_shield",
        "ch3_zhoukou_pulse",
        "ch4_amazon_zeroshot",
        "ch5_coastline_audit",
        "ch6_water_pulse",
    ]:
        vis, _suffix = get_mode_vis_and_suffix(mode)
        assert vis.get("format") == "png"


def test_get_tile_url_defaults_png_but_respects_explicit_format():
    from gee_service import get_tile_url

    class _TF:
        url_format = "https://example.com/{z}/{x}/{y}"

    class FakeImage:
        def __init__(self):
            self.last_vis = None

        def getMapId(self, vis):
            self.last_vis = dict(vis)
            return {"tile_fetcher": _TF()}

    img = FakeImage()
    url = get_tile_url(img, {"min": 0, "max": 1})
    assert url.endswith("{z}/{x}/{y}")
    assert img.last_vis.get("format") == "png"

    img2 = FakeImage()
    url2 = get_tile_url(img2, {"min": 0, "max": 1, "format": "jpg"})
    assert url2.endswith("{z}/{x}/{y}")
    assert img2.last_vis.get("format") == "jpg"


def test_fallback_png_is_valid_rgba_256_tile():
    from main import _TRANSPARENT_PNG_256

    chunks = _parse_png_chunks(_TRANSPARENT_PNG_256)
    ihdr = [d for (t, d) in chunks if t == b"IHDR"]
    assert len(ihdr) == 1

    width, height, bit_depth, color_type, comp, flt, interlace = struct.unpack(">IIBBBBB", ihdr[0])
    assert width == 256
    assert height == 256
    assert bit_depth == 8
    assert color_type == 6  # RGBA
    assert comp == 0
    assert flt == 0
    assert interlace == 0

    idat_parts = [d for (t, d) in chunks if t == b"IDAT"]
    assert idat_parts, "Expected at least one IDAT chunk"
    raw = zlib.decompress(b"".join(idat_parts))

    # Each row: 1 filter byte + 4*width bytes
    expected_row = 1 + 4 * width
    assert len(raw) == expected_row * height

    # First byte of each row is filter=0
    assert all(raw[r * expected_row] == 0 for r in range(height))

    # All pixels must be 0 (RGBA fully transparent black)
    pixel_bytes = bytearray()
    for r in range(height):
        start = r * expected_row + 1
        pixel_bytes.extend(raw[start : start + 4 * width])
    assert all(b == 0 for b in pixel_bytes)


def test_tile_fallback_response_contract():
    from main import _tile_fallback_response

    resp = _tile_fallback_response(
        ("dummy", 0, 0, 0),
        max_age_s=30,
        reason="unit-test",
        upstream_status=404,
    )
    assert resp.media_type == "image/png"
    assert resp.headers.get("X-AEF-Tile-Fallback") == "1"
    assert resp.headers.get("X-AEF-Upstream-Status") == "404"
    assert resp.body.startswith(b"\x89PNG\r\n\x1a\n")


def test_ch5_fallback_mask_removed():
    # Pure static check: ch5 should never recolor unknowns to mudflat.
    src = (backend_path / "gee_service.py").read_text(encoding="utf-8")
    assert "fallback_mask" not in src
    assert "CH5_FALLBACK_MASK" not in src


def test_embedding_layers_use_filterbounds_to_avoid_global_mosaic_timeouts():
    # Pure static check: keeps the test offline and fast.
    src = (backend_path / "gee_service.py").read_text(encoding="utf-8")
    lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    code = "\n".join(lines)
    assert ".filterBounds(region)" in code


def test_sentinel2_endpoint_uses_filterbounds_to_avoid_global_mosaic_timeouts():
    # Bound the collection: global S2 + mosaic() can cause macro-zoom timeouts.
    src = (backend_path / "main.py").read_text(encoding="utf-8")
    assert "@app.get(\"/api/sentinel2\")" in src
    lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    code = "\n".join(lines)
    assert ".filterBounds(viewport)" in code
    assert "CLOUDY_PIXEL_PERCENTAGE\", 45" in src
    assert "filterDate(\"2024-05-01\", \"2024-10-31\")" in src


def test_proxy_tile_cancelled_returns_499_quickly():
    # Import backend main reliably.
    sys.modules.pop("main", None)
    import main as main_module

    main_module.gee_initialized = True
    main_module.http_client = object()

    tile_id = main_module._register_tile_template("https://example.com/{z}/{x}/{y}")
    cache_key = (tile_id, 0, 0, 0)
    # Pre-create inflight event so the call becomes a non-owner waiter.
    main_module._tile_inflight[cache_key] = asyncio.Event()

    async def _run():
        t = asyncio.create_task(
            main_module.proxy_gee_tile(tile_id=tile_id, z=0, x=0, y=0, fallback="transparent")
        )
        await asyncio.sleep(0)
        t.cancel()
        return await t

    resp = asyncio.run(_run())
    assert resp.status_code == 499
