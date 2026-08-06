"""Blender MCP ↔ Stability Studio path conventions (LinuxBox Game drive)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


BLENDER_ASSET_SUBDIRS = ("pose", "depth", "previz")


def blender_assets_root(cfg: dict[str, Any]) -> Path:
    """Game-drive assets folder for Blender exports (shared with Windows delivery)."""
    delivery = (cfg.get("outputs") or {}).get("delivery") or ""
    if delivery:
        root = Path(delivery) / "assets" / "blender"
    else:
        root = Path("D:/ComfyBox Images and Videos/assets/blender")
    return root


def blender_asset_path(
    cfg: dict[str, Any],
    *,
    scene_id: str,
    kind: str = "pose",
    suffix: str = "png",
) -> Path:
    """Return `{delivery}/assets/blender/{kind}/{scene_id}_{kind}.{suffix}`."""
    if kind not in BLENDER_ASSET_SUBDIRS:
        raise ValueError(f"kind must be one of {BLENDER_ASSET_SUBDIRS}, got {kind!r}")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (scene_id or "scene"))
    return blender_assets_root(cfg) / kind / f"{safe}_{kind}.{suffix}"


def linux_game_assets_root() -> str:
    """Absolute path on LinuxBox for the same folder."""
    return "/mnt/game/ComfyBox Images and Videos/assets/blender"


def get_blender_workflow_playbook() -> dict[str, Any]:
    """Agent steps: exclusive GPU → Blender pose → Comfy pose-guided still."""
    return {
        "host": "LinuxBox RTX 5090",
        "docs": ["BLENDER-MCP.md", "POSE-CONTROL.md", "ACTION-COMBAT.md"],
        "gpu_exclusivity": {
            "before_blender": "ssh Linuxbox '~/bin/gpu_backend.sh blender'  # stops ComfyUI",
            "before_comfy": "ssh Linuxbox '~/bin/gpu_backend.sh comfy'  # stops Blender",
            "status": "ssh Linuxbox '~/bin/gpu_backend.sh status'",
        },
        "mcp": {
            "cursor_server": "blender",
            "env": {"BLENDER_HOST": "192.168.50.57", "BLENDER_PORT": "9876"},
            "start_remote": "~/bin/comfybox_start_blender_mcp.sh",
        },
        "steps_pose_guided_still": [
            "1. gpu_backend.sh blender (free 5090)",
            "2. Ensure Blender MCP listening (:9876) — start script or GUI Connect",
            "3. Use Blender MCP to pose characters / export OpenPose-style PNG",
            "4. Save under assets/blender/pose/{scene_id}_pose.png (Game drive)",
            "5. gpu_backend.sh comfy",
            "6. check_pose_control_readiness()",
            "7. generate_image_pose_guided(image_path=identity, pose_image_path=..., preprocess_pose=false)",
            "8. optional: edit_image → generate_video(mode=i2v, workflow_id=i2v)",
        ],
        "fallback": "OpenPose web editors in POSE-CONTROL.md if Blender MCP is down",
    }


def register_blender_control_maps(
    cfg: dict[str, Any],
    *,
    pose_path: str = "",
    depth_path: str = "",
    scene_id: str = "",
) -> dict[str, Any]:
    """Validate Blender export files exist and return paths for pose-guided tools."""
    out: dict[str, Any] = {"ok": True, "scene_id": scene_id or None, "maps": {}}
    for label, raw in (("pose", pose_path), ("depth", depth_path)):
        if not raw:
            continue
        p = Path(raw)
        exists = p.is_file()
        out["maps"][label] = {
            "path": str(p),
            "exists": exists,
            "size": p.stat().st_size if exists else 0,
        }
        if not exists:
            out["ok"] = False
    if not out["maps"]:
        out["ok"] = False
        out["error"] = "pass pose_path and/or depth_path"
    out["suggested_pose_path"] = str(
        blender_asset_path(cfg, scene_id=scene_id or "scene", kind="pose")
    )
    out["linux_assets_root"] = linux_game_assets_root()
    return out
