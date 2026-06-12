"""Edit intent classification, art food groups, and pipeline planning."""

from __future__ import annotations

import re
from typing import Any

# Four art "food groups" — keep in sync with catalog.yaml art_food_groups
ART_FOOD_GROUPS: dict[str, dict[str, Any]] = {
    "anime": {
        "label": "Anime",
        "description": "ilustmix, Illustrious, Animagine XL, AbyssOrangeMix2",
        "default_style": "ilustmix",
        "styles": ["anime", "ilustmix", "animagine_xl", "aom2"],
        "edit_style_sdxl": "ilustmix",
        "prompt_hint": "masterpiece, best quality, anime illustration",
    },
    "fantasy": {
        "label": "Fantasy art",
        "description": "Merged In Dreams (Pony), Pony XL — prompt with score_9 prefix + fantasy scene tags",
        "default_style": "merged_dreams",
        "styles": ["merged_dreams", "pony"],
        "edit_style_sdxl": "merged_dreams",
        "prompt_hint": "score_9, score_8_up, elegant fantasy, magical atmosphere, ethereal lighting, highly detailed",
    },
    "cyberpunk": {
        "label": "Cyberpunk",
        "description": "n4mik4 polished heroes; add cyberpunk/neon in prompt for dystopia",
        "default_style": "n4mik4",
        "styles": ["n4mik4", "juggernaut"],
        "edit_style_sdxl": "n4mik4",
        "prompt_hint": "cinematic, highly detailed, masterpiece",
    },
    "photoreal": {
        "label": "Photorealistic",
        "description": "Juggernaut cinematic SDXL and Flux2 miracle_nsfw",
        "default_style": "juggernaut",
        "styles": ["juggernaut", "miracle_nsfw"],
        "edit_style_sdxl": "juggernaut",
        "prompt_hint": "photorealistic, natural lighting, highly detailed",
    },
}

ADD_OBJECT_PATTERNS = re.compile(
    r"\b(add|insert|place|put|mount|attach|include|with a|with an|flag|sign|logo|banner)\b",
    re.I,
)
REGEN_PATTERNS = re.compile(
    r"\b(from scratch|regenerate|same composition|same pose|same layout|recreate)\b",
    re.I,
)
MOOD_PATTERNS = re.compile(
    r"\b(lighting|mood|color grade|atmosphere|slightly|subtle|warmer|cooler|darker|brighter)\b",
    re.I,
)
PRESERVE_PATTERNS = re.compile(
    r"\b(keep|preserve|same knight|same subject|identical|do not change|unchanged)\b",
    re.I,
)


def normalize_food_group(name: str | None) -> str | None:
    if not name:
        return None
    key = name.lower().strip().replace(" ", "_").replace("-", "_")
    aliases = {
        "photo": "photoreal",
        "realistic": "photoreal",
        "photorealistic": "photoreal",
        "illustration": "anime",
        "ilustmix": "anime",
        "animagine": "anime",
        "elegance": "fantasy",
        "divine": "fantasy",
        "cyber": "cyberpunk",
        "neon": "cyberpunk",
    }
    key = aliases.get(key, key)
    return key if key in ART_FOOD_GROUPS else None


def resolve_style_for_edit(
    *,
    food_group: str | None,
    style: str | None,
    architecture: str | None,
    catalog: Any,
) -> tuple[str, str]:
    """Return (style_id, architecture) for an edit job."""
    if style:
        sid = catalog._find_style_key(style)
        arch = catalog.resolve_architecture(sid)
        return sid, arch

    fg = normalize_food_group(food_group)
    if fg:
        meta = ART_FOOD_GROUPS[fg]
        default = meta.get("edit_style_sdxl") or meta["default_style"]
        if default in catalog.styles:
            return default, catalog.resolve_architecture(default)

    default = catalog.cfg.get("default_style", "juggernaut")
    sid = catalog._find_style_key(default)
    return sid, catalog.resolve_architecture(sid)


def classify_edit_intent(instruction: str) -> str:
    """
    Return pipeline id: i2i | inpaint | controlnet | hybrid | hybrid_preserve.
    """
    if REGEN_PATTERNS.search(instruction):
        return "controlnet"
    if ADD_OBJECT_PATTERNS.search(instruction):
        if PRESERVE_PATTERNS.search(instruction):
            return "hybrid_preserve"
        return "hybrid"
    if MOOD_PATTERNS.search(instruction) and not ADD_OBJECT_PATTERNS.search(instruction):
        return "i2i"
    return "hybrid_preserve"


def enrich_edit_prompts(instruction: str, food_group: str | None) -> tuple[str, str]:
    """Build prompt/negative additions from instruction heuristics."""
    prompt = instruction.strip()
    negatives: list[str] = []

    text = instruction.lower()
    if "irish" in text or "ireland" in text or "tricolor" in text:
        if "green white orange" not in text and "tricolor" not in text:
            prompt += ", green white orange vertical tricolor flag"
        negatives.extend(["orange armor", "orange cross on helmet", "flag on cross", "flag on steeple"])

    if "flag" in text:
        negatives.append("abstract flag, blurry flag")

    fg = normalize_food_group(food_group)
    if fg and fg in ART_FOOD_GROUPS:
        hint = ART_FOOD_GROUPS[fg].get("prompt_hint")
        if hint and hint.split(",")[0].lower() not in prompt.lower():
            prompt = f"{hint}, {prompt}"

    negatives.extend(["blurry background", "shifted ruins", "deformed subject", "watermark"])
    neg = ", ".join(dict.fromkeys(negatives))
    return prompt, neg


def plan_edit(
    *,
    instruction: str,
    food_group: str | None = None,
    mode: str = "auto",
    segment_prompt: str = "",
    preserve_subject: bool = True,
) -> dict[str, Any]:
    """Return pipeline plan for edit_image."""
    pipeline = mode.lower().strip() if mode and mode != "auto" else classify_edit_intent(instruction)
    if pipeline == "hybrid" and preserve_subject:
        pipeline = "hybrid_preserve"

    ref_key = None
    text = instruction.lower()
    if "irish" in text or "ireland" in text:
        ref_key = "ireland_flag"
    elif "american" in text or "usa flag" in text:
        ref_key = "usa_flag"
    elif "british" in text or "uk flag" in text:
        ref_key = "uk_flag"

    seg = segment_prompt.strip()
    if not seg and ADD_OBJECT_PATTERNS.search(instruction):
        if "right" in text or "church" in text or "wall" in text:
            seg = "stone church wall on the right"
        elif "sky" in text or "background" in text:
            seg = "sky background"

    return {
        "pipeline": pipeline,
        "food_group": normalize_food_group(food_group),
        "segment_prompt": seg or None,
        "flag_reference": ref_key,
        "mask_region_fallback": "right_building" if "right" in text else "church_tower",
        "use_ip_adapter": pipeline in {"hybrid", "hybrid_preserve", "inpaint"},
        "use_controlnet": pipeline in {"controlnet", "hybrid"} and not preserve_subject,
        "denoise_i2i": 0.32 if pipeline == "i2i" else None,
        "notes": _pipeline_notes(pipeline),
    }


def _pipeline_notes(pipeline: str) -> list[str]:
    notes = {
        "i2i": ["Good for mood/lighting only; will not reliably add new objects."],
        "inpaint": ["Regional edit; provide segment_prompt or mask_region."],
        "controlnet": ["Regenerates from scratch with depth+canny lock; SDXL ControlNet required."],
        "hybrid": ["ControlNet base then regional inpaint (may drift subject)."],
        "hybrid_preserve": [
            "Keeps original image; inpaint + IP-Adapter in small mask (recommended for add-object edits).",
        ],
    }
    return notes.get(pipeline, [])


def verify_edit_result(
    *,
    instruction: str,
    plan: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Structured review checklist (no vision model — agent/user validates)."""
    saved = result.get("saved_files") or []
    checks: list[dict[str, str]] = []

    text = instruction.lower()
    if "flag" in text:
        checks.append(
            {
                "id": "flag_visible",
                "question": "Is a recognizable flag visible in the intended region?",
                "hint": "Look for green-white-orange vertical stripes on the right church wall, not on the cross.",
            }
        )
    if PRESERVE_PATTERNS.search(instruction):
        checks.append(
            {
                "id": "subject_preserved",
                "question": "Is the main subject (pose, armor, face) unchanged?",
                "hint": "Compare helmet and foreground to the source image.",
            }
        )
    if "church" in text or "ruins" in text or "background" in text:
        checks.append(
            {
                "id": "background_stable",
                "question": "Are ruins/background sharp and in the same place?",
                "hint": "No blur, shift, or melted stonework outside the edit mask.",
            }
        )

    return {
        "instruction": instruction,
        "pipeline_used": plan.get("pipeline"),
        "output_files": saved,
        "manual_checks": checks,
        "pass": None,
        "note": "Set pass=true/false after visual review. Re-run edit_image with adjusted mask or seed if failed.",
    }
