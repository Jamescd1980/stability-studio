from __future__ import annotations

import re

# Illustrious / Pony models expect explicit negatives to suppress NSFW output.
SFW_NEGATIVE_BLOCK = (
    "nsfw, explicit, nude, naked, nipples, genitals, sex, sexual, porn, pornographic, "
    "erotic, lewd, hentai, ecchi, spread legs, undressed, topless, bottomless, "
    "suggestive pose, fetish, bondage"
)

SFW_POSITIVE_ANCHORS = "fully clothed, appropriate attire, safe for work, non-explicit"

SCENE_ANCHORS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(stage|podium|speech|rally|conference|press|american flag|flag behind)\b",
            re.I,
        ),
        "public event, on stage, formal clothing, suit and tie, speaking pose, "
        "american flag backdrop, dramatic stage lighting, crowd optional",
    ),
    (
        re.compile(r"\b(portrait|headshot|bust)\b", re.I),
        "portrait composition, shoulders up, neutral background",
    ),
]


def apply_content_policy(
    *,
    prompt: str,
    positive_prefix: str,
    negative_prompt: str,
    content_rating: str = "open",
) -> tuple[str, str]:
    rating = (content_rating or "open").lower().strip()
    if rating not in {"sfw", "safe"}:
        pos_parts = [p for p in (positive_prefix, prompt) if p]
        return ", ".join(pos_parts) if pos_parts else prompt, negative_prompt

    pos_parts = [p for p in (positive_prefix, SFW_POSITIVE_ANCHORS, prompt) if p]
    full_prompt = ", ".join(pos_parts)

    for pattern, anchors in SCENE_ANCHORS:
        if pattern.search(prompt):
            full_prompt = f"{full_prompt}, {anchors}"
            break

    neg_parts = [negative_prompt, SFW_NEGATIVE_BLOCK]
    full_negative = ", ".join(p for p in neg_parts if p)
    return full_prompt, full_negative


def is_nsfw_checkpoint_name(filename: str) -> bool:
    lower = filename.lower()
    markers = (
        "nsfw",
        "illustrious",
        "uncensored",
        "lust",
        "miraclein",
        "tastysin",
        "n4mik4",
        "mergedindreams",
    )
    return any(m in lower for m in markers)


def resolve_style_for_rating(style_id: str, checkpoint: str, content_rating: str) -> tuple[str, str]:
    """Honor catalog checkpoint unless user explicitly requests SFW filtering."""
    rating = (content_rating or "open").lower()
    if rating not in {"sfw", "safe"}:
        return style_id, checkpoint

    if is_nsfw_checkpoint_name(checkpoint):
        return style_id, "juggernautXL_ragnarokBy.safetensors"

    return style_id, checkpoint
