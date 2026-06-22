"""LLM service (OpenAI-compatible) for generating monitoring briefs.

Target provider: DashScope OpenAI compatible mode.
Base URL example: https://dashscope.aliyuncs.com/compatible-mode/v1
Model: qwen-plus

This module is intentionally small and dependency-free (uses httpx).
"""

from typing import Any, Dict, List, Optional

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
        "你是一名'Alpha Earth Demo 场景验证系统'的空间情报分析智能体。\n"
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


async def generate_flavor_text_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    user_prompt: str,
    timeout_s: float = 12,
    temperature: float = 0.4,
    max_tokens: int = 240,
) -> str:
    """Generate short demo narration text via OpenAI-compatible Chat Completions.

    This is intentionally simple and should be called behind a feature flag.
    """

    if not api_key:
        raise ValueError("Missing LLM api_key")

    prompt = (
        "你是一名面向领导汇报场景的空间智能工作台演示解说员。\n"
        "请基于用户指令，生成一段自然、克制、可信的中文讲解文案。\n"
        "要求：\n"
        "1) 80~160 字；\n"
        "2) 不要编造不存在的数据；不确定则用‘可能/建议核查’；\n"
        "3) 不要输出工具名或代码，只输出给观众听的讲解。\n\n"
        f"用户指令：{str(user_prompt or '').strip()}\n"
    )

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


async def plan_tool_calls_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    user_prompt: str,
    tools: List[Dict[str, Any]],
    timeout_s: float = 12,
    temperature: float = 0.2,
    max_tokens: int = 700,
) -> Dict[str, Any]:
    """Ask an OpenAI-compatible model to decide tool calls for a user prompt.

    Returns a dict with:
      - content: optional assistant text (may be empty)
      - tool_calls: list[{name: str, arguments: str}]

    Notes:
    - This should be called behind a feature flag.
    - This function does not execute tools; it only plans calls.
    """

    if not api_key:
        raise ValueError("Missing LLM api_key")

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的空间智能副驾。仅在确有必要时才调用工具，并保证参数是有效 JSON。",
            },
            {"role": "user", "content": str(user_prompt or "").strip()},
        ],
        "tools": tools,
        "tool_choice": "auto",
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
    if not message:
        raise ValueError("LLM response missing message")

    content = str(message.get("content") or "").strip()
    raw_calls = message.get("tool_calls") or []

    tool_calls: List[Dict[str, str]] = []
    if isinstance(raw_calls, list):
        for tc in raw_calls:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function")
            if not isinstance(fn, dict):
                continue
            name = fn.get("name")
            args = fn.get("arguments")
            if not name:
                continue
            tool_calls.append({"name": str(name), "arguments": str(args or "").strip()})

    return {"content": content, "tool_calls": tool_calls}
