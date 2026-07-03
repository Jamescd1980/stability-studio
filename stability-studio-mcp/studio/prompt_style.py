"""Compact prompt grammar for agents — one style or platform per call."""

from __future__ import annotations

from typing import Any

from studio.catalog import StyleCatalog

# Jan / Studio Copilot platform ids → catalog styles (see vlm studio-pack/persona/platforms.yaml)
PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    "flux": {
        "label": "Flux / natural language",
        "default_style": "miracle_nsfw",
        "style_ids": ["miracle_nsfw", "juggernaut", "merged_dreams"],
        "architecture": "flux2_klein",
        "length_hint": "75–150 words natural language",
        "format": "natural_language",
    },
    "sdxl": {
        "label": "SDXL hybrid tags",
        "default_style": "juggernaut",
        "style_ids": ["juggernaut", "ilustmix", "n4mik4", "merged_dreams"],
        "architecture": "sdxl",
        "length_hint": "40–75 tokens; quality tags + compact scene",
        "format": "comma_tags",
    },
    "pony": {
        "label": "Pony SDXL",
        "default_style": "pony",
        "style_ids": ["pony"],
        "architecture": "pony_sdxl",
        "length_hint": "score_9 line first, then comma phrases (not tag walls)",
        "format": "pony_scores",
    },
    "illustrious": {
        "label": "Illustrious / anime SDXL",
        "default_style": "ilustmix",
        "style_ids": ["ilustmix", "anime", "animagine_xl"],
        "architecture": "sdxl_anime",
        "length_hint": "danbooru-style tags; masterpiece/best quality prefix",
        "format": "danbooru_tags",
    },
    "wan_image": {
        "label": "Wan video still / motion prompt",
        "default_style": "i2v_5b",
        "workflow_ids": ["i2v_5b", "i2v_5b_painter", "t2v"],
        "architecture": "wan_video",
        "length_hint": "100–180 words; subject → environment → light → camera → mood",
        "format": "cinematography",
    },
    "wan_video": {
        "label": "Wan video (alias of wan_image)",
        "default_style": "i2v_5b",
        "workflow_ids": ["i2v_5b", "i2v_5b_painter", "t2v"],
        "architecture": "wan_video",
        "length_hint": "100–180 words; motion + scene; natural language",
        "format": "cinematography",
    },
    "qwen_edit": {
        "label": "Flux2 edit instruction",
        "default_style": "miracle_nsfw",
        "style_ids": ["miracle_nsfw"],
        "architecture": "flux2_klein",
        "length_hint": "Short edit instruction (what changes, what stays)",
        "format": "edit_instruction",
    },
}

AGENT_RULES = [
    "Call get_prompt_style(style=...) or get_prompt_style(platform=...) before writing Platform/Positive/Negative.",
    "Pass catalog style id to generate_image (ilustmix, pony, juggernaut) — not checkpoint filenames.",
    "After brainstorming: log_image_prompt with platform, style, prompt_positive, prompt_negative.",
]

# When a style appears in multiple platform specs, prefer the more specific id first.
_PLATFORM_LOOKUP_ORDER = (
    "illustrious",
    "pony",
    "flux",
    "qwen_edit",
    "wan_image",
    "sdxl",
    "wan_video",
)


def _normalize_key(value: str) -> str:
    return value.lower().strip().replace(" ", "_").replace("-", "_")


def _style_guide(catalog: StyleCatalog, style_id: str) -> dict[str, Any]:
    sid = catalog._find_style_key(style_id)
    style = catalog.styles[sid]
    arch = catalog.resolve_architecture(sid)
    family = catalog.resolve_family(arch)
    food_group = ""
    for fg_id, fg in (catalog.art_food_groups or {}).items():
        if sid in (fg.get("styles") or []):
            food_group = fg_id
            break
    platform = ""
    for pid in _PLATFORM_LOOKUP_ORDER:
        spec = PLATFORM_SPECS.get(pid, {})
        if sid in (spec.get("style_ids") or []):
            platform = pid
            break
    prompt_examples = style.get("prompt_examples") or {}
    return {
        "style": sid,
        "platform": platform or arch,
        "architecture": arch,
        "family_label": family.get("label", arch),
        "prompt_style": family.get("prompt_style", ""),
        "food_group": food_group,
        "description": style.get("description", ""),
        "checkpoint": style.get("checkpoint"),
        "prompt_prefix": style.get("prompt_prefix", ""),
        "negative_prompt": style.get("negative_prompt", ""),
        "prompt_examples": prompt_examples,
        "defaults": catalog.resolve_generation_defaults(sid),
        "generate_with": f"generate_image(style={sid!r}, prompt=..., negative_prompt=...)",
        "agent_rules": AGENT_RULES,
    }


def _platform_guide(catalog: StyleCatalog, platform_id: str) -> dict[str, Any]:
    key = _normalize_key(platform_id)
    if key not in PLATFORM_SPECS:
        known = ", ".join(sorted(PLATFORM_SPECS))
        raise ValueError(f"Unknown platform {platform_id!r}. Known: {known}")
    spec = PLATFORM_SPECS[key]
    default_style = spec.get("default_style")
    out: dict[str, Any] = {
        "platform": key,
        "label": spec["label"],
        "format": spec["format"],
        "length_hint": spec["length_hint"],
        "default_style": default_style,
        "style_ids": spec.get("style_ids") or [],
        "workflow_ids": spec.get("workflow_ids") or [],
        "agent_rules": AGENT_RULES,
    }
    if default_style and default_style in catalog.styles:
        out["recommended"] = _style_guide(catalog, default_style)
    elif spec.get("architecture"):
        family = catalog.resolve_family(spec["architecture"])
        out["architecture"] = spec["architecture"]
        out["prompt_style"] = family.get("prompt_style", "")
    return out


def _food_group_guide(catalog: StyleCatalog, food_group: str) -> dict[str, Any]:
    fg_id = _normalize_key(food_group)
    groups = catalog.art_food_groups or {}
    if fg_id not in groups:
        known = ", ".join(sorted(groups))
        raise ValueError(f"Unknown food_group {food_group!r}. Known: {known}")
    fg = groups[fg_id]
    default_style = fg.get("default_style", "")
    out: dict[str, Any] = {
        "food_group": fg_id,
        "label": fg.get("label", fg_id),
        "default_style": default_style,
        "styles": fg.get("styles", []),
        "prompt_guide": fg.get("prompt_guide", ""),
        "agent_rules": AGENT_RULES,
    }
    if default_style:
        out["recommended"] = _style_guide(catalog, default_style)
    return out


def build_prompt_style_guide(
    catalog: StyleCatalog,
    *,
    style: str = "",
    platform: str = "",
    food_group: str = "",
) -> dict[str, Any]:
    """Return a small prompt grammar payload for agents (Jan, Cursor, OI)."""
    if style:
        return {"lookup": "style", **_style_guide(catalog, style)}
    if platform:
        return {"lookup": "platform", **_platform_guide(catalog, platform)}
    if food_group:
        return {"lookup": "food_group", **_food_group_guide(catalog, food_group)}
    platforms = {
        pid: {
            "label": spec["label"],
            "default_style": spec.get("default_style"),
            "format": spec["format"],
        }
        for pid, spec in PLATFORM_SPECS.items()
        if pid != "wan_video"
    }
    return {
        "lookup": "index",
        "usage": "Call again with style=ilustmix | platform=pony | food_group=anime",
        "platforms": platforms,
        "food_groups": {
            k: {"default_style": v.get("default_style"), "label": v.get("label")}
            for k, v in (catalog.art_food_groups or {}).items()
        },
        "agent_rules": AGENT_RULES,
    }
