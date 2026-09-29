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
# Face / identity jobs must NEVER fall through to hybrid_preserve + scene masks
FACE_PATTERNS = re.compile(
    r"\b("
    r"face|faces|facial|eyes?|eyelids?|iris|pupils?|"
    r"hair\s*colou?r|eye\s*colou?r|"
    r"tattoo|tattoos|markings?|freckles?|scar|scars|glyph|glyphs|"
    r"face\s*paint|cheek\s*mark|forehead|"
    r"adetailer|face.?detail|face.?detailer|"
    r"fix\s+(her|his|their|the)\s+face|clean\s+(up\s+)?(her|his|their|the)\s+face|"
    r"face\s+artifacts?|face\s+refine|refine\s+face"
    r")\b",
    re.I,
)

# Safe defaults — never ship denoise 1.0 / strong IP-Adapter as silent preserve defaults
DEFAULT_HYBRID_DENOISE = 0.45
DEFAULT_IPADAPTER_WEIGHT = 0.55
DEFAULT_FACE_I2I_DENOISE = 0.35
DEFAULT_MOOD_I2I_DENOISE = 0.32


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


def is_face_edit_intent(instruction: str) -> bool:
    """True when the ask is about face / eyes / hair color / tattoos / markings."""
    if not instruction:
        return False
    # Adding a flag/object wins over incidental "face" in preserve wording
    if ADD_OBJECT_PATTERNS.search(instruction) and not FACE_PATTERNS.search(instruction):
        return False
    if ADD_OBJECT_PATTERNS.search(instruction) and FACE_PATTERNS.search(instruction):
        # "add freckles to her face" is still a face job; "add flag keep face" is object
        text = instruction.lower()
        if any(w in text for w in ("flag", "sign", "logo", "banner", "building", "wall", "tower")):
            return False
    return bool(FACE_PATTERNS.search(instruction))


def classify_edit_intent(instruction: str) -> str:
    """
    Return pipeline id: i2i | inpaint | controlnet | hybrid | hybrid_preserve.

    Face / identity asks → i2i (caller enables face_detail). Never hybrid_preserve
    with leftover demo masks (church_tower / right_building).
    """
    if is_face_edit_intent(instruction):
        return "i2i"
    if REGEN_PATTERNS.search(instruction):
        return "controlnet"
    if ADD_OBJECT_PATTERNS.search(instruction):
        if PRESERVE_PATTERNS.search(instruction):
            return "hybrid_preserve"
        return "hybrid"
    if MOOD_PATTERNS.search(instruction) and not ADD_OBJECT_PATTERNS.search(instruction):
        return "i2i"
    # Unknown soft edit — mild i2i, not hybrid with a fake building mask
    return "i2i"


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


def mask_region_from_instruction(instruction: str) -> str | None:
    """
    Only return a geometric mask when the text clearly asks for that region.
    Never default to church_tower / right_building — those were one demo still.
    """
    text = (instruction or "").lower()
    if not text:
        return None
    if any(w in text for w in ("church tower", "steeple", "bell tower", "spire")):
        return "church_tower"
    if "church" in text and ("tower" in text or "top" in text):
        return "church_tower"
    if any(w in text for w in ("right building", "right wall", "church wall", "right church")):
        return "right_building"
    if "right" in text and any(w in text for w in ("wall", "building", "church")):
        return "right_building"
    if "sky" in text or "top third" in text or "upper third" in text:
        return "top_third"
    if re.search(r"\bfull\s*(frame|image|mask)?\b", text):
        return "full"
    return None


def plan_edit(
    *,
    instruction: str,
    food_group: str | None = None,
    mode: str = "auto",
    segment_prompt: str = "",
    preserve_subject: bool = True,
) -> dict[str, Any]:
    """Return pipeline plan for edit_image."""
    face_job = is_face_edit_intent(instruction)
    # Face/identity always wins — agents must not force hybrid_preserve + building masks
    if face_job:
        pipeline = "forge_face"
    else:
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
    if not seg and ADD_OBJECT_PATTERNS.search(instruction) and not face_job:
        # Only invent a segment when the instruction names a place to edit
        if "right" in text or "church" in text or "wall" in text:
            seg = "stone wall on the right"
        elif "sky" in text or "background" in text:
            seg = "sky background"

    mask_fallback = None if face_job else mask_region_from_instruction(instruction)

    denoise_i2i = None
    if pipeline == "i2i":
        denoise_i2i = DEFAULT_FACE_I2I_DENOISE if face_job else DEFAULT_MOOD_I2I_DENOISE
    if pipeline == "forge_face":
        denoise_i2i = DEFAULT_FACE_I2I_DENOISE  # used only if Forge unavailable fallback

    notes = list(_pipeline_notes(pipeline))
    if face_job:
        notes.insert(
            0,
            "Face/identity job -> refine_face_forge (YOLO box + Forge region inpaint + Nari). "
            "Never hybrid_preserve / church_tower / right_building. "
            "Fallback if Forge down: Comfy i2i + face_detail.",
        )

    return {
        "pipeline": pipeline,
        "food_group": normalize_food_group(food_group),
        "segment_prompt": seg or None,
        "flag_reference": ref_key,
        "mask_region_fallback": mask_fallback,
        "use_ip_adapter": pipeline in {"hybrid", "hybrid_preserve", "inpaint"},
        "use_controlnet": pipeline in {"controlnet", "hybrid"} and not preserve_subject,
        "face_detail": bool(face_job and pipeline in {"i2i", "forge_face"}),
        "face_job": face_job,
        "preferred_tool": "refine_face_forge" if face_job else "edit_image",
        "denoise_i2i": denoise_i2i,
        "denoise_hybrid": DEFAULT_HYBRID_DENOISE,
        "ipadapter_weight": DEFAULT_IPADAPTER_WEIGHT if pipeline.startswith("hybrid") or pipeline == "inpaint" else None,
        "notes": notes,
        "agent_hint": (
            "Call refine_face_forge (or edit_image with a face ask — auto-routes to Forge). "
            "Keywords: face, eyes, hair color, tattoo, markings. "
            "Do not pass mask_region=right_building/church_tower."
            if face_job
            else "Object/region edits need mask_region or segment_prompt; no silent building fallback."
        ),
    }


def _pipeline_notes(pipeline: str) -> list[str]:
    notes = {
        "forge_face": [
            "Routes to refine_face_forge: detect face box, Forge inpaint, Nari gate.",
        ],
        "i2i": [
            "Mood/lighting or Comfy face_detail fallback; will not reliably add new objects.",
        ],
        "inpaint": ["Regional edit; provide segment_prompt or mask_region (required)."],
        "controlnet": ["Regenerates from scratch with depth+canny lock; SDXL ControlNet required."],
        "hybrid": ["ControlNet base then regional inpaint (may drift subject)."],
        "hybrid_preserve": [
            "Keeps original image; inpaint + IP-Adapter in an explicit mask only "
            "(add-object edits). Requires mask_region or segment_prompt.",
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
                "hint": "Confirm placement matches the mask/segment you requested.",
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
    if plan.get("face_job"):
        checks.append(
            {
                "id": "face_identity",
                "question": "Eye color, hair color, and tattoos/face markings match the source?",
                "hint": "Fail and revert if any drifted — do not keep color/marking changes.",
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
        "note": "Set pass=true/false after visual review. Re-run with adjusted mask or seed if failed.",
    }
