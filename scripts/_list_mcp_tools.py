"""List MCP tools registered in server.py via @mcp.tool decorators."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(r"D:\studio-agent\onedesk-mcp")
SERVER = ROOT / "server.py"
src = SERVER.read_text(encoding="utf-8")

# @mcp.tool(...) or @mcp.tool
pat = re.compile(
    r"@mcp\.tool(?:\([^)]*\))?\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
names = pat.findall(src)
uniq = sorted(set(names))
print(f"COUNT={len(names)} UNIQUE={len(uniq)}")
for n in uniq:
    print(n)

# group heuristically
GROUPS = {
    "context": [],
    "generate": [],
    "edit": [],
    "video": [],
    "audio": [],
    "assets": [],
    "health_lock": [],
    "media": [],
    "docs": [],
    "other": [],
}
for n in uniq:
    low = n.lower()
    if any(k in low for k in ("onboarding", "generation_context", "project_context", "prompt_style", "art_food", "list_styles", "list_checkpoints", "list_loras", "list_video", "list_baked", "list_character", "list_set", "list_solid", "list_studio", "list_nsfw", "list_source", "list_media", "list_delivery", "list_pose", "list_image_prompt")):
        GROUPS["context"].append(n)
    elif any(k in low for k in ("generate_image", "compile_image", "suggest_asset", "log_image", "resolve_style", "resolve_character", "lookup_character", "get_action")):
        GROUPS["generate"].append(n)
    elif any(k in low for k in ("edit_image", "inpaint", "plan_image", "setup_image", "check_image", "controlnet", "ip_adapter", "pose_control", "extract_control", "face_detail", "refine_image", "generate_image_forge", "switch_stills")):
        GROUPS["edit"].append(n)
    elif any(k in low for k in ("video", "wan", "i2v", "polish", "interpolate", "upscale_video", "concat", "splice", "gate_i2v", "extract_chain", "recommend_polish", "hunyuan", "storyboard", "scene_sequence", "renpy", "painter")):
        GROUPS["video"].append(n)
    elif any(k in low for k in ("audio", "moss", "kokoro", "speech", "phonetic")):
        GROUPS["audio"].append(n)
    elif any(k in low for k in ("download_", "check_", "install_", "setup_", "scan_models", "reload_catalog", "sync_checkpoint", "register_blender", "get_blender")):
        GROUPS["assets"].append(n)
    elif any(k in low for k in ("gpu", "comfy_queue", "unload_nari", "check_backend", "check_forge", "check_wan2gp", "release_gpu", "check_local_post", "check_kokoro", "check_ebsynth")):
        GROUPS["health_lock"].append(n)
    elif any(k in low for k in ("delivery", "view_delivery", "copy_delivery", "move_delivery", "rename_delivery", "open_delivery", "recycle", "list_media", "list_source")):
        GROUPS["media"].append(n)
    elif any(k in low for k in ("doc", "lesson", "append_project", "fetch_web", "search_studio", "read_studio", "append_lesson")):
        GROUPS["docs"].append(n)
    else:
        GROUPS["other"].append(n)

print("\n--- GROUPS ---")
for g, items in GROUPS.items():
    print(f"{g}: {len(items)}")
