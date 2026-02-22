"""FastAPI Backend for Cesium App

提供 RESTful API 端点，连接前端和 GEE 服务。

关键点：Earth Engine 的 tile server 在浏览器环境下通常不返回 CORS 允许头，
Cesium(WebGL texture) 会因此拒绝加载瓦片并表现为“地图空白”。
因此这里提供后端同源瓦片代理端点，把 tile 请求变为后端自身域名响应。
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import ee
from typing import Optional, Any, Dict, List
import base64
import hashlib
import time
import threading
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
        "ONEEARTH/AGENT v6 :: Mission Accepted\n"
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

# Global async HTTP client (connection pool) for high-concurrency tile proxying
http_client: Optional[httpx.AsyncClient] = None

# 临时注册表：把上游 GEE tile URL 模板映射为一个短 ID
# /api/layers 返回的 tile_url 指向 /api/tiles/{tile_id}/{z}/{x}/{y}
_tile_registry_lock = threading.Lock()
_tile_registry = {}  # tile_id -> {"template": str, "created_at": float}
_tile_registry_max_size = 256


# In-memory LRU cache for final rendered imagery tiles.
# Keyed by (tile_id, z, x, y). Stores (body bytes, media_type, headers dict, stored_at).
_tile_cache_lock = threading.Lock()
_tile_cache: "OrderedDict[tuple, tuple]" = OrderedDict()
_tile_cache_max_items = int(__import__("os").getenv("TILE_LRU_MAX_ITEMS", "4096"))
_tile_cache_ttl_s = float(__import__("os").getenv("TILE_LRU_TTL_S", "600"))


def _tile_cache_get(key: tuple) -> Optional[tuple]:
    """Get a cached tile entry and refresh its LRU position."""
    now = time.time()
    with _tile_cache_lock:
        entry = _tile_cache.get(key)
        if not entry:
            return None
        body, media_type, headers, stored_at = entry
        if _tile_cache_ttl_s > 0 and (now - stored_at) > _tile_cache_ttl_s:
            _tile_cache.pop(key, None)
            return None
        _tile_cache.move_to_end(key)
        return entry


def _tile_cache_set(key: tuple, body: bytes, media_type: str, headers: Dict[str, str]) -> None:
    now = time.time()
    with _tile_cache_lock:
        _tile_cache[key] = (body, media_type, headers, now)
        _tile_cache.move_to_end(key)
        # Evict LRU items to keep bounded memory
        while len(_tile_cache) > max(1, _tile_cache_max_items):
            _tile_cache.popitem(last=False)

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
        init_earth_engine()
        gee_initialized = True
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

    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE not initialized")

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

    stats = compute_zonal_stats(
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
        if not gee_initialized:
            raise HTTPException(status_code=503, detail="GEE not initialized")

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
        # Most modes mark "interesting" pixels via updateMask; clustering is categorical and
        # should not be interpreted as an anomaly mask.
        masked_as_anomaly = mode_id not in ("ch4_amazon_zeroshot",)
        stats = compute_zonal_stats(img, viewport, scale=30, max_pixels=int(1e9), masked_as_anomaly=masked_as_anomaly)
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

    report = (
        f"《区域空间监测简报》\n"
        f"任务：{title}\n"
        f"算子：{formula}\n"
        f"摘要：{narrative}\n"
        f"统计：总面积 { _fmt(total) } km²；异常面积 { _fmt(anomaly) } km²；异常占比 { _fmt(pct) }%\n"
        f"【共识印证】在统一表征隐空间中，本次结果提供了可复核的量化证据，用于支撑‘事件叙事’的客观核验。\n"
        f"建议：对异常占比高的网格优先开展核查，结合 Sentinel-2 影像与历史变化趋势形成处置清单。"
    )

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
        if not gee_initialized:
            raise HTTPException(status_code=503, detail="GEE not initialized")

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
        stats = compute_zonal_stats(img, viewport, scale=30, max_pixels=int(1e9), masked_as_anomaly=masked_as_anomaly)
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
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE not initialized")
    
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
        
        # 智能加载图层
        layer_img, vis_params, status_html, is_cached, asset_id, raw_img = smart_load(
            mode_full, viewport, location, settings.gee_user_path
        )
        
        # 获取上游 Tile URL 并注册到本地代理
        upstream_tile_url = get_tile_url(layer_img, vis_params)
        tile_id = _register_tile_template(upstream_tile_url)
        base_url = str(request.base_url).rstrip("/")
        # Critical fix: use standard XYZ {y}. Using Cesium {reverseY} will flip Y,
        # causing upstream GEE to miss tiles (400/404) and render black blocks.
        tile_url = f"{base_url}/api/tiles/{tile_id}/{{z}}/{{x}}/{{y}}"
        
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
            "location": loc_data,
            "mode": mode
        }
        
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
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE not initialized")
    
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
        image, vis_params, suffix = get_layer_logic(mode_full, viewport)
        
        # 生成 Asset ID
        asset_id = f"{settings.gee_user_path}/{request.location}_{suffix}"
        
        # 触发导出
        task_id = trigger_export_task(
            image,
            f"Cache_{request.location}_{suffix}",
            asset_id,
            viewport
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
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE not initialized")
    
    if location not in settings.locations:
        raise HTTPException(status_code=400, detail=f"Invalid location: {location}")
    
    try:
        loc_data = settings.locations[location]
        lat, lon, zoom = loc_data["coords"]
        viewport = ee.Geometry.Point([lon, lat]).buffer(settings.viewport_buffer_m)
        
        # 获取 Sentinel-2 影像
        s2_image = ee.ImageCollection("COPERNICUS/S2_SR") \
            .filterBounds(viewport) \
            .filterDate('2024-01-01', '2024-12-31') \
            .median()

        # 关键：填充 masked 像元，避免某些缩放级别/瓦片请求返回上游 400/404
        # (Cesium 会先请求低层级瓦片；如果这些请求失败，常会导致整屏“只有网格没有影像”)
        s2_image = s2_image.unmask(0)
        
        vis_params = {
            'min': 0,
            'max': 3000,
            'bands': ['B4', 'B3', 'B2']
        }
        
        upstream_tile_url = get_tile_url(s2_image, vis_params)
        tile_id = _register_tile_template(upstream_tile_url)
        base_url = str(request.base_url).rstrip("/")
        tile_url = f"{base_url}/api/tiles/{tile_id}/{{z}}/{{x}}/{{y}}"
        
        return {
            "tile_url": tile_url,
            "type": "sentinel2",
            "date_range": "2024-01-01 to 2024-12-31",
            "location": loc_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.get("/api/tiles/{tile_id}/{z}/{x}/{y}")
async def proxy_gee_tile(tile_id: str, z: int, x: int, y: int):
    """同源代理 Earth Engine 瓦片（完全异步），避免并发瓦片请求阻塞导致黑块。"""
    if not gee_initialized:
        raise HTTPException(status_code=503, detail="GEE not initialized")

    if http_client is None:
        raise HTTPException(status_code=503, detail="HTTP client not initialized")

    template = _get_registered_template(tile_id)
    if not template:
        raise HTTPException(status_code=404, detail="Unknown tile_id (expired or not registered)")

    cache_key = (tile_id, int(z), int(x), int(y))
    cached = _tile_cache_get(cache_key)
    if cached:
        body, media_type, headers, _stored_at = cached
        return Response(content=body, media_type=media_type, headers=headers)

    upstream_url = (
        template
        .replace("{z}", str(z))
        .replace("{x}", str(x))
        .replace("{y}", str(y))
    )

    try:
        resp = await http_client.get(upstream_url, timeout=10.0)

        # Upstream "no data / out of range" tiles often return 400/404.
        # Returning a valid transparent PNG is more stable for Cesium.
        if resp.status_code in (400, 404):
            headers = {"Cache-Control": "public, max-age=86400"}
            body = _TRANSPARENT_PNG_256
            media_type = "image/png"
            _tile_cache_set(cache_key, body, media_type, headers)
            return Response(content=body, media_type=media_type, headers=headers)

        resp.raise_for_status()

        body = resp.content
        content_type = resp.headers.get("Content-Type", "image/png")
        cache_control = resp.headers.get("Cache-Control")
        expires = resp.headers.get("Expires")

        headers = {}
        if cache_control:
            headers["Cache-Control"] = cache_control
        if expires:
            headers["Expires"] = expires

        # Cesium 只关心能否作为 texture 使用，最关键是同源 + 正确 Content-Type
        media_type = content_type.split(";")[0].strip()
        _tile_cache_set(cache_key, body, media_type, headers)
        return Response(content=body, media_type=media_type, headers=headers)

    except httpx.TimeoutException:
        # Timeout: return transparent tile to prevent Cesium black blocks
        headers = {"Cache-Control": "public, max-age=60"}
        body = _TRANSPARENT_PNG_256
        media_type = "image/png"
        _tile_cache_set(cache_key, body, media_type, headers)
        return Response(content=body, media_type=media_type, headers=headers)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail="Upstream tile error")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Tile proxy failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
