from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
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


def _execute_stub(prompt: str, *, context_id: str | None, scale: str | None) -> List[CopilotEvent]:
    p = (prompt or "").strip()
    lc = p.lower()

    events: List[CopilotEvent] = [
        CopilotEvent(type="thought", text="解析意图并选择工具…"),
    ]

    # Deterministic routing based on keywords.
    if "亚马逊" in p or "amazon" in lc or "聚类" in p or "k=6" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": -10.04485, "lon": -55.42936, "height": 90000, "duration_s": 4.0}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_kmeans_cluster", args={"k": 6, "use_dims": "all"}),
                CopilotEvent(type="tool_result", tool="aef_kmeans_cluster", result={"status": "stub", "clusters": 6}),
                CopilotEvent(type="final", text="已生成聚类指令（stub），下一步可将结果渲染为 GeoJSON 图层。"),
            ]
        )
        return events

    if "余杭" in p or "城建" in p:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 30.26879, "lon": 119.92284, "height": 16000, "duration_s": 3.8}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_compute_diff", args={"roi": "yuhang", "years": [2017, 2024], "metric": "euclidean", "dim": "A00"}),
                CopilotEvent(type="tool_result", tool="aef_compute_diff", result={"status": "stub", "tile_url": ""}),
                CopilotEvent(type="final", text="已生成城建审计指令（stub），下一步可挂载 tiles 并生成报告。"),
            ]
        )
        return events

    if "毛乌素" in p or "余弦" in p or "cos" in lc:
        events.extend(
            [
                CopilotEvent(type="tool_call", tool="camera_fly_to", args={"lat": 38.60, "lon": 109.60, "height": 70000, "duration_s": 3.9}),
                CopilotEvent(type="tool_result", tool="camera_fly_to", result="ok"),
                CopilotEvent(type="tool_call", tool="aef_compute_diff", args={"roi": "maowusu", "years": [2019, 2024], "metric": "cosine_similarity", "dim": "A01"}),
                CopilotEvent(type="tool_result", tool="aef_compute_diff", result={"status": "stub", "tile_url": ""}),
                CopilotEvent(type="final", text="已生成生态穿透指令（stub），余弦相似度用于降低季节干扰。"),
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
def copilot_execute(req: CopilotExecuteRequest) -> CopilotExecuteResponse:
    prompt = str(req.prompt or "")
    events = _execute_stub(prompt, context_id=req.context_id, scale=req.scale)
    return CopilotExecuteResponse(events=events)
