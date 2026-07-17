"""Compile LLM-written prompts into Comfy-safe compact form.

Diffusion models deform when the same action is described multiple ways in one
prompt. Agents also tend to use clinical euphemisms instead of terms the
checkpoint already understands for NSFW beats.
"""

from __future__ import annotations

import re
from typing import Any

# Shown in get_prompt_style / compile_image_prompt for Jan and Cursor agents.
COMFY_PROMPT_RULES: list[str] = [
    "One action, one phrase — never describe the same act twice (e.g. blowjob + oral sex + fellatio).",
    "Subject → pose/position → setting → lighting → one style line. No synonym stacks.",
    "Skip anatomy coaching in the positive (no 'perfect hands', 'correct limbs') — that belongs in negatives.",
    "For NSFW acts, name the act directly (blowjob, deepthroat, sex, cowgirl); add position tags only when needed.",
    "Call compile_image_prompt(prompt=...) to preview deduped text before generate_image.",
]

NSFW_PROMPT_RULES: list[str] = [
    "Checkpoints know common sex-act words — use them once, not clinical paraphrases.",
    "Good: '1girl, kneeling, blowjob, bedroom, soft light'.",
    "Bad: 'performing oral sex, fellatio, mouth on penis, intimate act'.",
    "Position tags (cowgirl, doggystyle, missionary) are fine alongside the act tag — not as replacements.",
    "After the act is named, describe who, pose, and scene — not another name for the same act.",
]

# First entry in each group is the canonical tag kept when duplicates appear.
_ACT_SYNONYM_GROUPS: list[list[str]] = [
    ["blowjob", "fellatio", "oral sex", "oral_sex", "oral", "sucking penis", "mouth on penis", "penis in mouth"],
    ["deepthroat", "deep throat", "deep_throat"],
    ["face fuck", "face_fuck", "facefuck", "throat fuck", "throat_fuck"],
    ["handjob", "hand job", "hand_job", "manual stimulation"],
    ["sex", "intercourse", "coitus", "vaginal sex", "vaginal_intercourse", "penetration", "penetrating"],
    ["anal", "anal sex", "anal_sex", "sodomy"],
    ["cunnilingus", "eating pussy", "pussy licking"],
    ["missionary", "missionary position", "missionary_position"],
    ["cowgirl", "cowgirl position", "cowgirl_position", "riding", "girl on top"],
    ["doggystyle", "doggy style", "doggy_style", "from behind"],
    ["fighting", "combat", "brawling", "in combat"],
    ["stabbing", "stab", "knife attack", "plunging knife", "knife stab"],
    ["running", "sprinting", "jogging"],
    ["walking", "strolling"],
]

# Whole-segment fluff to drop (case-insensitive substring match on normalized segment).
_STRIP_SEGMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in (
        r"^sexual activity$",
        r"^intimate (act|moment|scene)$",
        r"^genital contact$",
        r"^explicit (content|scene|act)$",
        r"^nsfw (act|scene|content)$",
        r"^performing (oral|sexual)",
        r"^engaged in (intercourse|sex)",
        r"^intimate (physical )?contact$",
    )
]

# Inline euphemism → canonical (applied per segment before grouping).
_EUPHEMISM_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\boral sex\b", re.I), "blowjob"),
    (re.compile(r"\bfellatio\b", re.I), "blowjob"),
    (re.compile(r"\bcoitus\b", re.I), "sex"),
    (re.compile(r"\bvaginal intercourse\b", re.I), "sex"),
    (re.compile(r"\bsexual intercourse\b", re.I), "sex"),
    (re.compile(r"\bdeep throat\b", re.I), "deepthroat"),
    (re.compile(r"\bface fuck\b", re.I), "face_fuck"),
    (re.compile(r"\bdoggy style\b", re.I), "doggystyle"),
    (re.compile(r"\bhand job\b", re.I), "handjob"),
]


def _normalize_key(text: str) -> str:
    return re.sub(r"[\s_\-]+", " ", text.lower().strip())


_GROUP_LOOKUP: list[tuple[str, frozenset[str]]] = []
for _group in _ACT_SYNONYM_GROUPS:
    canonical = _group[0]
    keys = frozenset(_normalize_key(s) for s in _group)
    _GROUP_LOOKUP.append((canonical, keys))


def _canonical_for_segment(segment: str) -> tuple[str | None, str | None]:
    """If segment belongs to a synonym group, return (canonical, matched_key)."""
    norm = _normalize_key(segment)
    if not norm:
        return None, None
    for canonical, keys in _GROUP_LOOKUP:
        if norm in keys:
            return canonical, norm
        for key in keys:
            if len(key) >= 4 and re.search(rf"\b{re.escape(key)}\b", norm):
                return canonical, key
    return None, None


def _apply_euphemisms(segment: str) -> str:
    out = segment
    for pattern, replacement in _EUPHEMISM_REPLACEMENTS:
        out = pattern.sub(replacement, out)
    return out.strip()


def _should_strip_segment(segment: str) -> bool:
    norm = _normalize_key(segment)
    if not norm:
        return True
    return any(p.search(norm) for p in _STRIP_SEGMENT_PATTERNS)


def _split_segments(prompt: str) -> list[str]:
    parts = [p.strip() for p in prompt.split(",")]
    return [p for p in parts if p]


def compile_image_prompt(
    prompt: str,
    *,
    content_rating: str = "open",
    architecture: str = "",
) -> tuple[str, dict[str, Any]]:
    """Dedupe redundant action phrases and normalize NSFW euphemisms.

    Returns (compiled_prompt, report). Skips heavy NSFW normalization when
    content_rating is sfw/safe.
    """
    rating = (content_rating or "open").lower().strip()
    report: dict[str, Any] = {
        "original": prompt,
        "removed": [],
        "replaced": [],
        "deduped_acts": [],
        "architecture": architecture or None,
    }
    if not prompt or not prompt.strip():
        return prompt, report

    segments = _split_segments(prompt)
    if rating in {"sfw", "safe"}:
        # Still dedupe obvious action stacks; skip NSFW euphemism pass.
        working = segments
    else:
        working = []
        for seg in segments:
            if _should_strip_segment(seg):
                report["removed"].append(seg)
                continue
            new_seg = _apply_euphemisms(seg)
            if new_seg != seg:
                report["replaced"].append({"from": seg, "to": new_seg})
            working.append(new_seg)

    seen_groups: set[str] = set()
    seen_exact: set[str] = set()
    out: list[str] = []

    for seg in working:
        norm = _normalize_key(seg)
        if norm in seen_exact:
            report["removed"].append(seg)
            continue

        canonical, matched = _canonical_for_segment(seg)
        if canonical:
            if canonical in seen_groups:
                report["deduped_acts"].append({"dropped": seg, "kept": canonical})
                continue
            seen_groups.add(canonical)
            seen_exact.add(_normalize_key(canonical))
            if seg != canonical:
                report["replaced"].append({"from": seg, "to": canonical})
            out.append(canonical)
            continue

        seen_exact.add(norm)
        out.append(seg)

    compiled = ", ".join(out)
    report["compiled"] = compiled
    report["rules"] = COMFY_PROMPT_RULES + (NSFW_PROMPT_RULES if rating not in {"sfw", "safe"} else [])
    return compiled, report
