"""Myra local cast resolve — character/show lists before Nari expands the scene.

Policy:
  - anime character X → character_list
  - character from Show → show_index
  - show named, character not → random/any (+ gender) or ask
  - unsure → ask; do not invent a cast
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

_CAST_DIR = Path(__file__).resolve().parent / "cast"
_CHAR_PATH = _CAST_DIR / "character_list.json"
_SHOW_PATH = _CAST_DIR / "show_index.json"

_FROM_SHOW_RE = re.compile(
    r"\b(?:character|someone|anybody|anyone|girl|boy|woman|man)\s+from\b"
    r"|\bfrom\s+(?:the\s+)?(?P<show>.+?)(?:\s+(?:show|series|anime))?\s*$",
    re.I,
)
_RANDOM_RE = re.compile(r"\b(?:random|any|someone|somebody|anybody|anyone)\b", re.I)
_FEMALE_RE = re.compile(r"\b(?:female|woman|girl|1girl)\b", re.I)
_MALE_RE = re.compile(r"\b(?:male|man|boy|1boy)\b", re.I)
_ANIME_CHAR_RE = re.compile(
    r"\b(?:anime\s+)?character(?:\s+named)?\s+(?P<name>[A-Za-z][A-Za-z0-9' \-]{1,40})",
    re.I,
)


def _load() -> tuple[list[dict], list[dict]]:
    chars: list[dict] = []
    shows: list[dict] = []
    if _CHAR_PATH.is_file():
        data = json.loads(_CHAR_PATH.read_text(encoding="utf-8"))
        chars = list(data.get("characters") or [])
    if _SHOW_PATH.is_file():
        data = json.loads(_SHOW_PATH.read_text(encoding="utf-8"))
        shows = list(data.get("shows") or [])
    return chars, shows


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _char_by_id(chars: list[dict], cid: str) -> dict | None:
    for c in chars:
        if c.get("id") == cid:
            return c
    return None


def match_character(text: str, chars: list[dict] | None = None) -> dict | None:
    if chars is None:
        chars, _ = _load()
    low = _norm(text)
    if not low:
        return None
    # Prefer longer alias hits
    best: dict | None = None
    best_len = 0
    for c in chars:
        names = [c.get("id", ""), c.get("display_name", "")] + list(c.get("aliases") or [])
        for n in names:
            nn = _norm(str(n))
            if not nn:
                continue
            if nn == low or f" {nn} " in f" {low} " or low.endswith(nn) or low.startswith(nn):
                if len(nn) > best_len:
                    best = c
                    best_len = len(nn)
    return best


def match_show(text: str, shows: list[dict] | None = None) -> dict | None:
    if shows is None:
        _, shows = _load()
    low = _norm(text)
    best: dict | None = None
    best_len = 0
    for s in shows:
        for n in [s.get("id", "")] + list(s.get("aliases") or []):
            nn = _norm(str(n))
            if nn and (nn in low or low in nn):
                if len(nn) > best_len:
                    best = s
                    best_len = len(nn)
    return best


def resolve_cast(request: str) -> dict[str, Any]:
    """Return ok + character row, or need_clarify / error."""
    chars, shows = _load()
    if not chars:
        return {
            "ok": False,
            "error": "Cast lists missing. Run export_cast_lists.py on Windows.",
            "need_clarify": False,
        }

    text = (request or "").strip()
    low = text.lower()
    wants_random = bool(_RANDOM_RE.search(low))
    from_show_phrasing = bool(
        re.search(r"\bfrom\b", low)
        or re.search(r"\b(?:someone|somebody|anybody|anyone)\s+from\b", low)
    )
    gender = None
    if _FEMALE_RE.search(low) and not _MALE_RE.search(low):
        gender = "female"
    elif _MALE_RE.search(low) and not _FEMALE_RE.search(low):
        gender = "male"

    show = match_show(text, shows)

    # Explicit "from <show>" / random-from-show takes precedence over matching
    # the show title as a character id (e.g. "someone from frieren").
    if show and (from_show_phrasing or wants_random):
        pool_ids = list(show.get("characters") or [])
        pool = [c for cid in pool_ids if (c := _char_by_id(chars, cid))]
        if gender:
            filtered = [c for c in pool if c.get("gender") == gender]
            if filtered:
                pool = filtered
        if wants_random and pool:
            pick = random.choice(pool)
            return {"ok": True, "character": pick, "show": show, "mode": "random_from_show"}
        if len(pool) == 1:
            return {"ok": True, "character": pool[0], "show": show, "mode": "solo_from_show"}
        names = [c["display_name"] for c in pool]
        return {
            "ok": False,
            "need_clarify": True,
            "show": show,
            "candidates": names,
            "ask": (
                f"Which character from {show['id'].replace('_', ' ')}? "
                f"I know: {', '.join(names)}."
            ),
        }

    # Named character (avoid matching inside "no character" / "without character")
    hit = None
    if not re.search(r"\b(?:no|without|any)\s+character\b", low):
        hit = match_character(text, chars)
        if not hit:
            m = _ANIME_CHAR_RE.search(text)
            if m:
                name = m.group("name").strip()
                # Ignore captures that are really "from <show>…"
                if not name.lower().startswith("from "):
                    hit = match_character(name, chars)

    if hit:
        return {"ok": True, "character": hit, "show": show, "mode": "named"}

    # User asked for a character but we missed the name
    asks_for_cast = bool(
        re.search(r"\banime\s+character\b", low)
        or re.search(r"\bcharacter\s+named\b", low)
        or re.search(r"\bmake\s+(?:me\s+)?(?:an?\s+)?(?:image|picture)\s+of\s+(?:the\s+)?(?:anime\s+)?character\b", low)
    )
    if asks_for_cast:
        return {
            "ok": False,
            "need_clarify": True,
            "ask": (
                "I didn't match a known character LoRA. "
                "Name the character, or say a show plus random female or male."
            ),
            "known": [c["display_name"] for c in chars[:24]],
        }

    return {"ok": True, "character": None, "mode": "scene_only"}


def directive_for_nari(request: str, resolved: dict[str, Any]) -> str:
    """Lock cast tokens so Nari cannot drop the character."""
    ch = resolved.get("character")
    if not ch:
        return request
    helpers = (ch.get("caption_helpers") or "").strip()
    parts = [
        f"Character={ch['display_name']}",
        f"trigger={ch.get('trigger')}",
        f"Keep trigger token `{ch.get('trigger')}` in the positive prompt.",
    ]
    if helpers:
        parts.append(f"look_tags={helpers}")
    parts.append(f"Scene request: {request}")
    return " ".join(parts)


def loras_for_comfy(resolved: dict[str, Any]) -> list[dict[str, Any]]:
    ch = resolved.get("character")
    if not ch or not ch.get("file"):
        return []
    out = [{"file": ch["file"], "weight": float(ch.get("weight", 0.8))}]
    for pair in ch.get("pair_with") or []:
        if isinstance(pair, dict) and pair.get("file"):
            out.append(
                {"file": pair["file"], "weight": float(pair.get("weight", 0.8))}
            )
    return out
