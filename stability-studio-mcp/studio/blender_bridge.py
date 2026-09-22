"""Blender MCP ↔ Stability Studio path conventions (GENERATION_HOST Game drive)."""

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
        root = Path("D:/GenerationHost Images and Videos/assets/blender")
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
    """Absolute path on GENERATION_HOST for the same folder."""
    return "<MODELS_MOUNT>/GenerationHost Images and Videos/assets/blender"


def get_blender_workflow_playbook() -> dict[str, Any]:
    """Agent steps: exclusive GPU → Blender pose → Comfy pose-guided still."""
    return {
        "host": "GENERATION_HOST RTX 5090",
        "docs": [
            "BLENDER-MCP.md",
            "POSE-CONTROL.md",
            "ACTION-COMBAT.md",
            "LESSONS-SET-FILL.md",
            "LESSONS-BLENDER-MCP.md",
        ],
        "gpu_exclusivity": {
            "before_blender": "ssh GENERATION_HOST '~/bin/gpu_backend.sh blender'  # stops ComfyUI",
            "before_comfy": "ssh GENERATION_HOST '~/bin/gpu_backend.sh comfy'  # stops Blender",
            "status": "ssh GENERATION_HOST '~/bin/gpu_backend.sh status'",
        },
        "mcp": {
            "cursor_server": "blender",
            "env": {"BLENDER_HOST": "GENERATION_HOST", "BLENDER_PORT": "9876"},
            "start_remote": "~/bin/generation-host_start_blender_mcp.sh",
        },
        "sets": {
            "casting_couch": "D:/GenerationHost Images and Videos/assets/blender/sets/casting_couch",
            "locked_wide_plate": "D:/GenerationHost Images and Videos/assets/blender/sets/casting_couch/plates/camWide_empty_B.png",
            "rule": ".cursor/rules/set-3d-base-ai-style.mdc",
        },
        "character_mesh": {
            "list_tool": "list_character_mesh_assets",
            "darkness": "D:/GenerationHost Images and Videos/assets/characters/Darkness/mesh_source",
            "mesh_glb": "D:/GenerationHost Images and Videos/assets/characters/Darkness/mesh_source/darkness_body_v1.glb",
            "note": "Solid mesh > Body25 sticks for silhouette masks. Keep on GenerationHost.",
        },
        "set_mesh": {
            "list_tool": "list_set_mesh_assets",
            "maps_tool": "list_solid_strip_maps",
            "casting_couch": "D:/GenerationHost Images and Videos/assets/blender/sets/casting_couch",
            "bg_glb": "D:/GenerationHost Images and Videos/assets/blender/sets/casting_couch/mesh/casting_couch_bg_v1.glb",
            "solid_maps": "D:/GenerationHost Images and Videos/assets/blender/sets/casting_couch/strip_maps/solid_mesh_v1",
            "pose_script": "D:/GenerationHost Images and Videos/assets/blender/kits/pose_solid_strip_beats.py",
        },
        "bg_lock_vn_stills": [
            "Do NOT full-frame pose i2i at high denoise on locked plates (walls drift).",
            "Masked inpaint on plate OR rembg oracle → paste → low denoise edge/feet blend.",
            "Outside mask must never enter the sampler.",
            "Solid path: list_solid_strip_maps → gray_cut + mask_inpaint_prep → inpaint_advanced → hardlock.",
        ],
        "steps_solid_strip_fill": [
            "1. gpu_backend.sh blender",
            "2. blender -b -P kits/pose_solid_strip_beats.py  # solid gray_cut/silhouette/depth/pose",
            "3. list_solid_strip_maps(set_id='casting_couch')",
            "4. mask_inpaint_prep.py --plate empty_B --cutout *_gray_cut.png",
            "5. gpu_backend.sh comfy",
            "6. inpaint_advanced(seeded_plate, mask_path=mask_dilate, depth optional)",
            "7. hardlock composite onto pristine empty_B",
        ],
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
