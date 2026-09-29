"""Read/write One Desk user preferences without editing catalog.yaml."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _desk_settings_path() -> Path:
    override = (os.environ.get("ONE_DESK_SETTINGS") or "").strip()
    if override:
        return Path(override)
    # Mirror desk-ui default
    return Path(os.path.expanduser(r"~\Documents\Desk\settings.json"))


def load_desk_settings() -> dict[str, Any]:
    path = _desk_settings_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_desk_settings_patch(patch: dict[str, Any]) -> dict[str, Any]:
    path = _desk_settings_path()
    data = load_desk_settings()
    data.update(patch or {})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def get_user_preferences() -> dict[str, Any]:
    s = load_desk_settings()
    workflows = s.get("workflows") or []
    active_id = s.get("active_workflow_id") or (workflows[0].get("id") if workflows else "default")
    active = None
    for w in workflows:
        if isinstance(w, dict) and w.get("id") == active_id:
            active = w
            break
    if active is None and workflows:
        active = workflows[0] if isinstance(workflows[0], dict) else None
    primary = (active or {}).get("primary_style") or s.get("primary_style") or "waijfu"
    override = str(s.get("style_override") or "").strip()
    return {
        "ok": True,
        "path": str(_desk_settings_path()),
        "active_workflow_id": active_id,
        "active_workflow": active,
        "primary_style": primary,
        "style_override": override,
        "effective_style": override or primary,
        "food_group": (active or {}).get("food_group") or "anime",
        "style_last_used": s.get("style_last_used") or "",
        "nari_light_footprint": bool(s.get("nari_light_footprint")),
        "nari_num_gpu": s.get("nari_num_gpu"),
        "note": "Cyberpunk food_group = house semi-real. Do not edit catalog.yaml for user prefs.",
    }


def update_user_preferences(patch_json: str = "{}") -> dict[str, Any]:
    try:
        patch = json.loads(patch_json) if isinstance(patch_json, str) else (patch_json or {})
    except Exception as e:
        return {"ok": False, "error": f"Invalid JSON: {e}"}
    if not isinstance(patch, dict):
        return {"ok": False, "error": "patch must be an object"}
    # Never allow catalog path writes through this API
    patch.pop("catalog", None)
    s = load_desk_settings()
    for key in (
        "style_override",
        "style_last_used",
        "active_workflow_id",
        "workflows",
        "nari_light_footprint",
        "nari_num_gpu",
        "new_user_guidance",
        "guided_complete",
        "guided_offer_seen",
    ):
        if key in patch:
            s[key] = patch[key]
    if "primary_style" in patch and isinstance(s.get("workflows"), list):
        aid = s.get("active_workflow_id")
        for w in s["workflows"]:
            if isinstance(w, dict) and w.get("id") == aid:
                w["primary_style"] = patch["primary_style"]
                break
    path = _desk_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(s, indent=2), encoding="utf-8")
    out = get_user_preferences()
    out["ok"] = True
    return out
