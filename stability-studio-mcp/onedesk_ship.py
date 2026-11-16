"""One Desk beta ship surface — room tools only.

Private Cursor/MCP keeps full ``server.py`` registration. Packaged ``One Desk\\mcp``
sets ship mode so only these tools remain on the FastMCP manager.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Paired with desk.mcp.ship.REQUIRES_MCP / desk.__version__ for beta.
SHIP_VERSION = "0.5.18"
DESK_COMPAT = "0.5.18"
APP_NAME = "OneDesk MCP"

# Owner-locked room set (Document MCP slice + T2I/I2I/Refine/Video + drop Edit).
ROOM_TOOLS: frozenset[str] = frozenset(
    {
        "generate_image",
        "generate_image_guided",
        "generate_image_i2i",
        "edit_image",
        "refine_image_forge",
        "refine_face_forge",
        "refine_region_forge",
        "face_denoise_guide",
        "generate_video",
        "check_wan_assets",
        "get_generation_context",
        "get_prompt_style",
        "resolve_style_lane",
        "compile_image_prompt",
        "resolve_character_loras",
        "check_gpu_backend",
        "check_forge_backend",
        "switch_stills_backend",
    }
)

ENV_SHIP = "ONEDESK_MCP_SHIP"
IDENTITY_NAME = "mcp_identity.json"


def ship_mode_enabled(root: Path | None = None) -> bool:
    """True for packaged One Desk\\mcp (identity present) or host ENV.

    Do not place ``mcp_identity.json`` in the private fat tree — that would trim
    Cursor/owner loads. Packaging writes identity only into the nested ship folder.
    """
    flag = (os.environ.get(ENV_SHIP) or "").strip().lower()
    if flag in {"1", "true", "yes", "ship", "onedesk"}:
        return True
    if flag in {"0", "false", "no", "private"}:
        return False
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    return (base / IDENTITY_NAME).is_file()


def identity_payload() -> dict[str, Any]:
    return {
        "app": APP_NAME,
        "version": SHIP_VERSION,
        "desk_compat": DESK_COMPAT,
        "tools": sorted(ROOM_TOOLS),
        "tool_count": len(ROOM_TOOLS),
    }


def write_identity(root: Path | None = None) -> Path:
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    path = base / IDENTITY_NAME
    path.write_text(json.dumps(identity_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def trim_fastmcp_tools(mcp: Any) -> list[str]:
    """Remove every registered tool not in ROOM_TOOLS. Returns removed names."""
    manager = getattr(mcp, "_tool_manager", None)
    tools = getattr(manager, "_tools", None) if manager is not None else None
    if not isinstance(tools, dict):
        return []
    removed: list[str] = []
    for name in list(tools.keys()):
        if name not in ROOM_TOOLS:
            tools.pop(name, None)
            removed.append(name)
    return sorted(removed)
