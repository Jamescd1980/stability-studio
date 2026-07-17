"""Combat / fight still playbook — pose-first pipeline (no one-shot T2I)."""

from __future__ import annotations

import re
from typing import Any

# Rows with these in `action` should set needs_pose=true (or auto-inferred).
COMBAT_ACTION_RE = re.compile(
    r"\b("
    r"fight|fighting|combat|battle|duel|stab|stabbing|knife|sword|blade|"
    r"kill|killing|attack|punch|kick|lunge|strike|martial|karate|"
    r"blood|gore|wound|injury|weapon|face.?to.?face|close.?quarters|"
    r"soldier.*soldier|vs\.|versus"
    r")\b",
    re.I,
)

# Prevents rifle-knife fusion when prompt asks for blades only.
FIREARM_NEGATIVE_BLOCK = (
    "gun, rifle, firearm, assault_rifle, bayonet, muzzle, scope, grenade, "
    "pistol, machine_gun, sniper, barrel, magazine, holstered_gun"
)

OPENPOSE_EDITORS = [
    {
        "name": "OpenPose Editor (Vercel)",
        "url": "https://openpose-editor.vercel.app/",
        "notes": "Set canvas to target width×height (e.g. 1216×832). Two skeletons for face-to-face combat.",
    },
    {
        "name": "Open Pose Editor (Zhuyu)",
        "url": "https://zhuyu1997.github.io/open-pose-editor/",
        "notes": "Hand keypoints; export pose PNG.",
    },
]

WORKFLOW_STEPS: list[dict[str, Any]] = [
    {
        "step": 1,
        "phase": "prepare",
        "tool": "get_prompt_style",
        "args": {"platform": "action_combat"},
        "note": "Tag grammar + negatives — danbooru tags on WAI (style anime), not photoreal paragraphs.",
    },
    {
        "step": 2,
        "phase": "prepare",
        "tool": "check_pose_control_readiness",
        "on_missing": "setup_pose_control",
        "note": "Restart ComfyUI after setup if required.",
    },
    {
        "step": 3,
        "phase": "layout",
        "action": "human",
        "title": "OpenPose export",
        "urls": OPENPOSE_EDITORS,
        "note": "Pose TWO figures for face-to-face beats; extend striker arm to target head/chest.",
    },
    {
        "step": 4,
        "phase": "keyframe",
        "tool": "generate_image_pose_guided",
        "required_params": {
            "preprocess_pose": False,
            "face_detail": False,
            "denoising_strength": "0.32–0.45",
            "openpose_strength": "0.82–0.90",
        },
        "note": "image_path = identity still or neutral base; pose_image_path = editor PNG.",
        "forbidden": "generate_image one-shot T2I for multi-person contact",
    },
    {
        "step": 5,
        "phase": "detail",
        "tool": "edit_image",
        "optional": True,
        "note": "Small mask on face/weapon — blade contact, blood, impact. Not full-frame T2I.",
    },
    {
        "step": 6,
        "phase": "motion",
        "tool": "generate_video",
        "optional": True,
        "args": {"mode": "i2v", "workflow_id": "i2v_5b_painter", "motion_amplitude": "1.15–1.2"},
        "note": "Video rows: keyframe still first, then i2v from approved image.",
    },
]

STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "anime": {
        "style": "anime",
        "platform": "illustrious",
        "checkpoint": "waiIllustriousSDXL_v160.safetensors",
        "label": "WAI Illustrious XL v16 (action default)",
        "width": 1216,
        "height": 832,
        "face_detail": False,
        "positive_template": (
            "masterpiece, best quality, {subjects}, face_to_face, {setting}, {lighting}, "
            "dynamic_pose, fighting, {weapon_tags}, military_uniform, camouflage, "
            "tactical_vest, action, motion_blur, cowboy_shot"
        ),
        "negative_template": (
            "lowres, bad anatomy, bad hands, solo, 1boy, standing, portrait, looking_at_viewer, "
            "daytime, sunlight, bright, overexposed, blurry_weapon, extra_fingers, {firearm_neg}"
        ),
        "example_weapon_tags": "holding_knife, knife, stabbing, blood",
        "example_positive": (
            "masterpiece, best quality, 2boys, face_to_face, night, jungle, tree, moonlight, dark, "
            "dynamic_pose, fighting, holding_knife, knife, stabbing, blood, military_uniform, "
            "camouflage, tactical_vest, helmet, action, motion_blur, cowboy_shot"
        ),
    },
    "pony": {
        "style": "pony",
        "platform": "pony",
        "width": 1216,
        "height": 832,
        "face_detail": False,
        "positive_template": (
            "score_9, score_8_up, rating_questionable, {subjects}, face_to_face, "
            "{setting}, {lighting}, dynamic_pose, {weapon_tags}, action, "
            "military_uniform, camouflage, motion_blur"
        ),
        "negative_template": (
            "score_6, score_5, score_4, solo, standing, portrait, daytime, bright_sunlight, "
            "blurry_weapon, extra_fingers, {firearm_neg}"
        ),
        "example_weapon_tags": "holding_knife, knife, stabbing, blood",
    },
    "juggernaut": {
        "style": "juggernaut",
        "platform": "sdxl",
        "width": 1216,
        "height": 832,
        "face_detail": False,
        "positive_template": (
            "cinematic wide shot, two soldiers {setting}, {lighting}, close quarters fight, "
            "{action_line}, combat knife only, no guns, tactical gear, sharp focus, "
            "35mm combat photography"
        ),
        "negative_template": (
            "solo portrait, standing pose, smiling, daytime, overexposed, blurry weapons, "
            "extra fingers, {firearm_neg}"
        ),
        "example_action_line": "one soldier stabbing the other with a combat knife",
    },
    "ilustmix": {
        "style": "ilustmix",
        "platform": "illustrious",
        "width": 1216,
        "height": 832,
        "face_detail": False,
        "warning": "Pinup/dialogue bias — use style anime (WAI) for combat instead.",
        "positive_template": (
            "masterpiece, best quality, 2boys, face_to_face, dynamic_pose, "
            "{weapon_tags}, {setting}, {lighting}, action"
        ),
        "negative_template": (
            "solo, portrait, photorealistic, {firearm_neg}"
        ),
        "example_weapon_tags": "holding_knife, knife, stabbing",
    },
}

AGENT_RULES = [
    "Combat default checkpoint: style anime (WAI Illustrious) — not ilustmix.",
    "Combat rows: needs_pose=true — never generate_image one-shot for multi-person weapon contact.",
    "Call get_prompt_style(platform=action_combat) or get_action_combat_playbook(style=anime) before prompts.",
    "Always face_detail=false; use wide aspect (1216×832), not square portrait.",
    "Negate gun/rifle/bayonet when scene uses knife only — prevents rifle-knife fusion.",
    "Gore/blade-in-face: keyframe pose first, then edit_image inpaint on small mask.",
    "Unload Jan model from VRAM before generate_image / pose-guided / video.",
]


def infer_needs_pose(row: dict[str, str]) -> bool:
    """True when sheet row is combat-heavy or needs_pose column is set."""
    flag = (row.get("needs_pose") or "").strip().lower()
    if flag in {"1", "true", "yes", "y"}:
        return True
    if flag in {"0", "false", "no", "n"}:
        return False
    action = row.get("action") or ""
    prompt = row.get("prompt_positive") or ""
    return bool(COMBAT_ACTION_RE.search(action) or COMBAT_ACTION_RE.search(prompt))


def resolve_combat_style(row: dict[str, str]) -> str:
    raw = (row.get("style") or "").strip().lower()
    if raw in STYLE_PRESETS:
        return raw
    if raw in {"wai", "wai_illustrious", "action_anime"}:
        return "anime"
    if raw in {"illustrious"}:
        return "anime"
    if raw == "ilustmix":
        return "ilustmix"
    if raw in {"photoreal", "realistic"}:
        return "juggernaut"
    return "anime"


def build_action_combat_playbook(
    *,
    style: str = "anime",
    look: str = "",
) -> dict[str, Any]:
    """Machine-readable combat still pipeline for agents."""
    style_key = (look or style or "anime").strip().lower()
    if style_key in {"wai", "wai_illustrious", "action_anime", "illustrious"}:
        style_key = "anime"
    if style_key == "ilustmix":
        style_key = "ilustmix"
    elif style_key in {"photoreal", "realistic", "photo"}:
        style_key = "juggernaut"
    preset = STYLE_PRESETS.get(style_key, STYLE_PRESETS["anime"])

    neg_extra = preset.get("negative_template", "").format(firearm_neg=FIREARM_NEGATIVE_BLOCK)
    return {
        "playbook": "action_combat",
        "summary": "Pose-first multi-step pipeline for fight/stab/gore stills. One-shot T2I will fail.",
        "agent_rules": AGENT_RULES,
        "workflow_steps": WORKFLOW_STEPS,
        "openpose_editors": OPENPOSE_EDITORS,
        "firearm_negative_block": FIREARM_NEGATIVE_BLOCK,
        "recommended_style": preset["style"],
        "preset": {
            **preset,
            "negative_template": neg_extra,
            "firearm_neg": FIREARM_NEGATIVE_BLOCK,
        },
        "generate_pose_guided": {
            "tool": "generate_image_pose_guided",
            "style": preset["style"],
            "width": preset["width"],
            "height": preset["height"],
            "face_detail": False,
            "preprocess_pose": False,
            "denoising_strength": 0.38,
            "openpose_strength": 0.85,
            "negative_prompt_append": FIREARM_NEGATIVE_BLOCK,
        },
        "forbidden": [
            "generate_image one-shot for two-person weapon contact",
            "long photoreal paragraph on pony/anime without pose PNG",
            "face_detail=true on action beats",
            "square 1024×1024 for wide combat compositions",
        ],
        "doc": "ACTION-COMBAT.md",
    }


def generation_queue_entry(row: dict[str, str]) -> dict[str, Any]:
    """Queue item for combat rows — pose pipeline, not plain T2I."""
    style = resolve_combat_style(row)
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["anime"])
    playbook = build_action_combat_playbook(style=style)
    base: dict[str, Any] = {
        "scene_id": row["scene_id"],
        "workflow": "action_combat",
        "needs_pose": True,
        "tool": "generate_image_pose_guided",
        "forbidden_tools": ["generate_image"],
        "style": preset["style"],
        "width": preset["width"],
        "height": preset["height"],
        "face_detail": False,
        "prompt": row.get("prompt_positive") or row.get("action", ""),
        "negative_prompt": _merge_negatives(row.get("prompt_negative", "")),
        "pose_image_path": "<REQUIRED: OpenPose editor export PNG>",
        "image_path": "<identity still or neutral base image>",
        "playbook_steps": WORKFLOW_STEPS,
        "agent_rules": AGENT_RULES,
        "target": row.get("image_asset") or "",
        "playbook_ref": "get_action_combat_playbook",
    }
    if row.get("type") == "video":
        base["note"] = "Generate keyframe still via pose pipeline first; then generate_video i2v from approved still."
        base["follow_up_tool"] = "generate_video"
        base["follow_up_args"] = {
            "mode": "i2v",
            "workflow_id": "i2v_5b_painter",
            "motion_amplitude": 1.18,
            "smooth_motion": False,
        }
    return base


def _merge_negatives(existing: str) -> str:
    parts = [p.strip() for p in (existing, FIREARM_NEGATIVE_BLOCK) if p and p.strip()]
    return ", ".join(dict.fromkeys(p for part in parts for p in part.split(",")))
