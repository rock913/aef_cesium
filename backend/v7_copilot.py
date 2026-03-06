from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/v7", tags=["v7"])


class CopilotPreset(BaseModel):
    id: str
    label: str
    prompt: str


class ToolDef(BaseModel):
    name: str
    description: str
    args_schema: Dict[str, Any] = Field(default_factory=dict)


CopilotEventType = Literal["thought", "tool_call", "tool_result", "final"]


class CopilotEvent(BaseModel):
    type: CopilotEventType
    text: Optional[str] = None
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None


class CopilotExecuteRequest(BaseModel):
    prompt: str
    context_id: Optional[str] = None
    scale: Optional[Literal["earth", "macro", "micro"]] = None


class CopilotExecuteResponse(BaseModel):
    events: List[CopilotEvent]


_PRESETS: List[CopilotPreset] = [
    CopilotPreset(
        id="demo:yuhang_audit",
        label="[演示] 余杭城建审计",
        prompt="对比余杭近7年的城建扩张，使用欧氏距离算子，生成城建审计图层。",
    ),
    CopilotPreset(
        id="demo:amazon_cluster",
        label="[演示] 亚马逊零样本聚类",
        prompt="扫描当前视窗，不使用先验标签，根据 AlphaEarth 64维特征进行零样本聚类(k=6)，找出毁林区。",
    ),
    CopilotPreset(
        id="demo:maowusu_cos",
        label="[演示] 毛乌素生态穿透",
        prompt="评估毛乌素沙地近5年真实治理成效，改用余弦相似度以排除秋冬植被枯黄干扰。",
    ),
    CopilotPreset(
        id="demo:yancheng_coastline",
        label="[演示] 盐城海岸线红线",
        prompt="基于 AEF 16维特征，使用随机森林，划分自然滩涂与人工海堤的边界红线。",
    ),
    CopilotPreset(
        id="demo:zhoukou_water_stress",
        label="[演示] 周口农田内涝胁迫",
        prompt="近期极端降雨，利用介电常数特征，扫描光学表象下农作物根系的隐形水灾风险。",
    ),
    CopilotPreset(
        id="demo:talatan_pv_cooccurrence",
        label="[演示] 塔拉滩光伏蓝海",
        prompt="提取太阳能面板铺设区，并与植被恢复（生物量）特征层进行空间共现性计算。",
    ),
    CopilotPreset(
        id="demo:everest_lake_glof",
        label="[演示] 珠峰冰川湖溃决 (GLOF)",
        prompt="融合高精度 DEM，测算当前冰碛湖体积，并模拟溃坝洪峰(GLOF) 3D路径。",
    ),
    CopilotPreset(
        id="demo:mauna_loa_volcano",
        label="[演示] 冒纳罗亚火山预判",
        prompt="加载 InSAR 形变相位，结合热力异常，生成火山膨胀隆起的 3D 态势图。",
    ),
    CopilotPreset(
        id="demo:congo_carbon_stock",
        label="[演示] 刚果碳汇估算",
        prompt="融合 GEDI 激光雷达树高，计算三维冠层碳储量，并以 3D 柱状体拉伸显示。",
    ),
    CopilotPreset(
        id="demo:nyc_heat_income",
        label="[演示] 纽约热岛×脆弱性",
        prompt="将夏季地表温度 (LST) 与社区平均收入数据进行空间皮尔逊相关性计算。",
    ),
    CopilotPreset(
        id="demo:malacca_oilspill",
        label="[演示] 马六甲油污追踪",
        prompt="利用 SAR 图像检测原油泄漏多边形，与过去 24 小时 AIS 船舶轨迹交集碰撞。",
    ),
    CopilotPreset(
        id="demo:pilbara_unmixing",
        label="[演示] 皮尔巴拉高光谱解译",
        prompt="使用高光谱解混算法 (Spectral Unmixing)，寻找地表下方的铁矿与锂矿隐伏脉络。",
    ),
    CopilotPreset(
        id="demo:global_wind_glsl",
        label="[演示] 全球风场流体 (GLSL)",
        prompt="用 GLSL 为我写一段基于 GFS 数据的全球风场流体渲染代码，并直接在地图上运行。",
    ),
    CopilotPreset(
        id="demo:wormhole_micro",
        label="[演示] 宏微虫洞跃迁",
        prompt="触发虫洞动画并切换到 micro，生成 SiO2 分子晶格。",
    ),
]


_TOOLS: List[ToolDef] = [
    ToolDef(
        name="camera_fly_to",
        description="Move camera to a lat/lon with optional height/duration.",
        args_schema={
            "lat": {"type": "number"},
            "lon": {"type": "number"},
            "height": {"type": "number"},
            "duration_s": {"type": "number"},
        },
    ),
    ToolDef(
        name="add_cesium_imagery",
        description="Mount a raster imagery overlay onto Cesium (tile template URL).",
        args_schema={
            "tile_url": {"type": "string"},
            "opacity": {"type": "number"},
            "palette": {"type": "string"},
            "threshold": {"type": "number"},
        },
    ),
    ToolDef(
        name="add_cesium_vector",
        description="Mount a vector overlay (GeoJSON) onto Cesium.",
        args_schema={
            "geojson": {"type": "object"},
            "opacity": {"type": "number"},
            "color": {"type": "string"},
        },
    ),
    ToolDef(
        name="show_chart",
        description="Write a chart dataset into Charts & Stats artifacts.",
        args_schema={
            "kind": {"type": "string"},
            "title": {"type": "string"},
            "data": {"type": "object"},
        },
    ),
    ToolDef(
        name="render_bivariate_map",
        description="Write a bivariate grid artifact (Charts/Maps placeholder).",
        args_schema={
            "title": {"type": "string"},
            "data": {"type": "object"},
        },
    ),
    ToolDef(
        name="switch_scale",
        description="Switch the twin scale: earth/macro/micro.",
        args_schema={"target": {"type": "string", "enum": ["earth", "macro", "micro"]}},
    ),
    ToolDef(
        name="aef_compute_diff",
        description="Compute cross-year change (diff) layer for a ROI.",
        args_schema={
            "roi": {"type": "string"},
            "years": {"type": "array", "items": {"type": "integer"}},
            "metric": {"type": "string"},
            "dim": {"type": "string"},
        },
    ),
    ToolDef(
        name="aef_kmeans_cluster",
        description="Run kmeans clustering over the current viewport.",
        args_schema={
            "k": {"type": "integer"},
            "use_dims": {"type": "string"},
        },
    ),
    ToolDef(
        name="aef_supervised_boundary_extraction",
        description="Extract supervised boundaries (e.g., coastline redline) with a specified model.",
        args_schema={
            "model": {"type": "string"},
            "target": {"type": "string"},
        },
    ),
    ToolDef(
        name="aef_extract_feature",
        description="Extract an AEF feature dim for a ROI.",
        args_schema={
            "roi": {"type": "string"},
            "dim": {"type": "string"},
        },
    ),
    ToolDef(
        name="aef_spatial_co_occurrence",
        description="Compute spatial co-occurrence between two layers.",
        args_schema={
            "layer1": {"type": "string"},
            "layer2": {"type": "string"},
        },
    ),
    ToolDef(
        name="enable_3d_terrain",
        description="Enable 3D terrain provider.",
        args_schema={"terrain": {"type": "string"}},
    ),
    ToolDef(
        name="calculate_3d_volume",
        description="Calculate 3D volume of a glacial lake using DEM.",
        args_schema={"roi": {"type": "string"}, "use_dem": {"type": "boolean"}},
    ),
    ToolDef(
        name="simulate_glof_fluid",
        description="Simulate GLOF flood path.",
        args_schema={"origin": {"type": "string"}, "volume": {"type": "number"}},
    ),
    ToolDef(
        name="fetch_insar_displacement",
        description="Fetch InSAR displacement for a ROI.",
        args_schema={"roi": {"type": "string"}},
    ),
    ToolDef(
        name="fetch_lst_anomaly",
        description="Fetch land surface temperature anomalies for a ROI.",
        args_schema={"roi": {"type": "string"}},
    ),
    ToolDef(
        name="generate_cesium_custom_shader",
        description="Generate Cesium CustomShader code.",
        args_schema={"vertex_displacement": {"type": "string"}, "fragment_heat": {"type": "string"}},
    ),
    ToolDef(
        name="estimate_carbon_stock",
        description="Estimate carbon stock for a ROI using given sources.",
        args_schema={"source": {"type": "string"}, "roi": {"type": "string"}},
    ),
    ToolDef(
        name="spatial_pearson_correlation",
        description="Compute spatial pearson correlation between two variables over a ROI.",
        args_schema={"var1": {"type": "string"}, "var2": {"type": "string"}, "roi": {"type": "string"}},
    ),
    ToolDef(
        name="detect_sar_oil_spill",
        description="Detect oil spill polygons from SAR.",
        args_schema={"roi": {"type": "string"}},
    ),
    ToolDef(
        name="intersect_ais_tracks",
        description="Intersect AIS tracks with a target polygon over a time window.",
        args_schema={"time_window": {"type": "string"}},
    ),
    ToolDef(
        name="hyperspectral_unmixing",
        description="Run hyperspectral spectral unmixing for a ROI.",
        args_schema={"roi": {"type": "string"}, "endmembers": {"type": "array", "items": {"type": "string"}}},
    ),
    ToolDef(
        name="get_gfs_uv_wind_data",
        description="Get GFS wind (u/v) data url for rendering.",
        args_schema={},
    ),
    ToolDef(
        name="write_to_editor",
        description="Write code/text to the Monaco editor.",
        args_schema={"code": {"type": "string"}, "tab": {"type": "string"}},
    ),
    ToolDef(
        name="execute_editor_code",
        description="Execute code currently in the editor (sandboxed in UI).",
        args_schema={},
    ),
    ToolDef(
        name="generate_report",
        description="Generate a short Markdown report and write it to Reports tab.",
        args_schema={"text": {"type": "string"}},
    ),
    ToolDef(
        name="generate_molecular_lattice",
        description="Generate a molecular lattice for micro scale rendering.",
        args_schema={"type": {"type": "string"}, "count": {"type": "integer"}},
    ),
]


@router.get("/prompts", response_model=List[CopilotPreset])
def list_prompts() -> List[CopilotPreset]:
    return list(_PRESETS)


@router.get("/tools", response_model=List[ToolDef])
def list_tools() -> List[ToolDef]:
    return list(_TOOLS)


async def _fetch_layer(
    request: Request,
    *,
    mode: str,
    location: str,
    variant: str | None = None,
    threshold: float | None = None,
    palette: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
) -> Tuple[Optional[dict], Optional[dict]]:
    """Best-effort fetch of same-origin tile_url from existing /api/layers.

    Returns:
        (data, error) where exactly one is not None.
    """

    params: dict[str, Any] = {
        "mode": mode,
        "location": location,
    }
    if variant:
        params["variant"] = variant
    if threshold is not None:
        params["threshold"] = float(threshold)
    if palette:
        params["palette"] = str(palette)
    if vmin is not None:
        params["min"] = float(vmin)
    if vmax is not None:
        params["max"] = float(vmax)

    transport = httpx.ASGITransport(app=request.app)
    async with httpx.AsyncClient(transport=transport, base_url=str(request.base_url)) as client:
        try:
            r = await client.get("/api/layers", params=params, timeout=12.0)
        except Exception as e:
            return None, {"error": "layers_request_failed", "message": f"{type(e).__name__}: {e}"}

    if r.status_code != 200:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        return None, {"error": "layers_non_200", "status_code": r.status_code, "detail": detail}

    try:
        return r.json(), None
    except Exception as e:
        return None, {"error": "layers_bad_json", "message": f"{type(e).__name__}: {e}"}


async def _execute_stub(
    request: Request,
    prompt: str,
    *,
    context_id: str | None,
    scale: str | None,
) -> List[CopilotEvent]:
    p = (prompt or "").strip()
    lc = p.lower()

    events: List[CopilotEvent] = [
        CopilotEvent(type="thought", text="解析意图并选择工具…"),
    ]

    if "鄱阳" in p or "poyang" in lc or ("水网" in p and ("脉动" in p or "变化" in p)):
        layer_data, layer_err = await _fetch_layer(
            request,
            mode="ch6_water_pulse",
            location="poyang",
        )
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 29.20, "lon": 116.20, "height": 95000, "duration_s": 4.0}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_compute_diff", args={"roi": "poyang", "years": [2022, 2024], "metric": "delta", "dim": "A02"}),
                CopilotEvent(type="tool_result", tool="aef_compute_diff", result={"status": "delegated", "tile_url": (layer_data or {}).get("tile_url") or ""}),
                CopilotEvent(
                    type="tool_call",
                    tool="add_cesium_imagery",
                    args={
                        "tile_url": (layer_data or {}).get("tile_url") or "/api/basemap/osm/{z}/{x}/{y}.png",
                        "opacity": (((layer_data or {}).get("render_hints") or {}).get("ai_opacity") or {}).get("ch6_water_pulse", 0.88),
                        "palette": "",
                        "threshold": None,
                    },
                ),
                CopilotEvent(type="tool_result", tool="add_cesium_imagery", result="ok"),
                CopilotEvent(
                    type="tool_call",
                    tool="generate_report",
                    args={
                        "text": "# 鄱阳湖水网脉动\n\n"
                        + "- A02 维度跨年差分：2024 vs 2022。\n"
                        + ("- ✅ 已从后端 /api/layers 获取同源瓦片模板并挂载。\n" if layer_data else "- ⚠️ GEE 图层不可用，已降级为 OSM 示例 overlay（不影响工具链验收）。\n")
                        + (f"\n## 降级原因\n```json\n{layer_err}\n```\n" if layer_err else ""),
                    },
                ),
                CopilotEvent(type="tool_result", tool="generate_report", result="ok"),
                CopilotEvent(type="final", text="已生成鄱阳湖水网脉动指令（Earth scale），并挂载了图层以验证端到端链路。"),
            ]
        )
        return events

    # Deterministic routing based on keywords.
    if "亚马逊" in p or "amazon" in lc or "聚类" in p or "k=6" in lc:
        layer_data, layer_err = await _fetch_layer(
            request,
            mode="ch4_amazon_zeroshot",
            location="amazon",
        )
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"cluster": 1},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-55.8, -10.2],
                                [-55.8, -9.9],
                                [-55.4, -9.9],
                                [-55.4, -10.2],
                                [-55.8, -10.2],
                            ]
                        ],
                    },
                }
            ],
        }
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": -10.04485, "lon": -55.42936, "height": 90000, "duration_s": 4.0}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_kmeans_cluster", args={"k": 6, "use_dims": "all"}),
                CopilotEvent(type="tool_result", tool="aef_kmeans_cluster", result={"status": "delegated", "clusters": 6}),
                CopilotEvent(
                    type="tool_call",
                    tool="add_cesium_imagery",
                    args={
                        "tile_url": (layer_data or {}).get("tile_url") or "/api/basemap/osm/{z}/{x}/{y}.png",
                        "opacity": (((layer_data or {}).get("render_hints") or {}).get("ai_opacity") or {}).get("ch4_amazon_zeroshot", 0.88),
                        "palette": "",
                        "threshold": None,
                    },
                ),
                CopilotEvent(type="tool_result", tool="add_cesium_imagery", result="ok"),
                CopilotEvent(type="tool_call", tool="add_cesium_vector", args={"geojson": geojson, "opacity": 0.9, "color": "#00F0FF"}),
                CopilotEvent(type="tool_result", tool="add_cesium_vector", result="ok"),
                CopilotEvent(
                    type="tool_call",
                    tool="generate_report",
                    args={
                        "text": "# 亚马逊零样本聚类\n\n"
                        + ("- ✅ 已从后端 /api/layers 获取同源瓦片模板并挂载为 imagery overlay。\n" if layer_data else "- ⚠️ GEE 图层不可用，已降级为 OSM 示例 overlay（不影响工具链验收）。\n")
                        + "- k=6 聚类仍以示例矢量覆盖演示（待接入真实 GeoJSON 输出）。\n"
                        + (f"\n## 降级原因\n```json\n{layer_err}\n```\n" if layer_err else ""),
                    },
                ),
                CopilotEvent(type="tool_result", tool="generate_report", result="ok"),
                CopilotEvent(type="final", text="已生成聚类指令（stub），下一步可将结果渲染为 GeoJSON 图层。"),
            ]
        )
        return events

    if "余杭" in p or "城建" in p:
        layer_data, layer_err = await _fetch_layer(
            request,
            mode="ch1_yuhang_faceid",
            location="yuhang",
        )
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 30.26879, "lon": 119.92284, "height": 16000, "duration_s": 3.8}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_compute_diff", args={"roi": "yuhang", "years": [2017, 2024], "metric": "euclidean", "dim": "A00"}),
                CopilotEvent(type="tool_result", tool="aef_compute_diff", result={"status": "delegated", "tile_url": (layer_data or {}).get("tile_url") or ""}),
                CopilotEvent(
                    type="tool_call",
                    tool="add_cesium_imagery",
                    args={
                        "tile_url": (layer_data or {}).get("tile_url") or "/api/basemap/osm/{z}/{x}/{y}.png",
                        "opacity": (((layer_data or {}).get("render_hints") or {}).get("ai_opacity") or {}).get("ch1_yuhang_faceid", 0.88),
                        "palette": "",
                        "threshold": None,
                    },
                ),
                CopilotEvent(type="tool_result", tool="add_cesium_imagery", result="ok"),
                CopilotEvent(
                    type="tool_call",
                    tool="generate_report",
                    args={
                        "text": "# 余杭城建审计\n\n"
                        + ("- ✅ 已从后端 /api/layers 获取同源瓦片模板并挂载。\n" if layer_data else "- ⚠️ GEE 图层不可用，已降级为 OSM 示例 overlay（不影响工具链验收）。\n")
                        + "- 欧氏距离路径：2017 vs 2024。\n"
                        + (f"\n## 降级原因\n```json\n{layer_err}\n```\n" if layer_err else ""),
                    },
                ),
                CopilotEvent(type="tool_result", tool="generate_report", result="ok"),
                CopilotEvent(type="final", text="已生成城建审计指令（stub），下一步可挂载 tiles 并生成报告。"),
            ]
        )
        return events

    if "毛乌素" in p or "余弦" in p or "cos" in lc:
        layer_data, layer_err = await _fetch_layer(
            request,
            mode="ch2_maowusu_shield",
            location="maowusu",
        )
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 38.60, "lon": 109.60, "height": 70000, "duration_s": 3.9}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_compute_diff", args={"roi": "maowusu", "years": [2019, 2024], "metric": "cosine_similarity", "dim": "A01"}),
                CopilotEvent(type="tool_result", tool="aef_compute_diff", result={"status": "delegated", "tile_url": (layer_data or {}).get("tile_url") or ""}),
                CopilotEvent(
                    type="tool_call",
                    tool="add_cesium_imagery",
                    args={
                        "tile_url": (layer_data or {}).get("tile_url") or "/api/basemap/osm/{z}/{x}/{y}.png",
                        "opacity": (((layer_data or {}).get("render_hints") or {}).get("ai_opacity") or {}).get("ch2_maowusu_shield", 0.88),
                        "palette": "",
                        "threshold": None,
                    },
                ),
                CopilotEvent(type="tool_result", tool="add_cesium_imagery", result="ok"),
                CopilotEvent(
                    type="tool_call",
                    tool="generate_report",
                    args={
                        "text": "# 毛乌素生态穿透\n\n"
                        + "- 余弦相似度用于降低季节枯黄干扰。\n"
                        + ("- ✅ 已从后端 /api/layers 获取同源瓦片模板并挂载。\n" if layer_data else "- ⚠️ GEE 图层不可用，已降级为 OSM 示例 overlay（不影响工具链验收）。\n")
                        + (f"\n## 降级原因\n```json\n{layer_err}\n```\n" if layer_err else ""),
                    },
                ),
                CopilotEvent(type="tool_result", tool="generate_report", result="ok"),
                CopilotEvent(type="final", text="已生成生态穿透指令（stub），余弦相似度用于降低季节干扰。"),
            ]
        )
        return events

    if "盐城" in p or "海岸线" in p or "coast" in lc:
        layer_data, layer_err = await _fetch_layer(
            request,
            mode="ch5_coastline_audit",
            location="yancheng",
        )
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 33.38, "lon": 120.50, "height": 95000, "duration_s": 4.0}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_supervised_boundary_extraction", args={"model": "random_forest", "target": "coastline"}),
                CopilotEvent(type="tool_result", tool="aef_supervised_boundary_extraction", result={"status": "delegated", "features": None}),
                CopilotEvent(
                    type="tool_call",
                    tool="add_cesium_imagery",
                    args={
                        "tile_url": (layer_data or {}).get("tile_url") or "/api/basemap/osm/{z}/{x}/{y}.png",
                        "opacity": (((layer_data or {}).get("render_hints") or {}).get("ai_opacity") or {}).get("ch5_coastline_audit", 0.65),
                        "palette": "",
                        "threshold": None,
                    },
                ),
                CopilotEvent(type="tool_result", tool="add_cesium_imagery", result="ok"),
                CopilotEvent(
                    type="tool_call",
                    tool="generate_report",
                    args={
                        "text": "# 盐城海岸线红线\n\n"
                        + ("- ✅ 已从后端 /api/layers 获取同源瓦片模板并挂载。\n" if layer_data else "- ⚠️ GEE 图层不可用，已降级为 OSM 示例 overlay（不影响工具链验收）。\n")
                        + "- 监督边界提取：RandomForest（后续可补齐矢量红线提取与导出）。\n"
                        + (f"\n## 降级原因\n```json\n{layer_err}\n```\n" if layer_err else ""),
                    },
                ),
                CopilotEvent(type="tool_result", tool="generate_report", result="ok"),
                CopilotEvent(type="final", text="已生成海岸线红线划界指令（stub），并挂载了图层以验证端到端链路。"),
            ]
        )
        return events

    if "周口" in p or "内涝" in p or "胁迫" in p or "dielectric" in lc:
        layer_data, layer_err = await _fetch_layer(
            request,
            mode="ch3_zhoukou_pulse",
            location="zhoukou",
        )
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 33.63, "lon": 114.65, "height": 70000, "duration_s": 4.0}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_extract_feature", args={"roi": "zhoukou", "dim": "A02"}),
                CopilotEvent(type="tool_result", tool="aef_extract_feature", result={"status": "delegated", "tile_url": (layer_data or {}).get("tile_url") or ""}),
                CopilotEvent(
                    type="tool_call",
                    tool="add_cesium_imagery",
                    args={
                        "tile_url": (layer_data or {}).get("tile_url") or "/api/basemap/osm/{z}/{x}/{y}.png",
                        "opacity": (((layer_data or {}).get("render_hints") or {}).get("ai_opacity") or {}).get("ch3_zhoukou_pulse", 0.88),
                        "palette": "",
                        "threshold": None,
                    },
                ),
                CopilotEvent(type="tool_result", tool="add_cesium_imagery", result="ok"),
                CopilotEvent(
                    type="tool_call",
                    tool="generate_report",
                    args={
                        "text": "# 周口农田内涝胁迫\n\n"
                        + ("- ✅ 已从后端 /api/layers 获取同源瓦片模板并挂载。\n" if layer_data else "- ⚠️ GEE 图层不可用，已降级为 OSM 示例 overlay（不影响工具链验收）。\n")
                        + "- A02 维度用于‘水分/胁迫’语义的隐性反演（后续可补齐阈值分级与统计）。\n"
                        + (f"\n## 降级原因\n```json\n{layer_err}\n```\n" if layer_err else ""),
                    },
                ),
                CopilotEvent(type="tool_result", tool="generate_report", result="ok"),
                CopilotEvent(type="final", text="已生成内涝胁迫提取指令（stub），并挂载了图层以验证端到端链路。"),
            ]
        )
        return events

    if "塔拉滩" in p or "光伏" in p or "co-occurrence" in lc or "共现" in p:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 36.10, "lon": 101.70, "height": 180000, "duration_s": 4.2}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_spatial_co_occurrence", args={"layer1": "A00_solar", "layer2": "A01_biomass"}),
                CopilotEvent(type="tool_result", tool="aef_spatial_co_occurrence", result={"status": "stub", "matrix": ""}),
                CopilotEvent(type="final", text="已生成光伏×生物量共现性计算指令（stub）。"),
            ]
        )
        return events

    if "珠峰" in p or "冰川湖" in p or "glof" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 28.04, "lon": 86.93, "height": 220000, "duration_s": 4.4}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="enable_3d_terrain", args={"terrain": "cesium_world_terrain"}),
                CopilotEvent(type="tool_result", tool="enable_3d_terrain", result="ok"),
                CopilotEvent(type="tool_call", tool="calculate_3d_volume", args={"roi": "everest_lake", "use_dem": True}),
                CopilotEvent(type="tool_result", tool="calculate_3d_volume", result={"status": "stub", "volume": 0.0}),
                CopilotEvent(type="tool_call", tool="simulate_glof_fluid", args={"origin": "everest_lake", "volume": 0.0}),
                CopilotEvent(type="tool_result", tool="simulate_glof_fluid", result={"status": "stub", "path": []}),
                CopilotEvent(type="final", text="已生成 GLOF 体积测算与路径模拟指令（stub）。"),
            ]
        )
        return events

    if "冒纳罗亚" in p or "火山" in p or "insar" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 19.48, "lon": -155.61, "height": 240000, "duration_s": 4.4}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="fetch_insar_displacement", args={"roi": "mauna_loa"}),
                CopilotEvent(type="tool_result", tool="fetch_insar_displacement", result={"status": "stub"}),
                CopilotEvent(type="tool_call", tool="fetch_lst_anomaly", args={"roi": "mauna_loa"}),
                CopilotEvent(type="tool_result", tool="fetch_lst_anomaly", result={"status": "stub"}),
                CopilotEvent(type="tool_call", tool="generate_cesium_custom_shader", args={"vertex_displacement": "insar", "fragment_heat": "lst"}),
                CopilotEvent(type="tool_result", tool="generate_cesium_custom_shader", result={"status": "stub", "code": ""}),
                CopilotEvent(type="final", text="已生成火山形变×热异常可视化指令（stub）。"),
            ]
        )
        return events

    if "刚果" in p or "碳" in p or "gedi" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": -1.20, "lon": 23.70, "height": 320000, "duration_s": 4.6}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="estimate_carbon_stock", args={"source": "GEDI+AEF", "roi": "congo"}),
                CopilotEvent(type="tool_result", tool="estimate_carbon_stock", result={"status": "stub", "geojson": None}),
                CopilotEvent(type="final", text="已生成碳储量估算指令（stub）。"),
            ]
        )
        return events

    if "纽约" in p or "热岛" in p or "income" in lc or "pearson" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 40.71, "lon": -74.00, "height": 180000, "duration_s": 4.0}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="spatial_pearson_correlation", args={"var1": "LST", "var2": "Income", "roi": "NYC"}),
                CopilotEvent(type="tool_result", tool="spatial_pearson_correlation", result={"status": "stub", "r": 0.0}),
                CopilotEvent(type="tool_call", tool="show_chart", args={"kind": "scatter", "title": "Income vs LST (stub)", "data": {"r": 0.0, "points": []}}),
                CopilotEvent(type="tool_result", tool="show_chart", result="ok"),
                CopilotEvent(type="tool_call", tool="render_bivariate_map", args={"title": "Bivariate Grid (stub)", "data": {"grid": []}}),
                CopilotEvent(type="tool_result", tool="render_bivariate_map", result="ok"),
                CopilotEvent(type="final", text="已生成 LST×收入相关性计算指令（stub）。"),
            ]
        )
        return events

    if "马六甲" in p or "油污" in p or "ais" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 2.50, "lon": 101.00, "height": 420000, "duration_s": 4.8}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="detect_sar_oil_spill", args={"roi": "malacca"}),
                CopilotEvent(type="tool_result", tool="detect_sar_oil_spill", result={"status": "stub", "polygon": None}),
                CopilotEvent(type="tool_call", tool="intersect_ais_tracks", args={"time_window": "-24h"}),
                CopilotEvent(type="tool_result", tool="intersect_ais_tracks", result={"status": "stub", "czml": None}),
                CopilotEvent(type="final", text="已生成 SAR 油污检测 + AIS 溯源指令（stub）。"),
            ]
        )
        return events

    if "皮尔巴拉" in p or "高光谱" in p or "unmix" in lc or "spectral" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": -22.30, "lon": 118.70, "height": 520000, "duration_s": 5.0}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="hyperspectral_unmixing", args={"roi": "pilbara", "endmembers": ["Fe", "Li"]}),
                CopilotEvent(type="tool_result", tool="hyperspectral_unmixing", result={"status": "stub", "voxels": None}),
                CopilotEvent(type="final", text="已生成高光谱解混指令（stub）。"),
            ]
        )
        return events

    if "风场" in p or "gfs" in lc or "glsl" in lc or "wind" in lc:
        code = """// Cesium CustomShader (stub)\n// Goal: render wind particles from a UV texture.\n\n// TODO: bind GFS UV texture + integrate a particle system in a post-process stage.\n""".strip()
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 0.0, "lon": 0.0, "height": 12000000, "duration_s": 4.2}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="get_gfs_uv_wind_data", args={}),
                CopilotEvent(type="tool_result", tool="get_gfs_uv_wind_data", result={"status": "stub", "url": ""}),
                CopilotEvent(type="tool_call", tool="write_to_editor", args={"code": code, "tab": "CODE & SCRIPT"}),
                CopilotEvent(type="tool_result", tool="write_to_editor", result="ok"),
                CopilotEvent(type="tool_call", tool="execute_editor_code", args={}),
                CopilotEvent(type="tool_result", tool="execute_editor_code", result={"status": "stub"}),
                CopilotEvent(type="final", text="已生成风场渲染代码骨架（stub），可在 CODE & SCRIPT 里继续完善。"),
            ]
        )
        return events

    if "虫洞" in p or "micro" in lc or "sio2" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="switch_scale", args={"target": "micro"}),
                CopilotEvent(type="tool_result", tool="switch_scale", result="ok"),
                CopilotEvent(type="tool_call", tool="generate_molecular_lattice", args={"type": "SiO2", "count": 8000}),
                CopilotEvent(type="tool_result", tool="generate_molecular_lattice", result={"status": "stub", "count": 8000}),
                CopilotEvent(type="final", text="已生成微观晶格指令（stub）。"),
            ]
        )
        return events

    # Fallback.
    events.append(CopilotEvent(type="final", text="已收到指令（stub）。请尝试点击 Prompt Gallery 的预置场景。"))
    return events


@router.post("/copilot/execute", response_model=CopilotExecuteResponse)
async def copilot_execute(request: Request, req: CopilotExecuteRequest) -> CopilotExecuteResponse:
    prompt = str(req.prompt or "")
    events = await _execute_stub(request, prompt, context_id=req.context_id, scale=req.scale)
    return CopilotExecuteResponse(events=events)
