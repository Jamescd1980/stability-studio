"""Call Wan2GP MCP tools (streamable HTTP) from Stability Studio."""

from __future__ import annotations

import asyncio
import json
from typing import Any


def _parse_tool_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "structuredContent") and result.structuredContent:
        return dict(result.structuredContent)
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {"raw": text}
    return {"raw": str(result)}


async def _call_tool_async(url: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return _parse_tool_result(result)


def call_wan2gp_tool(url: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(_call_tool_async(url, tool_name, arguments))


def wangp_generate(
    url: str,
    settings: dict[str, Any],
    *,
    wait: bool = True,
    timeout_s: float = 3600,
    event_limit: int = 20,
) -> dict[str, Any]:
    return call_wan2gp_tool(
        url,
        "wangp_generate",
        {
            "source": settings,
            "wait": wait,
            "timeout_s": timeout_s,
            "event_limit": event_limit,
        },
    )


def wangp_get_job(url: str, job_id: str, event_limit: int = 20) -> dict[str, Any]:
    return call_wan2gp_tool(url, "wangp_get_job", {"job_id": job_id, "event_limit": event_limit})
