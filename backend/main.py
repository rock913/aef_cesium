"""FastAPI Backend for Cesium App

提供 RESTful API 端点，连接前端和 GEE 服务。

关键点：Earth Engine 的 tile server 在浏览器环境下通常不返回 CORS 允许头，
Cesium(WebGL texture) 会因此拒绝加载瓦片并表现为“地图空白”。
因此这里提供后端同源瓦片代理端点，把 tile 请求变为后端自身域名响应。
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
import ee
from typing import Optional, Any, Dict, List
import base64
import json
import hashlib
import time
import asyncio
import concurrent.futures
import os
import threading
import uuid
import sys
import subprocess
from urllib.parse import urlparse, urlsplit, urlunsplit
from collections import defaultdict
from collections import OrderedDict
import httpx

from config import settings
from llm_service import (
    generate_monitoring_brief_openai_compatible,
    generate_agent_analysis_openai_compatible,
)
from gee_service import (
    smart_load,
    get_tile_url,
    get_layer_logic,
    compute_zonal_stats,
    trigger_export_task,
    init_earth_engine
)


# 创建 FastAPI 应用
app = FastAPI(
    title="AlphaEarth Cesium API",
    description="后端 API 用于 Cesium 3D 地球可视化",
    version="1.0.0"
)


# --- Debug / observability ---
_debug_lock = threading.Lock()
_debug_counters: "defaultdict[str, int]" = defaultdict(int)


@app.middleware("http")
async def _request_id_middleware(request: Request, call_next):
    """Attach a stable request id for correlating browser/Vite/backend logs.

    - Client may send `X-AEF-Request-Id` (we propagate it).
    - Otherwise we generate one and return it in `X-AEF-Request-Id`.
    """

    rid = request.headers.get("x-aef-request-id")
    if not rid:
        rid = uuid.uuid4().hex
    request.state.request_id = rid

    try:
        resp = await call_next(request)
    except Exception:
        with _debug_lock:
            _debug_counters["unhandled_exceptions_total"] += 1
        raise

    try:
        resp.headers["X-AEF-Request-Id"] = rid
    except Exception:
        pass
    return resp

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=False,  # 允许所有来源时必须为 False
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic 模型
class ExportRequest(BaseModel):
    """缓存导出请求模型"""
    mode: str
    location: str


class StatsRequest(BaseModel):
    """Zonal statistics request."""

    mode: str
    location: str
    # Optional overrides
    scale_m: Optional[int] = None


class ReportRequest(BaseModel):
    """Monitoring brief generation request.

    If `stats` is provided, the endpoint will NOT require GEE.
    Otherwise, it will compute stats in the cloud (requires GEE initialized).
    """

    mission_id: str
    stats: Optional[Dict[str, Any]] = None
    # Optional overrides (when computing stats server-side)
    mode: Optional[str] = None
    location: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Agent analysis request.

    If `stats` is provided, the endpoint will NOT require GEE.
    Otherwise, it will compute stats in the cloud (requires GEE initialized).
    """

    mission_id: str
    stats: Optional[Dict[str, Any]] = None
    # Optional overrides (when computing stats server-side)
    mode: Optional[str] = None
    location: Optional[str] = None


def _get_mission_by_id(mission_id: str) -> Optional[Dict[str, Any]]:
    for m in settings.missions:
        if m.get("id") == mission_id:
            return m
    return None


def _render_agent_analysis_template(mission: Dict[str, Any], stats: Dict[str, Any]) -> str:
    title = mission.get("title", "")
    narrative = mission.get("narrative", "")
    formula = mission.get("formula", "")
    mode_id = mission.get("api_mode", "")
    location = mission.get("location", "")

    total = stats.get("total_area_km2")
    anomaly = stats.get("anomaly_area_km2")
    pct = stats.get("anomaly_pct")

    def _fmt(x: Any) -> str:
        if x is None:
            return "—"
        try:
            return f"{float(x):.2f}"
        except Exception:
            return str(x)

    return (
        "AEF/AGENT v6 :: Mission Accepted\n"
        "----------------------------------------\n\n"
        "【异动感知 Observation】\n"
        f"- 任务：{title}\n"
        f"- 模式：{mode_id}（{formula}）\n"
        f"- 目标：{location}\n"
        f"- 统计：总面积 {_fmt(total)} km²；异常面积 {_fmt(anomaly)} km²；异常占比 {_fmt(pct)}%\n\n"
        "【归因分析 Reasoning】\n"
        f"- 叙事背景：{narrative}\n"
        "- 若异常呈连片且跨期稳定，更可能是结构性演变；若呈零散点状，建议优先排查云/阴影/季节扰动。\n"
        "- 建议结合 Sentinel-2 目视核查，确认边界与成因。\n\n"
        "【行动规划 Plan】\n"
        "- ① 将异常占比高的网格列入优先核查清单（按行政/网格编号输出）。\n"
        "- ② 拉取 Sentinel-2/历史影像做跨期对比，给出‘发生时间窗’与‘扩展方向’。\n"
        "- ③ 对高风险边界开展抽样外业/第三方数据交叉验证（若条件允许）。\n"
        "- ④ 将处置动作形成闭环台账：发现→核查→处置→复核。\n\n"
        "【共识印证 Consensus】\n"
        "- 本次结果为新闻/叙事提供了可复核的量化证据锚点，可用于对外沟通与跨部门复核。\n"
        "- 建议明确不确定性来源（季节/云影/尺度），避免把短期视觉变化误判为长期成果或风险。\n"
    )


class MissionCamera(BaseModel):
    lat: float
    lon: float
    height: float
    duration_s: float
    heading_deg: Optional[float] = None
    pitch_deg: Optional[float] = None


class Mission(BaseModel):
    id: str
    name: str
    title: str
    location: str
    api_mode: str
    formula: str
    narrative: str
    camera: MissionCamera


# 全局状态
gee_initialized = False

_gee_init_lock = threading.Lock()
_gee_last_error: Optional[str] = None
_gee_last_attempt_ts: float = 0.0
_gee_last_success_ts: float = 0.0
_gee_min_retry_interval_s: float = float(os.getenv("GEE_INIT_RETRY_INTERVAL_S", "15"))
_gee_init_timeout_s: float = float(os.getenv("GEE_INIT_TIMEOUT_S", "6"))
_gee_init_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_gee_init_future: Optional[concurrent.futures.Future] = None


def _gee_unavailable_detail() -> Dict[str, Any]:
    """Structured error payload for endpoints that require GEE."""

    # Do not leak secrets; only surface presence and basic guidance.
    service_account = str(os.getenv("EE_SERVICE_ACCOUNT", "")).strip()
    key_file = str(os.getenv("EE_PRIVATE_KEY_FILE", "")).strip()
    key_b64 = str(os.getenv("EE_PRIVATE_KEY_JSON_B64", "")).strip()

    return {
        "error": "gee_not_initialized",
        "message": "GEE not initialized",
        "gee_initialized": bool(gee_initialized),
        "last_error": _gee_last_error,
        "hint": (
            "Configure a service account for production via EE_SERVICE_ACCOUNT and "
            "EE_PRIVATE_KEY_FILE (recommended), or EE_PRIVATE_KEY_JSON_B64. "
            "Then restart the backend (or wait for lazy re-init)."
        ),
        "env": {
            "EE_SERVICE_ACCOUNT_set": bool(service_account),
            "EE_PRIVATE_KEY_FILE_set": bool(key_file),
            "EE_PRIVATE_KEY_JSON_B64_set": bool(key_b64),
        },
    }


def _ensure_gee_initialized(*, force: bool = False) -> bool:
    """Best-effort GEE init.

    Returns True if initialized; False otherwise.
    Throttles repeated init attempts to avoid stampeding under load.
    """

    global gee_initialized, _gee_last_error, _gee_last_attempt_ts, _gee_last_success_ts, _gee_init_future

    if gee_initialized and not force:
        return True

    now = time.time()
    if not force and _gee_min_retry_interval_s > 0:
        if (now - float(_gee_last_attempt_ts)) < float(_gee_min_retry_interval_s):
            return False

    with _gee_init_lock:
        if gee_initialized and not force:
            return True

        # If an init is already running, don't block other requests.
        if _gee_init_future is not None:
            if not _gee_init_future.done():
                return False
            try:
                _gee_init_future.result()
                gee_initialized = True
                _gee_last_error = None
                _gee_last_success_ts = time.time()
                _gee_init_future = None
                return True
            except Exception as e:
                gee_initialized = False
                _gee_last_error = f"{type(e).__name__}: {e}"
                _gee_init_future = None
                return False

        now = time.time()
        if not force and _gee_min_retry_interval_s > 0:
            if (now - float(_gee_last_attempt_ts)) < float(_gee_min_retry_interval_s):
                return False

        # Kick off init in a background thread; allow a bounded wait for fast paths.
        _gee_last_attempt_ts = now
        _gee_init_future = _gee_init_executor.submit(init_earth_engine)

    # Wait outside the lock so other requests can fail fast (503) instead of hanging.
    try:
        _gee_init_future.result(timeout=max(0.0, float(_gee_init_timeout_s)))
        with _gee_init_lock:
            gee_initialized = True
            _gee_last_error = None
            _gee_last_success_ts = time.time()
            _gee_init_future = None
        return True
    except concurrent.futures.TimeoutError:
        return False
    except Exception as e:
        with _gee_init_lock:
            gee_initialized = False
            _gee_last_error = f"{type(e).__name__}: {e}"
            _gee_init_future = None
        return False


def _require_gee() -> None:
    if _ensure_gee_initialized(force=False):
        return
    # Use a small retry-after; callers can back off and retry.
    raise HTTPException(
        status_code=503,
        detail=_gee_unavailable_detail(),
        headers={"Retry-After": "5"},
    )


@app.get("/api/debug/gee")
async def debug_gee_status():
    """Diagnostics for GEE-backed endpoints (e.g. /api/stats)."""

    with _gee_init_lock:
        init_in_progress = bool(_gee_init_future is not None and not _gee_init_future.done())
        last_error = _gee_last_error
        last_attempt_ts = _gee_last_attempt_ts
        last_success_ts = _gee_last_success_ts

    return {
        "gee_initialized": bool(gee_initialized),
        "init_in_progress": init_in_progress,
        "last_error": last_error,
        "last_attempt_ts": last_attempt_ts,
        "last_success_ts": last_success_ts,
        "min_retry_interval_s": float(_gee_min_retry_interval_s),
        "init_timeout_s": float(_gee_init_timeout_s),
    }

# Global async HTTP client (connection pool) for high-concurrency tile proxying
http_client: Optional[httpx.AsyncClient] = None

# --- Cesium Ion / Google photorealistic 3D tiles proxy ---
# Motivation: client networks (e.g. mainland China) may not reach Cesium Ion / Google tile
# domains reliably, while the backend server can. We proxy through same-origin `/api/*`.
_ION_API_BASE = str(os.getenv("ION_API_BASE", "https://api.cesium.com")).strip().rstrip("/")
_ION_ASSETS_BASE = str(os.getenv("ION_ASSETS_BASE", "https://assets.cesium.com")).strip().rstrip("/")
_GOOGLE_TILES_BASE = str(os.getenv("GOOGLE_TILES_BASE", "https://tile.googleapis.com")).strip().rstrip("/")
_GOOGLE_MAPS_API_KEY = str(os.getenv("GOOGLE_MAPS_API_KEY", "")).strip()

# Optional server-side Ion token for diagnostics (avoid relying on browser-provided token).
# If set, `/api/debug/ion` can validate upstream reachability without requiring
# callers to provide `Authorization`.
_ION_ACCESS_TOKEN = str(os.getenv("ION_ACCESS_TOKEN", "")).strip()

_ion_upstream_timeout_s = float(os.getenv("ION_UPSTREAM_TIMEOUT_S", "25"))
_google_tiles_timeout_s = float(os.getenv("GOOGLE_TILES_TIMEOUT_S", str(_ion_upstream_timeout_s)))
_ion_upstream_max_concurrency = int(os.getenv("ION_UPSTREAM_MAX_CONCURRENCY", "32"))
_ion_upstream_sem = asyncio.Semaphore(max(1, _ion_upstream_max_concurrency))


# --- Upstream diagnostics (Ion API / Ion assets / Google tiles) ---
_upstream_diag_lock = threading.Lock()
_upstream_diag: Dict[str, Dict[str, Any]] = {
    "ion_api": {"last_ts": None, "last_ok_ts": None, "last_status": None, "last_latency_ms": None, "last_error": None},
    "ion_assets": {"last_ts": None, "last_ok_ts": None, "last_status": None, "last_latency_ms": None, "last_error": None},
    "google_tiles": {"last_ts": None, "last_ok_ts": None, "last_status": None, "last_latency_ms": None, "last_error": None},
}


def _diag_key_for_upstream_url(upstream_url: str) -> Optional[str]:
    try:
        u = str(upstream_url or "")
        if not u:
            return None
        if u.startswith(_ION_API_BASE):
            return "ion_api"
        if u.startswith(_ION_ASSETS_BASE):
            return "ion_assets"
        if u.startswith(_GOOGLE_TILES_BASE):
            return "google_tiles"
    except Exception:
        return None
    return None


def _record_upstream_diag(
    key: Optional[str],
    *,
    status: Optional[int] = None,
    latency_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    if not key:
        return
    now = time.time()
    with _upstream_diag_lock:
        entry = _upstream_diag.get(key) or {}
        entry["last_ts"] = now
        if status is not None:
            entry["last_status"] = int(status)
        if latency_ms is not None:
            try:
                entry["last_latency_ms"] = float(latency_ms)
            except Exception:
                entry["last_latency_ms"] = None
        if error:
            entry["last_error"] = str(error)[:500]
        if status is not None and 200 <= int(status) < 300 and not error:
            entry["last_ok_ts"] = now
            entry["last_error"] = None
        _upstream_diag[key] = entry


def _strip_hop_by_hop_headers(headers: Dict[str, str]) -> Dict[str, str]:
    hop_by_hop = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    out: Dict[str, str] = {}
    for k, v in (headers or {}).items():
        if k.lower() in hop_by_hop:
            continue
        out[k] = v
    return out


def _rewrite_urls_in_json(value: Any, replacements: List[tuple]) -> Any:
    if isinstance(value, str):
        s = value
        for old, new in replacements:
            if old in s:
                s = s.replace(old, new)
        return s
    if isinstance(value, list):
        return [_rewrite_urls_in_json(v, replacements) for v in value]
    if isinstance(value, dict):
        return {k: _rewrite_urls_in_json(v, replacements) for k, v in value.items()}
    return value


def _proxy_request_headers(request: Request, *, accept_encoding_identity: bool) -> Dict[str, str]:
    # Keep it tight: forward only what we need; especially important for Range.
    want = {
        # Cesium Ion API uses Bearer tokens; without forwarding this header
        # the proxy will always get 401 and the frontend shows blank 3D tiles.
        "authorization",
        "range",
        "if-none-match",
        "if-modified-since",
        "accept",
        "accept-language",
        "user-agent",
        "referer",
    }
    out: Dict[str, str] = {}
    for k in want:
        v = request.headers.get(k)
        if v:
            out[k] = v
    if accept_encoding_identity:
        # Avoid transparent decompression that can confuse Content-Length/Range.
        out["accept-encoding"] = "identity"
    return out


async def _proxy_stream(
    request: Request,
    *,
    upstream_url: str,
    acquire_timeout_s: float = 1.5,
    timeout_s: Optional[float] = None,
    extra_params: Optional[Dict[str, str]] = None,
) -> Response:
    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    method = request.method.upper()
    if method not in {"GET", "HEAD"}:
        raise HTTPException(status_code=405, detail="Method not allowed")

    timeout_val = float(timeout_s) if timeout_s is not None else float(_ion_upstream_timeout_s)
    # Use explicit httpx.Timeout to avoid compatibility issues across httpx/httpcore versions.
    timeout_cfg = httpx.Timeout(timeout_val)

    diag_key = _diag_key_for_upstream_url(upstream_url)
    try:
        try:
            await asyncio.wait_for(_ion_upstream_sem.acquire(), timeout=max(0.1, float(acquire_timeout_s)))
        except Exception:
            raise HTTPException(status_code=503, detail="Upstream busy")

        headers = _proxy_request_headers(request, accept_encoding_identity=True)
        params = dict(request.query_params)
        if extra_params:
            for k, v in extra_params.items():
                if v is None:
                    continue
                if k not in params and str(v).strip() != "":
                    params[k] = v

        t0 = time.perf_counter()

        if method == "HEAD":
            resp = await http_client.request(
                "HEAD",
                upstream_url,
                params=params,
                headers=headers,
                timeout=timeout_cfg,
                follow_redirects=True,
            )
            _record_upstream_diag(
                diag_key,
                status=int(resp.status_code),
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                error=None,
            )
            out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
            out_headers["X-OneEarth-Proxy-Mode"] = "stream"
            return Response(status_code=int(resp.status_code), headers=out_headers)

        # IMPORTANT: do NOT use `async with http_client.stream(...) as upstream_resp` here.
        # Returning a StreamingResponse would exit the context manager immediately,
        # closing the upstream stream before Starlette starts consuming it, which
        # manifests as `httpx.StreamClosed` and (behind reverse proxies) 502.
        req = http_client.build_request(
            "GET",
            upstream_url,
            params=params,
            headers=headers,
            timeout=timeout_cfg,
        )
        upstream_resp = await http_client.send(
            req,
            stream=True,
            follow_redirects=True,
        )

        _record_upstream_diag(
            diag_key,
            status=int(upstream_resp.status_code),
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            error=None,
        )
        out_headers = _strip_hop_by_hop_headers(dict(upstream_resp.headers))
        # For streamed bodies we must not forward upstream Content-Length.
        # Any mid-stream disconnect or buffering can result in fewer bytes than
        # advertised and triggers `net::ERR_CONTENT_LENGTH_MISMATCH` in browsers.
        #
        # Also strip Content-Encoding defensively: if any upstream ignores our
        # `accept-encoding: identity`, httpx may decode the body but we would
        # otherwise still forward the encoding header.
        out_headers = {k: v for k, v in out_headers.items() if k.lower() not in {"content-length", "content-encoding"}}
        out_headers["X-OneEarth-Proxy-Mode"] = "stream"
        status = int(upstream_resp.status_code)

        async def _iter_bytes():
            try:
                async for chunk in upstream_resp.aiter_bytes():
                    yield chunk
            except httpx.StreamClosed:
                # Upstream stream got closed unexpectedly.
                return
            except asyncio.CancelledError:
                # Client disconnected/cancelled request.
                return
            finally:
                try:
                    await upstream_resp.aclose()
                except Exception:
                    pass

        return StreamingResponse(
            _iter_bytes(),
            status_code=status,
            headers=out_headers,
        )
    except httpx.TimeoutException as e:
        _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"timeout: {e}")
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.RequestError as e:
        _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"request_error: {e}")
        raise HTTPException(status_code=502, detail="Upstream request error")
    except Exception as e:
        _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"exception: {e}")
        raise
    finally:
        try:
            _ion_upstream_sem.release()
        except Exception:
            pass


async def _proxy_buffered(
    request: Request,
    *,
    upstream_url: str,
    acquire_timeout_s: float = 1.5,
    timeout_s: Optional[float] = None,
    retries: int = 1,
) -> Response:
    """Buffer upstream response fully before responding.

    This avoids browser-visible `ERR_INCOMPLETE_CHUNKED_ENCODING` when the upstream
    disconnects mid-stream (common on some networks) by retrying and only sending
    bytes once the full body is available.
    """

    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    method = request.method.upper()
    if method not in {"GET", "HEAD"}:
        raise HTTPException(status_code=405, detail="Method not allowed")

    timeout_val = float(timeout_s) if timeout_s is not None else float(_ion_upstream_timeout_s)
    diag_key = _diag_key_for_upstream_url(upstream_url)

    try:
        try:
            await asyncio.wait_for(_ion_upstream_sem.acquire(), timeout=max(0.1, float(acquire_timeout_s)))
        except Exception:
            raise HTTPException(status_code=503, detail="Upstream busy")

        headers = _proxy_request_headers(request, accept_encoding_identity=True)
        params = dict(request.query_params)

        last_error: Optional[Exception] = None
        for attempt in range(max(0, int(retries)) + 1):
            if attempt > 0:
                await asyncio.sleep(min(0.8, 0.2 * (2** (attempt - 1))))

            t0 = time.perf_counter()
            try:
                if method == "HEAD":
                    resp = await http_client.request(
                        "HEAD",
                        upstream_url,
                        params=params,
                        headers=headers,
                        timeout=timeout_val,
                        follow_redirects=True,
                    )
                    _record_upstream_diag(
                        diag_key,
                        status=int(resp.status_code),
                        latency_ms=(time.perf_counter() - t0) * 1000.0,
                        error=None,
                    )
                    out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
                    out_headers["X-OneEarth-Proxy-Mode"] = "buffered"
                    return Response(status_code=int(resp.status_code), headers=out_headers)

                resp = await http_client.get(
                    upstream_url,
                    params=params,
                    headers=headers,
                    timeout=timeout_val,
                    follow_redirects=True,
                )

                _record_upstream_diag(
                    diag_key,
                    status=int(resp.status_code),
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    error=None,
                )

                out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
                out_headers = {
                    k: v
                    for k, v in out_headers.items()
                    if k.lower() not in {"content-length", "content-encoding", "transfer-encoding", "content-type"}
                }
                out_headers["X-OneEarth-Proxy-Mode"] = "buffered"

                content_type = resp.headers.get("content-type") or "application/octet-stream"
                media_type = content_type.split(";")[0].strip() or "application/octet-stream"
                return Response(
                    content=resp.content,
                    status_code=int(resp.status_code),
                    headers=out_headers,
                    media_type=media_type,
                )
            except httpx.TimeoutException as e:
                last_error = e
                _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"timeout: {e}")
            except httpx.RequestError as e:
                last_error = e
                _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"request_error: {e}")
            except Exception as e:
                last_error = e
                _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"exception: {e}")

        if isinstance(last_error, httpx.TimeoutException):
            raise HTTPException(status_code=504, detail="Upstream timeout")
        raise HTTPException(status_code=502, detail="Upstream request error")
    finally:
        try:
            _ion_upstream_sem.release()
        except Exception:
            pass


async def _proxy_google_tiles_json_with_rewrite(
    request: Request,
    *,
    upstream_url: str,
    acquire_timeout_s: float = 1.5,
    timeout_s: Optional[float] = None,
    retries: int = 1,
    extra_params: Optional[Dict[str, str]] = None,
) -> Response:
    """Fetch Google tiles JSON and rewrite embedded URIs to remain same-origin.

    Google 3D Tiles metadata can contain absolute-path URIs like `/v1/3dtiles/...`.
    When the root JSON is served from `/api/google-tiles/...`, those absolute-path
    references escape the proxy and the browser requests `/v1/3dtiles/...` directly
    from our origin, often receiving `index.html`/404, leading Cesium to report
    `Invalid tile content`.
    """

    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    method = request.method.upper()
    if method not in {"GET", "HEAD"}:
        raise HTTPException(status_code=405, detail="Method not allowed")

    timeout_val = float(timeout_s) if timeout_s is not None else float(_ion_upstream_timeout_s)
    diag_key = _diag_key_for_upstream_url(upstream_url)

    try:
        try:
            await asyncio.wait_for(_ion_upstream_sem.acquire(), timeout=max(0.1, float(acquire_timeout_s)))
        except Exception:
            raise HTTPException(status_code=503, detail="Upstream busy")

        headers = _proxy_request_headers(request, accept_encoding_identity=True)
        params = dict(request.query_params)
        if extra_params:
            for k, v in extra_params.items():
                if v is None:
                    continue
                if k not in params and str(v).strip() != "":
                    params[k] = v

        last_error: Optional[Exception] = None
        for attempt in range(max(0, int(retries)) + 1):
            if attempt > 0:
                await asyncio.sleep(min(0.8, 0.2 * (2 ** (attempt - 1))))

            t0 = time.perf_counter()
            try:
                if method == "HEAD":
                    resp = await http_client.request(
                        "HEAD",
                        upstream_url,
                        params=params,
                        headers=headers,
                        timeout=timeout_val,
                        follow_redirects=True,
                    )
                    _record_upstream_diag(
                        diag_key,
                        status=int(resp.status_code),
                        latency_ms=(time.perf_counter() - t0) * 1000.0,
                        error=None,
                    )
                    out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
                    out_headers["X-OneEarth-Proxy-Mode"] = "buffered-json-rewrite"
                    return Response(status_code=int(resp.status_code), headers=out_headers)

                resp = await http_client.get(
                    upstream_url,
                    params=params,
                    headers=headers,
                    timeout=timeout_val,
                    follow_redirects=True,
                )
                _record_upstream_diag(
                    diag_key,
                    status=int(resp.status_code),
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    error=None,
                )

                # Pass through non-JSON or non-200 responses as buffered bytes.
                content_type = (resp.headers.get("content-type") or "").lower()
                if int(resp.status_code) != 200 or "json" not in content_type:
                    out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
                    out_headers = {
                        k: v
                        for k, v in out_headers.items()
                        if k.lower() not in {"content-length", "content-encoding", "transfer-encoding", "content-type"}
                    }
                    out_headers["X-OneEarth-Proxy-Mode"] = "buffered"
                    media_type = (resp.headers.get("content-type") or "application/octet-stream").split(";")[0].strip()
                    return Response(
                        content=resp.content,
                        status_code=int(resp.status_code),
                        headers=out_headers,
                        media_type=media_type or "application/octet-stream",
                    )

                try:
                    upstream_json = resp.json()
                except Exception:
                    # If JSON parsing fails, return bytes as-is.
                    out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
                    out_headers = {
                        k: v
                        for k, v in out_headers.items()
                        if k.lower() not in {"content-length", "content-encoding", "transfer-encoding", "content-type"}
                    }
                    out_headers["X-OneEarth-Proxy-Mode"] = "buffered"
                    return Response(
                        content=resp.content,
                        status_code=int(resp.status_code),
                        headers=out_headers,
                        media_type="application/json",
                    )

                # Rewrite absolute-path and upstream-host references to the proxy.
                replacements = [
                    ("https://tile.googleapis.com", "/api/google-tiles"),
                    ("http://tile.googleapis.com", "/api/google-tiles"),
                    ("//tile.googleapis.com", "/api/google-tiles"),
                    ("/v1/3dtiles", "/api/google-tiles/v1/3dtiles"),
                ]
                rewritten = _rewrite_urls_in_json(upstream_json, replacements)
                body = json.dumps(rewritten, ensure_ascii=False).encode("utf-8")

                out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
                out_headers = {
                    k: v
                    for k, v in out_headers.items()
                    if k.lower() not in {"content-length", "content-encoding", "transfer-encoding", "content-type"}
                }
                out_headers["X-OneEarth-Proxy-Mode"] = "buffered-json-rewrite"
                return Response(
                    content=body,
                    status_code=200,
                    headers=out_headers,
                    media_type="application/json",
                )

            except httpx.TimeoutException as e:
                last_error = e
                _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"timeout: {e}")
            except httpx.RequestError as e:
                last_error = e
                _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"request_error: {e}")
            except Exception as e:
                last_error = e
                _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"exception: {e}")

        if isinstance(last_error, httpx.TimeoutException):
            raise HTTPException(status_code=504, detail="Upstream timeout")
        raise HTTPException(status_code=502, detail="Upstream request error")
    finally:
        try:
            _ion_upstream_sem.release()
        except Exception:
            pass


async def _proxy_json_with_rewrite(request: Request, *, upstream_url: str) -> Response:
    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    diag_key = _diag_key_for_upstream_url(upstream_url)
    headers = _proxy_request_headers(request, accept_encoding_identity=True)
    params = dict(request.query_params)

    try:
        try:
            await asyncio.wait_for(_ion_upstream_sem.acquire(), timeout=1.5)
        except Exception:
            raise HTTPException(status_code=503, detail="Upstream busy")

        t0 = time.perf_counter()
        try:
            resp = await http_client.get(
                upstream_url,
                params=params,
                headers=headers,
                timeout=float(_ion_upstream_timeout_s),
                follow_redirects=True,
            )
        except httpx.TimeoutException as e:
            _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"timeout: {e}")
            raise HTTPException(status_code=504, detail="Upstream timeout")
        except httpx.RequestError as e:
            _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"request_error: {e}")
            raise HTTPException(status_code=502, detail="Upstream request error")
        finally:
            pass
    finally:
        try:
            _ion_upstream_sem.release()
        except Exception:
            pass

    _record_upstream_diag(
        diag_key,
        status=int(resp.status_code),
        latency_ms=(time.perf_counter() - t0) * 1000.0,
        error=None,
    )

    status = int(resp.status_code)
    content_type = str(resp.headers.get("Content-Type", "application/json"))

    # Only rewrite JSON bodies. For non-JSON, just return as-is.
    if "application/json" not in content_type.lower():
        out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
        body = resp.content
        return Response(content=body, status_code=status, headers=out_headers)

    try:
        data = resp.json()
    except Exception:
        # If upstream returns invalid JSON, just pass through.
        out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
        return Response(content=resp.content, status_code=status, headers=out_headers)

    # Rewrite upstream absolute URLs into our same-origin proxy endpoints.
    # Use relative URLs so they automatically stick to :8506.
    replacements = [
        ("https://assets.cesium.com", "/api/ion-assets"),
        ("http://assets.cesium.com", "/api/ion-assets"),
        ("https://tile.googleapis.com", "/api/google-tiles"),
        ("http://tile.googleapis.com", "/api/google-tiles"),
    ]
    data2 = _rewrite_urls_in_json(data, replacements)

    out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
    # Ensure correct content-type for rewritten JSON.
    out_headers["Content-Type"] = "application/json; charset=utf-8"
    # Body length changes after rewrite; never forward upstream content-length.
    for hk in list(out_headers.keys()):
        if hk.lower() == "content-length":
            out_headers.pop(hk, None)

    import json as _json

    body = _json.dumps(data2, ensure_ascii=False).encode("utf-8")
    return Response(content=body, status_code=status, headers=out_headers)


@app.get("/api/debug/ion")
async def debug_ion(request: Request, timeout_s: float = Query(default=3.0, ge=0.2, le=20.0)):
    """Runtime diagnostic for Cesium Ion upstream.

    Returns whether the backend can reach Ion API (200/401), upstream latency,
    and the last recorded proxy error.

    Auth sourcing order:
    1) Forward caller-provided `Authorization` header (recommended when debugging).
    2) Use server-side `ION_ACCESS_TOKEN` if configured.

    NEVER returns the token.
    """

    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    auth = request.headers.get("authorization")
    auth_source = "request" if auth else None
    if not auth and _ION_ACCESS_TOKEN:
        auth = _ION_ACCESS_TOKEN
        if not auth.lower().startswith("bearer "):
            auth = f"Bearer {auth}"
        auth_source = "env"

    if not auth:
        return {
            "ok": False,
            "error": "missing_authorization",
            "hint": "Provide Authorization: Bearer <ion_token> or set server env ION_ACCESS_TOKEN",
            "ion": {
                "api_base": _ION_API_BASE,
                "auth_source": None,
            },
            "last": dict(_upstream_diag.get("ion_api") or {}),
            "ts": time.time(),
        }

    headers = {
        "Authorization": auth,
        "Accept": "application/json",
        "User-Agent": "AlphaEarthCesium/2.0 debug",
    }

    upstream_url = f"{_ION_API_BASE}/v1/me"
    t0 = time.perf_counter()
    status = None
    err = None

    try:
        try:
            await asyncio.wait_for(_ion_upstream_sem.acquire(), timeout=1.5)
        except Exception:
            raise HTTPException(status_code=503, detail="Upstream busy")

        resp = await http_client.get(upstream_url, headers=headers, timeout=float(timeout_s), follow_redirects=True)
        status = int(resp.status_code)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        _record_upstream_diag("ion_api", status=status, latency_ms=latency_ms, error=None)

        ok = 200 <= status < 300
        return {
            "ok": bool(ok),
            "ts": time.time(),
            "ion": {
                "api_base": _ION_API_BASE,
                "endpoint": "/v1/me",
                "auth_source": auth_source,
            },
            "upstream": {
                "status": status,
                "latency_ms": round(float(latency_ms), 2),
                "content_type": str(resp.headers.get("Content-Type", ""))[:80],
            },
            "last": dict(_upstream_diag.get("ion_api") or {}),
        }
    except httpx.TimeoutException as e:
        err = f"timeout: {e}"
        _record_upstream_diag("ion_api", status=None, latency_ms=None, error=err)
        return {
            "ok": False,
            "ts": time.time(),
            "ion": {"api_base": _ION_API_BASE, "endpoint": "/v1/me", "auth_source": auth_source},
            "upstream": {"status": status, "latency_ms": None},
            "error": "upstream_timeout",
            "detail": str(e)[:200],
            "last": dict(_upstream_diag.get("ion_api") or {}),
        }
    except httpx.RequestError as e:
        err = f"request_error: {e}"
        _record_upstream_diag("ion_api", status=None, latency_ms=None, error=err)
        return {
            "ok": False,
            "ts": time.time(),
            "ion": {"api_base": _ION_API_BASE, "endpoint": "/v1/me", "auth_source": auth_source},
            "upstream": {"status": status, "latency_ms": None},
            "error": "upstream_request_error",
            "detail": str(e)[:200],
            "last": dict(_upstream_diag.get("ion_api") or {}),
        }
    finally:
        try:
            _ion_upstream_sem.release()
        except Exception:
            pass

# Basemap proxy (OSM). Motivation: some client networks cannot reach public OSM tiles
# (timeouts), while the server can. Proxying via same-origin keeps Cesium usable.
_OSM_TILE_URL_TEMPLATE = os.getenv(
    "OSM_TILE_URL_TEMPLATE",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
)

_basemap_upstream_max_concurrency = int(os.getenv("BASEMAP_UPSTREAM_MAX_CONCURRENCY", "16"))
_basemap_upstream_sem = asyncio.Semaphore(max(1, _basemap_upstream_max_concurrency))
_basemap_upstream_timeout_s = float(os.getenv("BASEMAP_UPSTREAM_TIMEOUT_S", "5"))

# 临时注册表：把上游 GEE tile URL 模板映射为一个短 ID
# /api/layers 返回的 tile_url 指向 /api/tiles/{tile_id}/{z}/{x}/{y}
_tile_registry_lock = threading.Lock()
_tile_registry = {}  # tile_id -> {"template": str, "created_at": float}
_tile_registry_max_size = 256

# In-memory TTL cache for upstream tile URL templates produced by ee.Image.getMapId().
# Keyed by (asset_id, vis_params_signature). Prevents repeated getMapId calls under
# prefetch / multi-client access patterns.
_layer_template_cache_lock = threading.Lock()
_layer_template_cache: "OrderedDict[str, tuple]" = OrderedDict()
_layer_template_cache_max_items = int(os.getenv("LAYER_TEMPLATE_MAX_ITEMS", "256"))
_layer_template_cache_ttl_s = float(os.getenv("LAYER_TEMPLATE_TTL_S", "900"))


def _layer_template_cache_key(asset_id: str, vis_params: Dict) -> str:
    import json

    try:
        sig = json.dumps(vis_params or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except Exception:
        sig = str(vis_params)
    return f"{asset_id}|{sig}"


def _layer_template_cache_get(key: str) -> Optional[str]:
    now = time.time()
    with _layer_template_cache_lock:
        entry = _layer_template_cache.get(key)
        if not entry:
            return None
        template, stored_at = entry
        if _layer_template_cache_ttl_s > 0 and (now - float(stored_at)) > _layer_template_cache_ttl_s:
            _layer_template_cache.pop(key, None)
            return None
        _layer_template_cache.move_to_end(key)
        return template


def _layer_template_cache_set(key: str, template: str) -> None:
    now = time.time()
    with _layer_template_cache_lock:
        _layer_template_cache[key] = (template, now)
        _layer_template_cache.move_to_end(key)
        while len(_layer_template_cache) > max(1, _layer_template_cache_max_items):
            _layer_template_cache.popitem(last=False)


# In-memory LRU cache for final rendered imagery tiles.
# Keyed by (tile_id, z, x, y).
# Stores (body bytes, media_type, headers dict, stored_at, nbytes).
_tile_cache_lock = threading.Lock()
_tile_cache: "OrderedDict[tuple, tuple]" = OrderedDict()
_tile_cache_max_items = int(__import__("os").getenv("TILE_LRU_MAX_ITEMS", "4096"))
_tile_cache_ttl_s = float(__import__("os").getenv("TILE_LRU_TTL_S", "600"))
_tile_cache_max_bytes = int(__import__("os").getenv("TILE_LRU_MAX_BYTES", str(64 * 1024 * 1024)))
_tile_cache_total_bytes = 0

# Limit concurrent upstream tile fetches to avoid rate-limits (429) / transient 5xx storms.
# Default is intentionally conservative for small servers.
_tile_upstream_max_concurrency = int(os.getenv("TILE_UPSTREAM_MAX_CONCURRENCY", "16"))
_tile_upstream_sem = asyncio.Semaphore(max(1, _tile_upstream_max_concurrency))

# NOTE: To avoid proxy-level 502 (nginx/SLB timing out before we can return our fallback),
# the tile proxy is intentionally time-bounded. Defaults are chosen to be < 5s.
_tile_upstream_timeout_s = float(os.getenv("TILE_UPSTREAM_TIMEOUT_S", "10"))
_tile_upstream_retries = int(os.getenv("TILE_UPSTREAM_RETRIES", "2"))
_tile_upstream_acquire_timeout_s = float(os.getenv("TILE_UPSTREAM_ACQUIRE_TIMEOUT_S", "2.5"))

# Total budget for serving a tile request (including inflight wait + semaphore queueing + retries).
# This should be lower than typical reverse-proxy timeouts (often 5s).
_tile_proxy_total_timeout_s = float(os.getenv("TILE_PROXY_TOTAL_TIMEOUT_S", "3.8"))
# Cap a single upstream GET attempt to leave room for cleanup/fallback and avoid long hangs.
_tile_proxy_per_attempt_timeout_s = float(os.getenv("TILE_PROXY_PER_ATTEMPT_TIMEOUT_S", "3.2"))

# Coalesce concurrent requests for the same tile to avoid upstream storms.
_tile_inflight_lock = asyncio.Lock()
_tile_inflight: Dict[tuple, asyncio.Event] = {}


def _tile_fallback_response(
    cache_key: tuple,
    *,
    max_age_s: int,
    reason: str,
    upstream_status: Optional[int] = None,
) -> Response:
    headers: Dict[str, str] = {
        "Cache-Control": f"public, max-age={int(max(1, max_age_s))}",
        "X-AEF-Tile-Fallback": "1",
        "X-AEF-Tile-Reason": str(reason)[:80],
        "X-AEF-Tile-Cache": "FALLBACK",
    }
    if upstream_status is not None:
        headers["X-AEF-Upstream-Status"] = str(int(upstream_status))

    with _debug_lock:
        _debug_counters["tile_fallback_total"] += 1
        _debug_counters[f"tile_fallback_reason__{str(reason)[:40]}"] += 1

    body = _TRANSPARENT_PNG_256
    media_type = "image/png"
    _tile_cache_set(cache_key, body, media_type, headers)
    return Response(content=body, media_type=media_type, headers=headers)


@app.get("/api/debug/config")
async def debug_config():
    """Debug endpoint: returns non-sensitive runtime configuration & counters."""

    # Snapshot sizes under locks where applicable.
    with _tile_registry_lock:
        tile_registry_size = len(_tile_registry)
    with _tile_cache_lock:
        tile_cache_items = len(_tile_cache)
        tile_cache_total_bytes = int(_tile_cache_total_bytes)
    with _debug_lock:
        counters = dict(_debug_counters)

    return {
        "ts": time.time(),
        "gee_initialized": gee_initialized,
        "tile_proxy": {
            "upstream_max_concurrency": int(_tile_upstream_max_concurrency),
            "upstream_timeout_s": float(_tile_upstream_timeout_s),
            "upstream_retries": int(_tile_upstream_retries),
            "upstream_acquire_timeout_s": float(_tile_upstream_acquire_timeout_s),
            "proxy_total_timeout_s": float(_tile_proxy_total_timeout_s),
            "proxy_per_attempt_timeout_s": float(_tile_proxy_per_attempt_timeout_s),
            "tile_lru": {
                "max_items": int(_tile_cache_max_items),
                "ttl_s": float(_tile_cache_ttl_s),
                "max_bytes": int(_tile_cache_max_bytes),
                "items": int(tile_cache_items),
                "total_bytes": int(tile_cache_total_bytes),
            },
            "tile_registry": {
                "max_size": int(_tile_registry_max_size),
                "size": int(tile_registry_size),
            },
        },
        "counters": counters,
    }


@app.get("/api/debug/version")
async def debug_version():
    """Debug endpoint: report runtime version info.

    Used to confirm which python/venv and which backend code is currently serving
    requests (helps when old uvicorn workers keep running after deploy).
    """

    git_head = None
    try:
        git_head = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=os.path.dirname(__file__))
            .decode("utf-8", errors="ignore")
            .strip()
        )
    except Exception:
        git_head = None

    # In release tarballs / Docker images, `.git/` is often not present.
    # Allow CI/CD to inject a stable build id for post-deploy verification.
    release_sha = (
        str(os.getenv("ONEEARTH_RELEASE_SHA", "")).strip()
        or str(os.getenv("ONEEARTH_GIT_HEAD", "")).strip()
        or str(os.getenv("GIT_SHA", "")).strip()
        or None
    )
    if not git_head and release_sha:
        git_head = release_sha

    httpcore_version = None
    try:
        import httpcore  # type: ignore

        httpcore_version = getattr(httpcore, "__version__", None)
    except Exception:
        httpcore_version = None

    return {
        "ts": time.time(),
        "git_head": git_head,
        "release": {
            "deployment": str(os.getenv("ONEEARTH_DEPLOYMENT", "")).strip() or None,
            "sha": release_sha,
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
        },
        "backend": {
            "main_file": __file__,
            "cwd": os.getcwd(),
        },
        "deps": {
            "httpx": getattr(httpx, "__version__", None),
            "httpcore": httpcore_version,
        },
        "notes": {
            "proxy_stream_timeout": "http_client.build_request(timeout=...)",
        },
    }


@app.get("/api/debug/tiles/{tile_id}")
async def debug_tile(tile_id: str):
    """Debug endpoint: introspect a tile_id without leaking upstream URL tokens."""

    with _tile_registry_lock:
        entry = _tile_registry.get(tile_id)
        entry = dict(entry) if entry else None

    if not entry:
        return {"tile_id": tile_id, "registered": False}

    template = str(entry.get("template") or "")
    created_at = float(entry.get("created_at") or 0.0)
    parsed = urlparse(template)
    template_sha256 = hashlib.sha256(template.encode("utf-8")).hexdigest() if template else None

    return {
        "tile_id": tile_id,
        "registered": True,
        "created_at": created_at,
        "age_s": max(0.0, time.time() - created_at) if created_at else None,
        "upstream": {
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path,
        },
        "template_sha256": template_sha256,
    }


def _tile_cache_get(key: tuple) -> Optional[tuple]:
    """Get a cached tile entry and refresh its LRU position."""
    now = time.time()
    with _tile_cache_lock:
        entry = _tile_cache.get(key)
        if not entry:
            return None
        body, media_type, headers, stored_at, _nbytes = entry
        if _tile_cache_ttl_s > 0 and (now - stored_at) > _tile_cache_ttl_s:
            _tile_cache_pop_nolock(key)
            return None
        _tile_cache.move_to_end(key)
        return entry


def _tile_cache_set(key: tuple, body: bytes, media_type: str, headers: Dict[str, str]) -> None:
    global _tile_cache_total_bytes
    now = time.time()
    with _tile_cache_lock:
        # Overwrite: subtract old entry size if present.
        if key in _tile_cache:
            _tile_cache_pop_nolock(key)

        nbytes = int(len(body) if body is not None else 0)
        _tile_cache[key] = (body, media_type, headers, now, nbytes)
        _tile_cache_total_bytes += nbytes
        _tile_cache.move_to_end(key)

        # Evict LRU items to keep bounded memory (item count and byte budget).
        max_items = max(1, int(_tile_cache_max_items))
        max_bytes = max(0, int(_tile_cache_max_bytes))

        # If max_bytes is 0, treat cache as disabled (but still allow a single entry via max_items).
        while len(_tile_cache) > max_items:
            _tile_cache_popitem_lru_nolock()

        if max_bytes > 0:
            while _tile_cache_total_bytes > max_bytes and len(_tile_cache) > 1:
                _tile_cache_popitem_lru_nolock()


def _tile_cache_pop_nolock(key: tuple) -> None:
    """Pop a cache entry and adjust byte accounting.

    Caller MUST hold _tile_cache_lock.
    """
    global _tile_cache_total_bytes
    entry = _tile_cache.pop(key, None)
    if not entry:
        return
    try:
        _nbytes = int(entry[4])
    except Exception:
        _nbytes = int(len(entry[0]) if entry[0] is not None else 0)
    _tile_cache_total_bytes = max(0, int(_tile_cache_total_bytes) - int(_nbytes))


def _tile_cache_popitem_lru_nolock() -> None:
    """Pop the least-recently-used entry and adjust byte accounting.

    Caller MUST hold _tile_cache_lock.
    """
    try:
        key, _val = _tile_cache.popitem(last=False)
    except KeyError:
        return
    # popitem already removed entry; adjust bytes by using the popped value
    global _tile_cache_total_bytes
    try:
        _nbytes = int(_val[4])
    except Exception:
        _nbytes = int(len(_val[0]) if _val and _val[0] is not None else 0)
    _tile_cache_total_bytes = max(0, int(_tile_cache_total_bytes) - int(_nbytes))

def _make_transparent_png(width: int, height: int) -> bytes:
    """Create a transparent RGBA PNG of the given size.

    Pure-Python implementation to avoid adding image dependencies.
    Cesium imagery tiles are typically 256x256; returning 1x1 can be treated as a failed tile.
    """
    import struct
    import zlib

    if width <= 0 or height <= 0:
        raise ValueError("Invalid PNG dimensions")

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA

    # Raw image data: each row starts with filter byte 0, then RGBA pixels
    row = b"\x00" + (b"\x00" * (width * 4))
    raw = row * height
    compressed = zlib.compress(raw, level=9)

    return signature + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")


# Transparent 256x256 PNG (valid imagery tile for Cesium when upstream has no data)
_TRANSPARENT_PNG_256 = _make_transparent_png(256, 256)


def _register_tile_template(tile_template: str) -> str:
    # 使用模板哈希作为稳定 ID，避免同一模板重复占用空间
    tile_id = hashlib.sha256(tile_template.encode("utf-8")).hexdigest()[:24]
    now = time.time()
    with _tile_registry_lock:
        _tile_registry[tile_id] = {"template": tile_template, "created_at": now}

        if len(_tile_registry) > _tile_registry_max_size:
            # 删除最老的若干条，保持 registry 有界
            to_delete = sorted(_tile_registry.items(), key=lambda kv: kv[1]["created_at"])[: max(1, len(_tile_registry) - _tile_registry_max_size)]
            for old_id, _ in to_delete:
                if old_id != tile_id:
                    _tile_registry.pop(old_id, None)

    return tile_id


def _get_registered_template(tile_id: str) -> Optional[str]:
    with _tile_registry_lock:
        entry = _tile_registry.get(tile_id)
        if not entry:
            return None
        return entry["template"]


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 GEE"""
    global gee_initialized, http_client
    try:
        _ensure_gee_initialized(force=True)
    except Exception as e:
        print(f"Warning: GEE initialization failed: {e}")
        gee_initialized = False

    # Create shared async client with a connection pool
    http_client = httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=100, max_connections=200),
        headers={"User-Agent": "AlphaEarthCesium/2.0"},
    )


@app.on_event("shutdown")
async def shutdown_event():
    global http_client
    if http_client is not None:
        await http_client.aclose()
        http_client = None


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "gee_initialized": gee_initialized,
        "gee_last_error": _gee_last_error,
        "version": "1.0.0"
    }


@app.get("/api/locations")
async def get_locations():
    """获取所有可用地点"""
    # 返回dict格式并为每个地点添加bounds
    locations_with_bounds = {}
    
    for loc_id, loc_data in settings.locations.items():
        lat, lon, zoom = loc_data["coords"]
        
        # 计算边界框 (20km buffer)
        buffer_km = 20
        lat_delta = buffer_km / 111.0  # ~111 km per degree latitude
        lon_delta = buffer_km / (111.0 * max(abs(lat), 0.01))  # avoid division by zero
        
        locations_with_bounds[loc_id] = {
            **loc_data,
            "bounds": {
                "west": lon - lon_delta,
                "south": lat - lat_delta,
                "east": lon + lon_delta,
                "north": lat + lat_delta
            }
        }
    
    return locations_with_bounds


@app.get("/api/locations/{location_code}")
async def get_location(location_code: str):
    """获取特定地点信息"""
    if location_code not in settings.locations:
        raise HTTPException(status_code=404, detail=f"Location '{location_code}' not found")
    return settings.locations[location_code]


@app.get("/api/modes")
async def get_modes():
    """获取所有 AI 模式"""
    # 返回 dict 格式：{"dna": "地表 DNA (语义视图)", ...}
    # 前端可以直接使用 mode ID 作为 key
    return settings.modes


@app.get("/api/missions", response_model=List[Mission], response_model_exclude_none=True)
async def get_missions():
    """获取 V6 Missions（任务驱动演示主线）。

    该端点不依赖 GEE 初始化，主要用于前端叙事流程与任务面板渲染。
    """
    return settings.missions


@app.post("/api/stats")
async def get_stats(req: StatsRequest):
    """Compute dynamic zonal statistics for a mode+location.

    V5 goal: replace HUD mockStats with real Earth Engine reduceRegion results.
    """

    _require_gee()

    if req.mode not in settings.modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {req.mode}. Valid modes: {list(settings.modes.keys())}",
        )

    if req.location not in settings.locations:
        raise HTTPException(status_code=400, detail=f"Invalid location: {req.location}")

    loc_data = settings.locations[req.location]
    lat, lon, _zoom = loc_data["coords"]
    buffer_m = settings.get_viewport_buffer_m_for_mode(req.mode)
    viewport = ee.Geometry.Point([lon, lat]).buffer(buffer_m)

    mode_full = settings.modes[req.mode]
    img, _vis_params, _suffix = get_layer_logic(mode_full, viewport)

    # Most modes mark "interesting" pixels via updateMask; clustering is categorical and
    # should not be interpreted as an anomaly mask.
    masked_as_anomaly = req.mode not in ("ch4_amazon_zeroshot", "ch5_coastline_audit")
    scale_m = int(req.scale_m) if req.scale_m else 30

    stats = await run_in_threadpool(
        compute_zonal_stats,
        img,
        viewport,
        scale=scale_m,
        max_pixels=int(1e9),
        masked_as_anomaly=masked_as_anomaly,
    )

    return {
        "mode": req.mode,
        "location": req.location,
        "stats": stats,
    }


@app.post("/api/report")
async def generate_report(req: ReportRequest):
    """Generate a short monitoring brief for a mission.

    V5 roadmap includes LLM-generated reports. For demo robustness we always
    provide a deterministic template fallback.
    """

    mission = _get_mission_by_id(req.mission_id)
    if not mission:
        raise HTTPException(status_code=400, detail=f"Unknown mission_id: {req.mission_id}")

    stats = req.stats
    computed = False

    if stats is None:
        _require_gee()

        mode_id = req.mode or mission.get("api_mode")
        location_id = req.location or mission.get("location")

        if mode_id not in settings.modes:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode_id}")
        if location_id not in settings.locations:
            raise HTTPException(status_code=400, detail=f"Invalid location: {location_id}")

        loc_data = settings.locations[location_id]
        lat, lon, _zoom = loc_data["coords"]
        buffer_m = settings.get_viewport_buffer_m_for_mode(mode_id)
        viewport = ee.Geometry.Point([lon, lat]).buffer(buffer_m)

        mode_full = settings.modes[mode_id]
        img, _vis_params, _suffix = get_layer_logic(mode_full, viewport)
        # Most modes mark "interesting" pixels via updateMask.
        # Categorical outputs (clustering / CH5 audit classes) should not be treated as anomaly masks.
        masked_as_anomaly = mode_id not in ("ch4_amazon_zeroshot", "ch5_coastline_audit")
        stats = await run_in_threadpool(
            compute_zonal_stats,
            img,
            viewport,
            scale=30,
            max_pixels=int(1e9),
            masked_as_anomaly=masked_as_anomaly,
        )
        computed = True

    title = mission.get("title", "")
    narrative = mission.get("narrative", "")
    formula = mission.get("formula", "")

    total = stats.get("total_area_km2") if isinstance(stats, dict) else None
    anomaly = stats.get("anomaly_area_km2") if isinstance(stats, dict) else None
    pct = stats.get("anomaly_pct") if isinstance(stats, dict) else None

    def _fmt(x):
        if x is None:
            return "—"
        try:
            return f"{float(x):.2f}"
        except Exception:
            return str(x)

    def _ch5_v8_evidence_appendix() -> str:
        # Keep this appendix deterministic (no GEE calls) so it works offline and in unit tests.
        mode_id = req.mode or mission.get("api_mode")
        if mode_id != "ch5_coastline_audit":
            return ""

        # Asset id resolution mirrors backend/ch5_rf_export.py.
        explicit = str(os.getenv("CH5_RF_ASSET_ID", "")).strip()
        if explicit:
            asset_id = explicit
        else:
            gee_user_path = str(os.getenv("GEE_USER_PATH", "") or getattr(settings, "gee_user_path", "")).strip()
            if gee_user_path and gee_user_path != "users/default/aef_demo":
                asset_id = f"{gee_user_path.rstrip('/')}/classifiers/ch5_coastline_rf_v1"
            else:
                asset_id = "<unset>"

        scale = str(os.getenv("CH5_RF_SAMPLE_SCALE", "30") or "30")
        points_per_class = str(os.getenv("CH5_RF_POINTS_PER_CLASS", "3000") or "3000")
        trees = str(os.getenv("CH5_RF_TREES", "60") or "60")
        min_leaf = str(os.getenv("CH5_RF_MIN_LEAF_POP", "10") or "10")
        bag_fraction = str(os.getenv("CH5_RF_BAG_FRACTION", "0.6") or "0.6")

        training_region = "[119.8, 32.8, 121.5, 34.0]"
        esa_dataset = "ESA/WorldCover/v200"
        jrc_dataset = "JRC/GSW1_4/GlobalSurfaceWater (occurrence 0–100)"

        geofence_polygon = "[[[120.30,34.00],[121.50,34.00],[121.80,32.50],[120.60,32.50]]]"

        return (
            "【证据附件：V8.1 泛化与精度控制（多源共识 × 正则化 × 形态学平滑）】\n"
            "- 数据源：Google AEF Embedding (16D, 2023–2025) × ESA WorldCover × JRC Global Surface Water\n"
            f"- ESA 数据集：{esa_dataset}（Map）\n"
            f"- JRC 数据集：{jrc_dataset}\n"
            "- 软边界共识标签（Soft Margin；仅保留达成共识的像元入样）：\n"
            "  - 0 水体：JRC occurrence ≥ 80% 且 ESA=80(水体)\n"
            "  - 1 潮间带滩涂：5% < occurrence < 80% 且 ESA≠50(建筑)\n"
            "  - 2 人工硬化：ESA=50(建筑/不透水) 且 occurrence≤2%\n"
            "  - 3 内陆背景：ESA∈{40(农田),10(树林)} 且 occurrence≤2%\n"
            f"- 采样区域：{training_region}\n"
            f"- 分层采样：每类 {points_per_class} 像元（stratifiedSample），scale={scale}m\n"
            f"- 模型：RandomForest(trees={trees}, minLeafPopulation={min_leaf}, bagFraction={bag_fraction})（正则化抑制过拟合）\n"
            f"- 资产：{asset_id}\n"
            "- 渲染后缀：ch5_audit_v8_1_generalized\n"
            "- 形态学平滑：img.focal_mode(radius=1.5, kernelType='circle', iterations=1)（多数滤波抑制椒盐碎斑）\n"
            f"- 空间围栏（Coastal Geofence）：{geofence_polygon}（先 clip，物理切除内陆干扰）\n"
            "- 推理净化：透明化水域与内陆（mask 掉 0 和 3）：img.updateMask(img.neq(3).And(img.neq(0)))\n"
            "- 可视化：仅保留 1=金黄(滩涂) 与 2=警告红(硬化) 的证据对抗"
        )

    report = (
        f"《区域空间监测简报》\n"
        f"任务：{title}\n"
        f"算子：{formula}\n"
        f"摘要：{narrative}\n"
        f"统计：总面积 { _fmt(total) } km²；异常面积 { _fmt(anomaly) } km²；异常占比 { _fmt(pct) }%\n"
        f"【共识印证】在统一表征隐空间中，本次结果提供了可复核的量化证据，用于支撑‘事件叙事’的客观核验。\n"
        f"建议：对异常占比高的网格优先开展核查，结合 Sentinel-2 影像与历史变化趋势形成处置清单。"
    )

    appendix = _ch5_v8_evidence_appendix()
    if appendix:
        report = report.rstrip() + "\n\n" + appendix

    generated_by = "template"
    if settings.llm_api_key:
        try:
            llm_text = await generate_monitoring_brief_openai_compatible(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                mission=mission,
                stats=stats if isinstance(stats, dict) else {},
                timeout_s=settings.llm_timeout_s,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
            if llm_text:
                # Keep a deterministic header so the brief always contains mission context
                # (and tests/demos remain stable even if the model omits some fields).
                header = (
                    f"《区域空间监测简报》\n"
                    f"任务：{title}\n"
                    f"算子：{formula}\n"
                    f"统计：总面积 { _fmt(total) } km²；异常面积 { _fmt(anomaly) } km²；异常占比 { _fmt(pct) }%\n"
                    f"\n"
                )

                text = str(llm_text).strip()
                if title and (title not in text):
                    report = header + text
                else:
                    # Still ensure numbers are present for stakeholder-facing traceability
                    if _fmt(pct) not in text:
                        report = header + text
                    else:
                        report = text
                generated_by = "llm"
        except Exception as e:
            print(f"Warning: LLM report generation failed: {e}")

    # Ensure CH5 evidence appendix is always attached (even when LLM is used).
    appendix = _ch5_v8_evidence_appendix()
    if appendix and appendix not in report:
        report = report.rstrip() + "\n\n" + appendix

    return {
        "mission_id": req.mission_id,
        "generated_by": generated_by,
        "computed_stats": computed,
        "report": report,
    }


@app.post("/api/analyze")
async def analyze_mission(req: AnalyzeRequest):
    """Generate an agent analysis text for the front-end analysis console.

    - If `stats` is provided, works without GEE.
    - Otherwise computes stats server-side (requires GEE initialized).
    - If LLM is configured, will try LLM first and fall back to template.
    """

    mission = _get_mission_by_id(req.mission_id)
    if not mission:
        raise HTTPException(status_code=400, detail=f"Unknown mission_id: {req.mission_id}")

    stats = req.stats
    computed = False

    if stats is None:
        _require_gee()

        mode_id = req.mode or mission.get("api_mode")
        location_id = req.location or mission.get("location")

        if mode_id not in settings.modes:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode_id}")
        if location_id not in settings.locations:
            raise HTTPException(status_code=400, detail=f"Invalid location: {location_id}")

        loc_data = settings.locations[location_id]
        lat, lon, _zoom = loc_data["coords"]
        buffer_m = settings.get_viewport_buffer_m_for_mode(mode_id)
        viewport = ee.Geometry.Point([lon, lat]).buffer(buffer_m)

        mode_full = settings.modes[mode_id]
        img, _vis_params, _suffix = get_layer_logic(mode_full, viewport)
        masked_as_anomaly = mode_id not in ("ch4_amazon_zeroshot",)
        stats = await run_in_threadpool(
            compute_zonal_stats,
            img,
            viewport,
            scale=30,
            max_pixels=int(1e9),
            masked_as_anomaly=masked_as_anomaly,
        )
        computed = True

    generated_by = "template"
    analysis = _render_agent_analysis_template(mission, stats if isinstance(stats, dict) else {})

    if settings.llm_api_key:
        try:
            llm_text = await generate_agent_analysis_openai_compatible(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                mission=mission,
                stats=stats if isinstance(stats, dict) else {},
                timeout_s=settings.llm_timeout_s,
                temperature=settings.llm_temperature,
                max_tokens=max(700, int(settings.llm_max_tokens)),
            )
            if llm_text:
                analysis = llm_text
                generated_by = "llm"
        except Exception:
            analysis = _render_agent_analysis_template(mission, stats if isinstance(stats, dict) else {})
            generated_by = "template"

    return {
        "mission_id": req.mission_id,
        "generated_by": generated_by,
        "computed": computed,
        "analysis": analysis,
    }


@app.get("/api/layers")
async def get_layer(
    request: Request,
    mode: str = Query(..., description="AI 场景模式"),
    location: str = Query(..., description="地点代码")
):
    """
    获取指定模式和地点的图层 Tile URL
    
    Args:
        mode: AI 模式 (如 "change", "dna")
        location: 地点代码 (如 "shanghai")
    
    Returns:
        {
            "tile_url": "https://earthengine.googleapis.com/...",
            "is_cached": true/false,
            "status": "缓存/实时",
            "asset_id": "...",
            "vis_params": {...}
        }
    """
    _require_gee()
    
    # 验证地点
    if location not in settings.locations:
        raise HTTPException(status_code=400, detail=f"Invalid location: {location}")
    
    # 验证模式
    if mode not in settings.modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Valid modes: {list(settings.modes.keys())}")
    
    # 转换模式代码为完整名称
    mode_full = settings.modes.get(mode, mode)
    
    try:
        # 获取地点坐标
        loc_data = settings.locations[location]
        lat, lon, zoom = loc_data["coords"]
        
        # 创建视口区域：用于 filterBounds/mosaic 的空间筛选。
        # buffer 太小会导致缩小视角时只看到一小块区域。
        buffer_m = settings.get_viewport_buffer_m_for_mode(mode)
        viewport = ee.Geometry.Point([lon, lat]).buffer(buffer_m)
        # For tile rendering, prefer a simple bounds geometry for filterBounds.
        # This keeps the same extent but avoids a high-vertex buffer polygon.
        viewport_for_tiles = viewport.bounds()
        
        # 智能加载图层（包含 ee.data.getAsset 等阻塞调用；放到 threadpool）
        layer_img, vis_params, status_html, is_cached, asset_id, raw_img = await run_in_threadpool(
            smart_load,
            mode_full,
            viewport_for_tiles,
            location,
            settings.gee_user_path,
        )
        
        # 获取上游 Tile URL (ee.getMapId) 并注册到本地代理。
        # 为避免前端 prefetch/多客户端导致的重复 getMapId 调用，这里使用 TTL cache。
        template_cache_key = _layer_template_cache_key(str(asset_id), vis_params)
        upstream_tile_url = _layer_template_cache_get(template_cache_key)
        if not upstream_tile_url:
            # ee.Image.getMapId() 会发起网络请求，属于阻塞调用
            upstream_tile_url = await run_in_threadpool(get_tile_url, layer_img, vis_params)
            _layer_template_cache_set(template_cache_key, upstream_tile_url)
        tile_id = _register_tile_template(upstream_tile_url)
        # Always return a same-origin URL template.
        # IMPORTANT: do not include scheme/host/port here. In production, nginx may pass
        # `Host` without port (e.g. using `$host`), which would accidentally produce
        # `http://<ip>/api/...` (port 80) and trigger CORS failures from `:8506`.
        # Critical fix: use standard XYZ {y}. Using Cesium {reverseY} will flip Y,
        # causing upstream GEE to miss tiles (400/404) and render black blocks.
        tile_url = f"/api/tiles/{tile_id}/{{z}}/{{x}}/{{y}}"
        
        # 计算边界框 (基于缓冲区)
        buffer_km = max(1, int(buffer_m / 1000))
        # 简单的边界框计算 (度数转换)
        lat_delta = buffer_km / 111.0  # ~111 km per degree latitude
        lon_delta = buffer_km / (111.0 * abs(lat))  # longitude depends on latitude
        bounds = [
            lon - lon_delta,  # west
            lat - lat_delta,  # south
            lon + lon_delta,  # east
            lat + lat_delta   # north
        ]
        
        return {
            "tile_url": tile_url,
            "bounds": bounds,
            "is_cached": is_cached,
            "status": status_html,
            "asset_id": asset_id,
            "vis_params": vis_params,
            # Rendering hints are optional/additive; frontend may ignore them.
            # Motivation: some palettes (bright/yellow/light) can look like a "white film"
            # when stacked at high alpha. Per-mode opacity stabilizes perception.
            "render_hints": {
                "ai_opacity": {
                    # Legacy visual baseline: App.vue historically used 0.88 for all modes.
                    # Keep non-Yancheng modes at 0.88 to match the old look.
                    "ch1_yuhang_faceid": 0.88,
                    "ch2_maowusu_shield": 0.88,
                    "ch3_zhoukou_pulse": 0.88,
                    "ch4_amazon_zeroshot": 0.88,
                    "ch6_water_pulse": 0.88,
                    # Yancheng optimization: reduce perceived "white film" for coastline audit.
                    "ch5_coastline_audit": 0.65,
                }.get(mode, 0.88),
            },
            "location": loc_data,
            "mode": mode
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.post("/api/cache/export")
async def export_cache(request: ExportRequest):
    """
    触发缓存导出任务
    
    Args:
        request: 包含 mode 和 location 的请求体
    
    Returns:
        {
            "task_id": "TASK_12345",
            "status": "submitted",
            "asset_id": "..."
        }
    """
    _require_gee()
    
    # 验证模式
    if request.mode not in settings.modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}. Valid modes: {list(settings.modes.keys())}")
    
    # 验证地点
    if request.location not in settings.locations:
        raise HTTPException(status_code=400, detail=f"Invalid location: {request.location}")
    
    try:
        # 获取地点坐标
        loc_data = settings.locations[request.location]
        lat, lon, zoom = loc_data["coords"]
        buffer_m = settings.get_viewport_buffer_m_for_mode(request.mode)
        viewport = ee.Geometry.Point([lon, lat]).buffer(buffer_m)
        
        # 转换mode ID为完整名称
        mode_full = settings.modes[request.mode]
        
        # 获取图层逻辑 (使用完整名称)
        image, vis_params, suffix = await run_in_threadpool(get_layer_logic, mode_full, viewport)
        
        # 生成 Asset ID
        asset_id = f"{settings.gee_user_path}/{request.location}_{suffix}"
        
        # 触发导出
        task_id = await run_in_threadpool(
            trigger_export_task,
            image,
            f"Cache_{request.location}_{suffix}",
            asset_id,
            viewport,
        )
        
        return {
            "task_id": task_id,
            "status": "submitted",
            "asset_id": asset_id,
            "location": request.location,
            "mode": request.mode  # 返回mode ID而不是完整名称
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.get("/api/sentinel2")
async def get_sentinel2_layer(request: Request, location: str):
    """
    获取 Sentinel-2 真实影像图层 (用于左侧对比)
    
    Args:
        location: 地点代码
    
    Returns:
        Sentinel-2 影像的 Tile URL
    """
    _require_gee()
    
    if location not in settings.locations:
        raise HTTPException(status_code=400, detail=f"Invalid location: {location}")
    
    try:
        loc_data = settings.locations[location]
        lat, lon, zoom = loc_data["coords"]
        viewport = ee.Geometry.Point([lon, lat]).buffer(settings.viewport_buffer_m).bounds()
        
        # 获取 Sentinel-2 影像（极限优化：避免全年的 median 触发超大计算图/超时）
        # 策略：缩短时间窗口 + 选取少云影像优先拼接（mosaic），通常比 median 快一个数量级。
        # 说明：mosaic 会按集合顺序把未遮罩像元覆盖到输出；我们先按云量升序排序。
        s2_col = (
            ee.ImageCollection("COPERNICUS/S2_SR")
            # IMPORTANT:
            # Bound the collection search space. Without filterBounds(), a global S2
            # ImageCollection + mosaic() can force GEE to scan huge metadata at macro zooms,
            # leading to 504/502 storms. Our viewport already includes a generous buffer.
            .filterBounds(viewport)
            .filterDate("2024-05-01", "2024-10-31")
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 45))
        )
        # Avoid .median() and also avoid .sort() at macro zoom levels.
        s2_image = s2_col.mosaic()
        
        vis_params = {
            'min': 0,
            'max': 3000,
            'bands': ['B4', 'B3', 'B2'],
            # True-color basemap does not need alpha; JPEG is smaller/faster.
            'format': 'jpg'
        }
        
        upstream_tile_url = await run_in_threadpool(get_tile_url, s2_image, vis_params)
        tile_id = _register_tile_template(upstream_tile_url)
        # IMPORTANT:
        # Sentinel-2 is used as an *optional* true-color overlay in the frontend.
        # The app always keeps a stable basemap (Ion/OSM/Grid) underneath, so we
        # prefer the default `fallback=transparent` to avoid 504/502 console storms.
        tile_url = f"/api/tiles/{tile_id}/{{z}}/{{x}}/{{y}}"
        
        return {
            "tile_url": tile_url,
            "type": "sentinel2",
            "date_range": "2024-05-01 to 2024-10-31",
            "location": loc_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.get("/api/basemap/osm/{z}/{x}/{y}.png")
async def proxy_osm_tile(z: int, x: int, y: int):
    """Same-origin proxy for OpenStreetMap raster tiles.

    Does NOT require GEE.

    When the upstream is unreachable, returns a transparent PNG so the grid layer
    (or other basemap layers) can show through without spamming errors.
    """

    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    cache_key = ("osm", int(z), int(x), int(y))
    cached = _tile_cache_get(cache_key)
    if cached:
        body, media_type, headers, _stored_at, _nbytes = cached
        resp_headers = dict(headers or {})
        resp_headers["X-AEF-Tile-Cache"] = "HIT"
        resp_headers["X-AEF-Basemap"] = "osm"
        return Response(content=body, media_type=media_type, headers=resp_headers)

    upstream_url = str(_OSM_TILE_URL_TEMPLATE).format(z=int(z), x=int(x), y=int(y))

    async def _fallback(reason: str, upstream_status: Optional[int] = None) -> Response:
        resp = _tile_fallback_response(
            cache_key,
            max_age_s=30,
            reason=f"osm-{reason}",
            upstream_status=upstream_status,
        )
        resp.headers["X-AEF-Basemap"] = "osm"
        return resp

    try:
        try:
            await asyncio.wait_for(_basemap_upstream_sem.acquire(), timeout=1.5)
        except Exception:
            return await _fallback("busy")

        try:
            resp = await http_client.get(upstream_url, timeout=float(_basemap_upstream_timeout_s))
        finally:
            try:
                _basemap_upstream_sem.release()
            except Exception:
                pass

        status = int(resp.status_code)
        if not (200 <= status < 300):
            return await _fallback("upstream", upstream_status=status)

        body = resp.content
        content_type = resp.headers.get("Content-Type", "image/png")
        cache_control = resp.headers.get("Cache-Control")
        expires = resp.headers.get("Expires")

        headers: Dict[str, str] = {
            # Ensure clients can cache even if upstream headers are missing.
            "Cache-Control": cache_control or "public, max-age=86400",
            "X-AEF-Basemap": "osm",
        }
        if expires:
            headers["Expires"] = expires

        media_type = content_type.split(";")[0].strip() or "image/png"
        _tile_cache_set(cache_key, body, media_type, headers)

        resp_headers = dict(headers)
        resp_headers["X-AEF-Tile-Cache"] = "MISS"
        return Response(content=body, media_type=media_type, headers=resp_headers)

    except httpx.TimeoutException:
        return await _fallback("timeout")
    except httpx.RequestError:
        return await _fallback("request-error")
    except Exception:
        return await _fallback("exception")


@app.api_route("/api/bing-proxy", methods=["GET", "HEAD"])
async def proxy_bing_tile(request: Request, url: str = Query(...)):
    """Same-origin proxy for Bing Maps raster tiles (virtualearth.net).

    This endpoint is intentionally strict (allowlist) to avoid becoming an open proxy.
    """

    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    raw_url = str(url or "").strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="Missing url")

    try:
        parsed = urlsplit(raw_url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid url")

    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Invalid url scheme")

    host = (parsed.hostname or "").lower().strip(".")
    if not host.endswith(".tiles.virtualearth.net"):
        raise HTTPException(status_code=403, detail="Host not allowed")

    path = parsed.path or ""
    if not path.startswith("/tiles/"):
        raise HTTPException(status_code=403, detail="Path not allowed")

    # Force https to avoid mixed-content issues and improve reachability.
    upstream_url = urlunsplit((
        "https",
        parsed.netloc,
        parsed.path,
        parsed.query,
        "",
    ))

    cache_key = ("bing", upstream_url)
    cached = _tile_cache_get(cache_key)
    if cached:
        body, media_type, headers, _stored_at, _nbytes = cached
        resp_headers = dict(headers or {})
        resp_headers["X-AEF-Tile-Cache"] = "HIT"
        resp_headers["X-AEF-Basemap"] = "bing"
        resp_headers.setdefault("Access-Control-Allow-Origin", "*")
        return Response(content=body, media_type=media_type, headers=resp_headers)

    def _proxy_headers() -> Dict[str, str]:
        want = {
            "range",
            "if-none-match",
            "if-modified-since",
            "accept",
            "accept-language",
            "user-agent",
            "referer",
        }
        out: Dict[str, str] = {}
        for k in want:
            v = request.headers.get(k)
            if v:
                out[k] = v
        out["accept-encoding"] = "identity"
        return out

    async def _fallback(reason: str, upstream_status: Optional[int] = None) -> Response:
        resp = _tile_fallback_response(
            cache_key,
            max_age_s=30,
            reason=f"bing-{reason}",
            upstream_status=upstream_status,
        )
        resp.headers["X-AEF-Basemap"] = "bing"
        resp.headers.setdefault("Access-Control-Allow-Origin", "*")
        return resp

    try:
        try:
            await asyncio.wait_for(_basemap_upstream_sem.acquire(), timeout=1.5)
        except Exception:
            return await _fallback("busy")

        try:
            if request.method.upper() == "HEAD":
                upstream_resp = await http_client.request(
                    "HEAD",
                    upstream_url,
                    headers=_proxy_headers(),
                    timeout=float(_basemap_upstream_timeout_s),
                    follow_redirects=True,
                )
                status = int(upstream_resp.status_code)
                if not (200 <= status < 300):
                    return await _fallback("upstream", upstream_status=status)

                out_headers = _strip_hop_by_hop_headers(dict(upstream_resp.headers))
                out_headers["X-AEF-Basemap"] = "bing"
                out_headers.setdefault("Access-Control-Allow-Origin", "*")
                return Response(status_code=status, headers=out_headers)

            upstream_resp = await http_client.get(
                upstream_url,
                headers=_proxy_headers(),
                timeout=float(_basemap_upstream_timeout_s),
                follow_redirects=True,
            )
        finally:
            try:
                _basemap_upstream_sem.release()
            except Exception:
                pass

        status = int(upstream_resp.status_code)
        if not (200 <= status < 300):
            return await _fallback("upstream", upstream_status=status)

        body = upstream_resp.content
        content_type = upstream_resp.headers.get("Content-Type") or "image/jpeg"
        cache_control = upstream_resp.headers.get("Cache-Control")
        expires = upstream_resp.headers.get("Expires")

        headers: Dict[str, str] = {
            "Cache-Control": cache_control or "public, max-age=86400",
            "X-AEF-Basemap": "bing",
            "Access-Control-Allow-Origin": "*",
        }
        if expires:
            headers["Expires"] = expires

        media_type = content_type.split(";")[0].strip() or "image/jpeg"
        _tile_cache_set(cache_key, body, media_type, headers)

        resp_headers = dict(headers)
        resp_headers["X-AEF-Tile-Cache"] = "MISS"
        return Response(content=body, media_type=media_type, headers=resp_headers)

    except httpx.TimeoutException:
        return await _fallback("timeout")
    except httpx.RequestError:
        return await _fallback("request-error")
    except HTTPException:
        raise
    except Exception:
        return await _fallback("exception")


@app.api_route("/api/ion/{path:path}", methods=["GET", "HEAD"])
async def proxy_cesium_ion_api(path: str, request: Request):
    """Same-origin proxy for Cesium Ion API (api.cesium.com).

    We rewrite JSON responses to ensure returned asset URLs are also same-origin
    (pointing to /api/ion-assets and /api/google-tiles), so the browser never
    needs to reach external domains directly.
    """

    upstream_url = f"{_ION_API_BASE}/{str(path).lstrip('/')}"
    # Ion API responses are typically small JSON; rewrite when applicable.
    if request.method.upper() == "GET":
        return await _proxy_json_with_rewrite(request, upstream_url=upstream_url)
    return await _proxy_stream(request, upstream_url=upstream_url)


@app.api_route("/api/ion-assets/{path:path}", methods=["GET", "HEAD"])
async def proxy_cesium_ion_assets(path: str, request: Request):
    """Same-origin proxy for Cesium Ion asset content (assets.cesium.com).

    Must support large binary payloads and Range requests.
    """

    upstream_url = f"{_ION_ASSETS_BASE}/{str(path).lstrip('/')}"
    return await _proxy_stream(request, upstream_url=upstream_url)


@app.api_route("/api/google-tiles/{path:path}", methods=["GET", "HEAD"])
async def proxy_google_tiles(path: str, request: Request):
    """Same-origin proxy for Google tiles (tile.googleapis.com).

    Photorealistic 3D tiles can reference tile.googleapis.com; proxying keeps the
    client within the same origin.
    """

    upstream_url = f"{_GOOGLE_TILES_BASE}/{str(path).lstrip('/')}"

    # Optional server-side API key injection.
    # - Recommended: set GOOGLE_MAPS_API_KEY on the backend so clients never need to embed keys.
    # - If clients explicitly provide ?key=..., we preserve it.
    extra_params: Optional[Dict[str, str]] = None
    try:
        if "key" not in request.query_params and _GOOGLE_MAPS_API_KEY:
            extra_params = {"key": _GOOGLE_MAPS_API_KEY}
    except Exception:
        extra_params = None
    # `root.json` (and other small JSON metadata) is especially sensitive to
    # mid-stream disconnects; buffering+retry avoids browser-side
    # ERR_INCOMPLETE_CHUNKED_ENCODING.
    if request.method.upper() == "GET" and str(path).lower().endswith(".json"):
        return await _proxy_google_tiles_json_with_rewrite(
            request,
            upstream_url=upstream_url,
            timeout_s=float(_google_tiles_timeout_s),
            retries=1,
            extra_params=extra_params,
        )
    return await _proxy_stream(
        request,
        upstream_url=upstream_url,
        timeout_s=float(_google_tiles_timeout_s),
        extra_params=extra_params,
    )


@app.post("/api/google-tiles/v1/createSession")
async def google_tiles_create_session(request: Request):
    """Create a Google Map Tiles API session (official flow).

    This endpoint exists because Google Map Tiles API requires a POST createSession
    call before 2D tiles can be fetched.

    Auth:
    - Prefer server-side env GOOGLE_MAPS_API_KEY.
    - For dev, you may pass ?key=... (not recommended for production).
    """

    key = str(request.query_params.get("key") or "").strip() or _GOOGLE_MAPS_API_KEY
    if not key:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_google_maps_api_key",
                "hint": "Set backend env GOOGLE_MAPS_API_KEY (recommended) or pass ?key=... for dev.",
            },
        )

    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    upstream_url = f"{_GOOGLE_TILES_BASE}/v1/createSession"
    diag_key = _diag_key_for_upstream_url(upstream_url)

    # Preserve caller-sent query params, but ensure key is present.
    params = dict(request.query_params)
    params.setdefault("key", key)

    headers = _proxy_request_headers(request, accept_encoding_identity=True)
    headers.setdefault("accept", "application/json")
    # Content-Type is required by the upstream; keep caller value when provided.
    if "content-type" not in {k.lower(): v for k, v in headers.items()}:
        ct = request.headers.get("content-type")
        if ct:
            headers["content-type"] = ct
        else:
            headers["content-type"] = "application/json"

    body = await request.body()
    timeout_cfg = httpx.Timeout(float(_google_tiles_timeout_s))

    try:
        try:
            await asyncio.wait_for(_ion_upstream_sem.acquire(), timeout=1.5)
        except Exception:
            raise HTTPException(status_code=503, detail="Upstream busy")

        t0 = time.perf_counter()
        resp = await http_client.request(
            "POST",
            upstream_url,
            params=params,
            headers=headers,
            content=body,
            timeout=timeout_cfg,
            follow_redirects=True,
        )
        _record_upstream_diag(
            diag_key,
            status=int(resp.status_code),
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            error=None,
        )

        out_headers = _strip_hop_by_hop_headers(dict(resp.headers))
        out_headers = {
            k: v
            for k, v in out_headers.items()
            if k.lower() not in {"content-length", "content-encoding", "transfer-encoding"}
        }
        out_headers["X-OneEarth-Proxy-Mode"] = "buffered"

        content_type = resp.headers.get("content-type") or "application/json"
        media_type = content_type.split(";")[0].strip() or "application/json"
        return Response(
            content=resp.content,
            status_code=int(resp.status_code),
            headers=out_headers,
            media_type=media_type,
        )

    except httpx.TimeoutException as e:
        _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"timeout: {e}")
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.RequestError as e:
        _record_upstream_diag(diag_key, status=None, latency_ms=None, error=f"request_error: {e}")
        raise HTTPException(status_code=502, detail="Upstream request error")
    finally:
        try:
            _ion_upstream_sem.release()
        except Exception:
            pass


@app.get("/api/tiles/{tile_id}/{z}/{x}/{y}")
async def proxy_gee_tile(
    tile_id: str,
    z: int,
    x: int,
    y: int,
    fallback: str = Query(
        default="transparent",
        description="Tile failure policy: 'transparent' (HTTP 200 PNG) or 'error' (propagate HTTP error)",
    ),
):
    """同源代理 Earth Engine 瓦片（完全异步），避免并发瓦片请求阻塞导致黑块。"""
    _require_gee()

    fallback_mode = str(fallback or "transparent").strip().lower()
    if fallback_mode not in {"transparent", "error"}:
        fallback_mode = "transparent"

    # IMPORTANT: client zooming/dragging can cancel in-flight requests.
    # In Py3.8+, CancelledError inherits BaseException, so it bypasses `except Exception`
    # and can manifest as upstream disconnects (nginx returns 502). We handle it explicitly.
    try:
        template = _get_registered_template(tile_id)
        if not template:
            # After backend restart/reload, old tile_ids will naturally disappear.
            # For AI layers we prefer a transparent tile over a hard 404 to avoid console storms.
            # For basemap (fallback=error), keep 404 so the frontend can fall back immediately.
            if fallback_mode == "error":
                raise HTTPException(status_code=404, detail="Unknown tile_id (expired or not registered)")
            cache_key = (tile_id, int(z), int(x), int(y))
            return _tile_fallback_response(
                cache_key,
                max_age_s=30,
                reason="unknown-tile-id",
                upstream_status=404,
            )

        if http_client is None:
            raise HTTPException(status_code=503, detail="HTTP client not initialized")

        cache_key = (tile_id, int(z), int(x), int(y))
        cached = _tile_cache_get(cache_key)
        if cached:
            body, media_type, headers, _stored_at, _nbytes = cached
            resp_headers = dict(headers or {})
            resp_headers["X-AEF-Tile-Cache"] = "HIT"
            return Response(content=body, media_type=media_type, headers=resp_headers)

        deadline = time.monotonic() + max(0.2, float(_tile_proxy_total_timeout_s))

        def _remaining_s() -> float:
            return max(0.0, deadline - time.monotonic())

        def _transparent_or_error(
            *,
            reason: str,
            status_code: int,
            max_age_s: int,
            upstream_status: Optional[int] = None,
        ):
            if fallback_mode == "error":
                raise HTTPException(
                    status_code=int(status_code),
                    detail={
                        "error": "tile_proxy_failed",
                        "reason": str(reason),
                        "upstream_status": upstream_status,
                    },
                )
            return _tile_fallback_response(
                cache_key,
                max_age_s=max_age_s,
                reason=reason,
                upstream_status=upstream_status,
            )

        # Coalesce concurrent fetches for the same tile.
        is_owner = False
        async with _tile_inflight_lock:
            ev = _tile_inflight.get(cache_key)
            if ev is None:
                ev = asyncio.Event()
                _tile_inflight[cache_key] = ev
                is_owner = True

        if not is_owner:
            try:
                await asyncio.wait_for(ev.wait(), timeout=max(0.05, _remaining_s()))
            except asyncio.CancelledError:
                return Response(status_code=499)
            except Exception:
                return _transparent_or_error(
                    reason="inflight-timeout",
                    status_code=504,
                    max_age_s=10,
                    upstream_status=None,
                )

            cached2 = _tile_cache_get(cache_key)
            if cached2:
                body, media_type, headers, _stored_at, _nbytes = cached2
                resp_headers = dict(headers or {})
                resp_headers["X-AEF-Tile-Cache"] = "HIT"
                resp_headers["X-AEF-Tile-Inflight"] = "WAIT"
                return Response(content=body, media_type=media_type, headers=resp_headers)

            return _transparent_or_error(
                reason="inflight-miss",
                status_code=504,
                max_age_s=10,
                upstream_status=None,
            )

        upstream_url = (
            template
            .replace("{z}", str(z))
            .replace("{x}", str(x))
            .replace("{y}", str(y))
        )

        # Retry transient upstream errors (especially noticeable when zooming in)
        retryable_statuses = {408, 425, 429, 500, 502, 503, 504}
        attempt = 0
        last_status: Optional[int] = None

        # For basemap tiles, prefer fast failure to enable immediate frontend fallback.
        # For AI tiles, allow a couple of retries to reduce transient gaps.
        max_retries = 0 if fallback_mode == "error" else max(0, int(_tile_upstream_retries))

        try:
            while True:
                attempt += 1
                try:
                    if _remaining_s() <= 0.05:
                        return _transparent_or_error(
                            reason="deadline",
                            status_code=504,
                            max_age_s=5,
                            upstream_status=last_status,
                        )

                    try:
                        await asyncio.wait_for(
                            _tile_upstream_sem.acquire(),
                            timeout=max(0.05, min(float(_tile_upstream_acquire_timeout_s), _remaining_s())),
                        )
                    except asyncio.CancelledError:
                        return Response(status_code=499)
                    except Exception:
                        return _transparent_or_error(
                            reason="busy",
                            status_code=503,
                            max_age_s=5,
                            upstream_status=None,
                        )

                    try:
                        per_attempt = min(
                            float(_tile_proxy_per_attempt_timeout_s),
                            float(_tile_upstream_timeout_s),
                            max(0.05, _remaining_s()),
                        )
                        resp = await http_client.get(upstream_url, timeout=per_attempt)
                    finally:
                        try:
                            _tile_upstream_sem.release()
                        except Exception:
                            pass

                    last_status = int(resp.status_code)

                except asyncio.CancelledError:
                    return Response(status_code=499)
                except httpx.TimeoutException:
                    return _transparent_or_error(
                        reason="timeout",
                        status_code=504,
                        max_age_s=15,
                        upstream_status=last_status,
                    )
                except httpx.RequestError:
                    if attempt <= (1 + max_retries) and _remaining_s() > 0.15:
                        await asyncio.sleep(min(0.8, 0.15 * (2 ** (attempt - 1))))
                        continue
                    return _transparent_or_error(
                        reason="request-error",
                        status_code=502,
                        max_age_s=10,
                        upstream_status=last_status,
                    )
                except Exception:
                    return _transparent_or_error(
                        reason="proxy-exception",
                        status_code=502,
                        max_age_s=10,
                        upstream_status=last_status,
                    )

                if last_status in (400, 404):
                    return _transparent_or_error(
                        reason="upstream-no-data",
                        status_code=404,
                        max_age_s=600,
                        upstream_status=last_status,
                    )

                if 200 <= last_status < 300:
                    body = resp.content
                    content_type = resp.headers.get("Content-Type", "image/png")
                    cache_control = resp.headers.get("Cache-Control")
                    expires = resp.headers.get("Expires")

                    headers: Dict[str, str] = {}
                    if cache_control:
                        headers["Cache-Control"] = cache_control
                    if expires:
                        headers["Expires"] = expires

                    media_type = content_type.split(";")[0].strip()
                    _tile_cache_set(cache_key, body, media_type, headers)
                    resp_headers = dict(headers or {})
                    resp_headers["X-AEF-Tile-Cache"] = "MISS"
                    resp_headers["X-AEF-Tile-Inflight"] = "OWNER"
                    return Response(content=body, media_type=media_type, headers=resp_headers)

                if last_status in retryable_statuses and attempt <= (1 + max_retries) and _remaining_s() > 0.15:
                    await asyncio.sleep(min(0.8, 0.15 * (2 ** (attempt - 1))))
                    continue

                return _transparent_or_error(
                    reason="upstream-error",
                    status_code=502,
                    max_age_s=10,
                    upstream_status=last_status,
                )
        finally:
            try:
                async with _tile_inflight_lock:
                    ev2 = _tile_inflight.pop(cache_key, None)
                if ev2:
                    ev2.set()
            except Exception:
                pass

    except asyncio.CancelledError:
        return Response(status_code=499)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )


def _maybe_mount_frontend_dist() -> None:
    """Optionally serve built Vite frontend from this FastAPI process.

    Why:
    - In production, a common 502 root cause is a reverse proxy (or port mapping)
      pointing to a dead frontend upstream. If static assets like /__cesium/* return 502,
      the issue is infrastructure/process keepalive, not GEE.
    - Serving dist directly removes the second process entirely.

    Enable with:
      SERVE_FRONTEND_DIST=1
      FRONTEND_DIST_DIR=/abs/path/to/frontend/dist (optional)
    """

    if os.getenv("SERVE_FRONTEND_DIST", "0") != "1":
        return

    # Resolve dist dir (default assumes repo layout: backend/../frontend/dist)
    dist_dir = os.getenv("FRONTEND_DIST_DIR")
    if not dist_dir:
        dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

    if not os.path.isdir(dist_dir):
        # Don't crash the API if dist isn't present; just run as API-only.
        return

    # Mount last so /api/* routes keep precedence.
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")


# Mount static frontend if configured.
_maybe_mount_frontend_dist()
