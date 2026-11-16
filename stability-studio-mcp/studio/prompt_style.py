"""Compact prompt grammar for agents — one style or platform per call."""

from __future__ import annotations

from typing import Any

from studio.hardware_profile import BASIC_STILL_NEGATIVE

from studio.catalog import StyleCatalog

# Jan / Studio Copilot platform ids → catalog styles (see vlm studio-pack/persona/platforms.yaml)
PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    "flux": {
        "label": "Flux / natural language",
        "default_style": "miracle_nsfw",
        "style_ids": ["miracle_nsfw"],
        "architecture": "flux2_klein",
        "length_hint": "30–80 words. Subject, action, style, context. No negative prompt.",
        "format": "natural_language",
    },
    "sdxl": {
        "label": "Photoreal SDXL",
        "default_style": "juggernaut",
        "style_ids": ["juggernaut", "realisian", "realvis_xl"],
        "architecture": "sdxl",
        "length_hint": "Subject first, then action, setting, light. Negatives yes. No Illustrious quality line.",
        "format": "comma_tags",
    },
    "pony": {
        "label": "Pony SDXL",
        "default_style": "pony",
        "style_ids": ["pony", "merged_dreams"],
        "architecture": "pony_sdxl",
        "length_hint": "score_9 line first, then comma phrases (not tag walls)",
        "format": "pony_scores",
    },
    "illustrious": {
        "label": "Illustrious / anime SDXL",
        "default_style": "unholy_desire",
        "style_ids": [
            "unholy_desire",
            "thumbs_up",
            "ilustmix",
            "anime",
            "animagine_xl",
            "aom2",
            "homochi",
            "perfection_25d",
            "noobai_vpred",
            "waijfu",
            "n4mik4",
        ],
        "architecture": "sdxl_anime",
        "length_hint": "Comma tags after the auto quality prefix. Negatives yes. Do not say camera.",
        "format": "danbooru_tags",
    },
    "wan_image": {
        "label": "Wan video still / motion prompt",
        "default_style": "i2v_5b",
        "workflow_ids": ["i2v_5b", "i2v_5b_painter", "t2v"],
        "architecture": "wan_video",
        "length_hint": "Short motion sentence. Do not re-describe the still face or eyes.",
        "format": "cinematography",
    },
    "wan_video": {
        "label": "Wan video (alias of wan_image)",
        "default_style": "i2v_5b",
        "workflow_ids": ["i2v_5b", "i2v_5b_painter", "t2v"],
        "architecture": "wan_video",
        "length_hint": "Short motion sentence. Do not re-describe the still face or eyes.",
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
    "Do's → positive prompt; Don'ts → negative prompt. Never mix.",
    "Lexicon: 'gold standard' / detail hero / recreate 003 = resolve_style_lane + LoRAs/settings — NEVER paste those words into Positive/Negative for Forge/Comfy.",
    "AUTO-INJECT: generate_image(style=…) prepends that style's prompt_prefix and merges its default negative with the negative you pass. Always read prompt_prefix from get_prompt_style and do NOT repeat those words in Positive.",
    "BASIC NEGATIVE (Illustrious, Pony, photoreal SDXL — not Flux): always keep bad hands, poorly drawn hands, extra fingers, missing fingers, fused fingers, deformed fingers, mutated hands, extra limbs, bad anatomy. Scene don'ts go after that block. Do not drop hands or fingers to keep the line short. generate_image puts the block back if you leave it out. Flux stays an empty negative.",
    "Match the family. Illustrious (unholy_desire, thumbs_up, ilustmix): comma tags after the auto quality line, negatives yes, do not say camera. Pony: score_9 line first. Photoreal SDXL (juggernaut): subject first, negatives yes. Flux (miracle_nsfw only): sentences, subject then action then style then context, no negative, camera language is fine. Do not mix these.",
    "Style tags are optional. Ask and explain in one sentence each; add only yeses: anime illustration (anime drawing), anime style (harder anime medium), anime++ (sharper anime faces, flatter color), bold outline (thicker ink), cel-shaded coloring (hard shadows; changes mouth and lighting). Eye LoRA triggers such as perfect eyes are not part of this ask.",
    "Call get_prompt_style(style=...) or get_prompt_style(platform=...) before writing Platform/Positive/Negative.",
    "Read doc id 'prompting' (docs/PROMPTING.md) for the full Do/Don't + lexicon table.",
    "Pass catalog style id to generate_image (ilustmix, pony, juggernaut, waijfu) — not checkpoint filenames.",
    "After brainstorming: log_image_prompt with platform, style, prompt_positive, prompt_negative.",
]

# Studio jargon that must never be sent to the diffusion model as prompt text.
HOUSE_LEXICON: dict[str, str] = {
    "gold_standard": (
        "House finish mood/look: resolve_style_lane('gold standard') → waijfu + "
        "illustrious_detail_hero LoRAs + prompt_tail/negative_extra. Not model caption text."
    ),
    "gold standard": (
        "Alias of gold_standard — agent/settings instruction only; never write into Positive/Negative."
    ),
    "detail hero": "Alias of gold_standard look bar (illustrious_detail_hero).",
    "recreate 003": "Alias of gold_standard (recreate_003 bar).",
    "look_profile": "Catalog LoRA/neg stack id — apply via tools, do not prompt the id.",
    "keeper": "Quality bar for a kept still/clip — human/agent gate, not a prompt tag.",
    "prepare wan": "Desk/MCP ready step — not a diffusion prompt.",
}

PROMPT_DO_DONT = {
    "positive_is": "Do's — what should appear (subject, act, setting, light, View framing).",
    "negative_is": "Don'ts — the basic hand and finger block, then scene tags (PIP, unwanted styles/props).",
    "basic_negative": BASIC_STILL_NEGATIVE,
    "never_in_either": [
        "gold standard",
        "gold_standard",
        "detail hero",
        "recreate 003",
        "look_profile",
        "illustrious_detail_hero",
        "resolve_style_lane",
        "keeper",
        "prepare wan",
    ],
}

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
        "prompt_style": (
            PLATFORM_SPECS["illustrious"]["length_hint"]
            if platform == "illustrious" and arch not in {"sdxl_anime"}
            else family.get("prompt_style", "")
        ),
        "food_group": food_group,
        "description": style.get("description", ""),
        "checkpoint": style.get("checkpoint"),
        "prompt_prefix": style.get("prompt_prefix", ""),
        "negative_prompt": style.get("negative_prompt", ""),
        "basic_negative": "" if arch in {"flux2", "flux2_klein"} else BASIC_STILL_NEGATIVE,
        "prompt_examples": prompt_examples,
        "defaults": catalog.resolve_generation_defaults(sid),
        "generate_with": f"generate_image(style={sid!r}, prompt=..., negative_prompt=...)",
        "agent_rules": AGENT_RULES,
        "do_dont": PROMPT_DO_DONT,
        "lexicon": HOUSE_LEXICON,
        "prompting_doc": "prompting",
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
        "do_dont": PROMPT_DO_DONT,
        "lexicon": HOUSE_LEXICON,
        "prompting_doc": "prompting",
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
        "do_dont": PROMPT_DO_DONT,
        "lexicon": HOUSE_LEXICON,
        "prompting_doc": "prompting",
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
        "usage": (
            "Call again with style=ilustmix | platform=pony | food_group=anime. "
            "Do's=positive, Don'ts=negative. Lexicon: gold standard = lane/LoRAs — not prompt text. "
            "Full table: read_studio_doc(doc='prompting')."
        ),
        "platforms": platforms,
        "food_groups": {
            k: {"default_style": v.get("default_style"), "label": v.get("label")}
            for k, v in (catalog.art_food_groups or {}).items()
        },
        "agent_rules": AGENT_RULES,
        "do_dont": PROMPT_DO_DONT,
        "lexicon": HOUSE_LEXICON,
        "prompting_doc": "prompting",
    }
