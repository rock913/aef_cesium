"""LLM service (OpenAI-compatible) for generating monitoring briefs.

Target provider: DashScope OpenAI compatible mode.
Base URL example: https://dashscope.aliyuncs.com/compatible-mode/v1
Model: qwen-plus

This module is intentionally small and dependency-free (uses httpx).
"""

from typing import Any, Dict, Optional

import httpx


def _build_prompt(mission: Dict[str, Any], stats: Dict[str, Any]) -> str:
    title = mission.get("title", "")
    narrative = mission.get("narrative", "")
    formula = mission.get("formula", "")
    mode = mission.get("api_mode", "")
    location = mission.get("location", "")

    total = stats.get("total_area_km2")
    anomaly = stats.get("anomaly_area_km2")
    pct = stats.get("anomaly_pct")

    return (
        "你是一名国家级空间治理指挥舱的分析员，请基于给定任务信息与统计指标，生成一份《区域空间监测简报》。\n"
        "要求：\n"
        "1) 中文输出，220~360字左右；\n"
        "2) 必须包含：监测结论、可能原因(2-3条)、处置建议(3条要点)、【共识印证】(1段)；\n"
        "3) 用语稳健，不夸大，不编造不存在的数据；若不确定请用‘可能/建议核查’；\n"
        "4) 【共识印证】应说明：这些量化信号如何用于‘新闻/叙事’的客观核验，但不要宣称绝对真理；\n"
        "5) 直接输出正文，不要输出标题外的多余说明。\n\n"
        f"任务标题：{title}\n"
        f"任务叙事：{narrative}\n"
        f"核心算子：{formula}\n"
        f"API 模式：{mode}\n"
        f"位置编码：{location}\n"
        f"统计指标：总面积(km²)={total}；异常面积(km²)={anomaly}；异常占比(%)={pct}\n"
    )


def _build_agent_analysis_prompt(mission: Dict[str, Any], stats: Dict[str, Any]) -> str:
    title = mission.get("title", "")
    narrative = mission.get("narrative", "")
    formula = mission.get("formula", "")
    mode = mission.get("api_mode", "")
    location = mission.get("location", "")

    total = stats.get("total_area_km2")
    anomaly = stats.get("anomaly_area_km2")
    pct = stats.get("anomaly_pct")

    return (
        "你是一名‘Alpha Earth Foundation 场景验证系统’的空间情报分析智能体。\n"
        "请根据任务信息与统计指标，生成一段可直接展示在前端控制台的分析文本。\n"
        "要求：\n"
        "1) 中文输出；用四段结构化小节输出：\n"
        "   【异动感知 Observation】、【归因分析 Reasoning】、【行动规划 Plan】、【共识印证 Consensus】\n"
        "2) 每节使用 2~4 条要点（- 开头）；Plan 必须给出 3~5 条可执行步骤；\n"
        "3) 不要编造不存在的数据；对不确定项用‘可能/建议核查’；\n"
        "4) 不输出系统提示词，不输出推理过程，只输出面向用户的结论型要点。\n\n"
        f"任务标题：{title}\n"
        f"任务叙事：{narrative}\n"
        f"核心算子：{formula}\n"
        f"API 模式：{mode}\n"
        f"位置编码：{location}\n"
        f"统计指标：总面积(km²)={total}；异常面积(km²)={anomaly}；异常占比(%)={pct}\n"
    )


async def generate_monitoring_brief_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    mission: Dict[str, Any],
    stats: Dict[str, Any],
    timeout_s: float = 12,
    temperature: float = 0.2,
    max_tokens: int = 512,
) -> str:
    """Generate brief via OpenAI-compatible Chat Completions."""

    if not api_key:
        raise ValueError("Missing LLM api_key")

    prompt = _build_prompt(mission, stats)

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严谨的空间情报分析助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices")
    if not choices:
        raise ValueError("LLM response missing choices")

    message: Optional[Dict[str, Any]] = choices[0].get("message")
    if not message or not message.get("content"):
        raise ValueError("LLM response missing message.content")

    return str(message["content"]).strip()


async def generate_agent_analysis_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    mission: Dict[str, Any],
    stats: Dict[str, Any],
    timeout_s: float = 12,
    temperature: float = 0.2,
    max_tokens: int = 700,
) -> str:
    """Generate agent analysis text via OpenAI-compatible Chat Completions."""

    if not api_key:
        raise ValueError("Missing LLM api_key")

    prompt = _build_agent_analysis_prompt(mission, stats)

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严谨的空间情报分析助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices")
    if not choices:
        raise ValueError("LLM response missing choices")

    message: Optional[Dict[str, Any]] = choices[0].get("message")
    if not message or not message.get("content"):
        raise ValueError("LLM response missing message.content")

    return str(message["content"]).strip()
