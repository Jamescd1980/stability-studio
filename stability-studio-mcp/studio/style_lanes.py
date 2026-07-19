"""Resolve voice/prompt asks into style_lanes recipes (medium + mood + cast)."""

from __future__ import annotations

import re
from typing import Any


def _lanes(catalog_data: dict[str, Any]) -> dict[str, Any]:
    return dict(catalog_data.get("style_lanes") or {})


def _look_profiles(catalog_data: dict[str, Any]) -> dict[str, Any]:
    return dict(catalog_data.get("look_profiles") or {})


def _alias_hit(text: str, aliases: list[str], label: str = "") -> bool:
    low = text.lower()
    keys = [a.lower() for a in aliases if a]
    if label:
        keys.append(label.lower())
    # Longer aliases first so "retro anime" wins over "anime"
    keys = sorted(set(keys), key=len, reverse=True)
    for a in keys:
        if not a:
            continue
        if " " in a or "-" in a:
            if a in low:
                return True
        elif re.search(rf"\b{re.escape(a)}\b", low):
            return True
    return False


def _match_bucket(text: str, bucket: dict[str, Any]) -> str | None:
    # Prefer longer alias matches across the whole bucket
    scored: list[tuple[int, str]] = []
    for mid, meta in bucket.items():
        if not isinstance(meta, dict):
            continue
        aliases = list(meta.get("aliases") or [])
        label = str(meta.get("label") or mid)
        keys = sorted(
            {*(a.lower() for a in aliases if a), label.lower(), mid.lower().replace("_", " ")},
            key=len,
            reverse=True,
        )
        for a in keys:
            if not a:
                continue
            hit = a in text.lower() if (" " in a or "-" in a) else bool(
                re.search(rf"\b{re.escape(a)}\b", text.lower())
            )
            if hit:
                scored.append((len(a), mid))
                break
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


def _match_cast_axis(text: str, axis_rows: list[dict[str, Any]]) -> str | None:
    scored: list[tuple[int, str]] = []
    low = text.lower()
    for row in axis_rows or []:
        rid = str(row.get("id") or "")
        aliases = [str(a).lower() for a in (row.get("aliases") or []) if a]
        for a in sorted({*aliases, rid}, key=len, reverse=True):
            if not a:
                continue
            if " " in a:
                hit = a in low
            else:
                hit = bool(re.search(rf"\b{re.escape(a)}\b", low))
            if hit:
                scored.append((len(a), rid))
                break
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


def _pick_checkpoint_role(
    lanes: dict[str, Any],
    *,
    subject: str | None,
    grouping: str | None,
    content: str | None,
) -> str | None:
    roles = lanes.get("checkpoint_roles") or {}
    for rid, meta in roles.items():
        if not isinstance(meta, dict):
            continue
        pref = meta.get("prefer_when") or {}
        ok = True
        for axis, val in (
            ("subject", subject),
            ("grouping", grouping),
            ("content", content),
        ):
            allowed = pref.get(axis)
            if allowed and val and val not in allowed:
                ok = False
                break
            if allowed and not val and axis == "grouping" and "group" in allowed:
                # don't force C without grouping signal
                if rid.startswith("C"):
                    ok = False
                    break
        if ok and any(pref.get(a) for a in ("subject", "grouping", "content")):
            # Require at least one matching axis that was detected
            matched = False
            for axis, val in (
                ("subject", subject),
                ("grouping", grouping),
                ("content", content),
            ):
                allowed = pref.get(axis) or []
                if val and val in allowed:
                    matched = True
            if matched:
                return rid
    # Explicit group lean
    if grouping in ("pair", "group"):
        for rid in roles:
            if rid.startswith("C"):
                return rid
    if subject == "woman" and content in ("nsfw", "portrait", None):
        for rid in ("A_women_nsfw", "B_women_nsfw"):
            if rid in roles:
                return rid
    return None


def resolve_style_lane(catalog_data: dict[str, Any], ask: str) -> dict[str, Any]:
    """Parse a natural-language image ask into medium/mood/cast + recipe."""
    text = (ask or "").strip()
    lanes = _lanes(catalog_data)
    if not text:
        return {"ok": False, "error": "Empty ask", "howto": lanes.get("howto")}
    if not lanes:
        return {"ok": False, "error": "No style_lanes in catalog"}

    media_id = _match_bucket(text, lanes.get("media") or {})
    mood_id = _match_bucket(text, lanes.get("moods") or {})
    axes = lanes.get("cast_axes") or {}
    subject = _match_cast_axis(text, axes.get("subject") or [])
    grouping = _match_cast_axis(text, axes.get("grouping") or [])
    content = _match_cast_axis(text, axes.get("content") or [])

    # Solo hero vs monster/opponent stays solo
    if grouping == "group" and re.search(
        r"\b(?:monster|demon|beast|enemy|foe|opponent)\b", text.lower()
    ):
        if not re.search(r"\b(?:party|crowd|group of|multiple people|2girls|2boys)\b", text.lower()):
            grouping = "solo"

    media = (lanes.get("media") or {}).get(media_id or "", {}) if media_id else {}
    mood = (lanes.get("moods") or {}).get(mood_id or "", {}) if mood_id else {}

    # Merge rule from catalog howto
    mood_priority = mood_id in ("cyber", "gold_standard", "dark_fantasy") and bool(
        mood.get("default_style")
    )
    if mood_priority:
        style = mood.get("default_style")
        style_source = f"mood:{mood_id}"
    elif media.get("default_style"):
        style = media.get("default_style")
        style_source = f"media:{media_id}"
    else:
        style = None
        style_source = None

    role_id = _pick_checkpoint_role(
        lanes, subject=subject, grouping=grouping, content=content
    )
    role = (lanes.get("checkpoint_roles") or {}).get(role_id or "", {}) if role_id else {}
    if not style and role.get("styles"):
        style = role["styles"][0]
        style_source = f"checkpoint_role:{role_id}"

    look_id = mood.get("look_profile") or media.get("look_profile")
    look = _look_profiles(catalog_data).get(look_id or "", {}) if look_id else {}
    if look.get("style") and not mood_priority:
        # look profile can refine media style when mood didn't override
        style = look.get("style") or style
        if look.get("style"):
            style_source = f"look_profile:{look_id}"

    food_group = (
        mood.get("food_group_hint")
        or media.get("food_group")
        or look.get("food_group")
        or "anime"
    )

    prompt_parts = [
        p
        for p in (
            media.get("prompt_tail"),
            mood.get("prompt_tail"),
            look.get("prompt_tail"),
        )
        if p
    ]
    neg_parts = [
        p
        for p in (
            media.get("negative_extra"),
            mood.get("negative_extra"),
            look.get("negative_extra"),
        )
        if p
    ]

    loras: list[dict[str, Any]] = []
    for src in (look.get("loras") or [], mood.get("loras") or []):
        for row in src:
            if isinstance(row, dict) and row.get("file"):
                if row.get("optional"):
                    continue
                loras.append(
                    {"file": row["file"], "weight": float(row.get("weight", 0.7))}
                )

    # Dedupe loras by file
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in loras:
        f = row["file"]
        if f in seen:
            continue
        seen.add(f)
        deduped.append(row)

    return {
        "ok": True,
        "ask": text,
        "media": media_id,
        "mood": mood_id,
        "cast": {
            "subject": subject,
            "grouping": grouping,
            "content": content,
        },
        "checkpoint_role": role_id,
        "food_group": food_group,
        "style": style,
        "style_source": style_source,
        "look_profile": look_id,
        "prompt_tail": ", ".join(
            " ".join(str(p).split()) for p in prompt_parts if p
        ),
        "negative_extra": ", ".join(
            " ".join(str(p).split()) for p in neg_parts if p
        ),
        "loras": deduped,
        "usage": (
            "Pass style= and loras= to generate_image; append prompt_tail to the positive "
            "prompt and negative_extra to the negative. Resolve cast LoRAs separately "
            "with resolve_character_loras when a named character is present."
        ),
        "notes": {
            "media": media.get("notes"),
            "mood": mood.get("notes"),
            "role": role.get("notes"),
            "look": look.get("notes"),
        },
    }
