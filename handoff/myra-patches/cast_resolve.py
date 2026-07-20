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
    # Collapse hyphens/underscores/spaces so He-jin == heejin-ish matching via aliases
    t = (s or "").lower().replace("ü", "u").replace("Ü", "u")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def characters_for_show(show_id: str, *, gender: str | None = None) -> list[str]:
    """Ordered character ids for a show (for cast_batch)."""
    chars, shows = _load()
    sid = (show_id or "").strip().lower().replace(" ", "_")
    show = None
    for s in shows:
        if str(s.get("id", "")).lower() == sid:
            show = s
            break
        aliases = [_norm(a) for a in (s.get("aliases") or [])]
        if _norm(sid) in aliases or _norm(s.get("id", "")) == _norm(sid):
            show = s
            break
    if not show:
        show = match_show(show_id or "", shows)
    if not show:
        return []
    out: list[str] = []
    for cid in show.get("characters") or []:
        ch = _char_by_id(chars, str(cid))
        if not ch:
            continue
        if gender and ch.get("gender") and ch.get("gender") != gender:
            continue
        out.append(str(ch["id"]))
    return out


def _char_by_id(chars: list[dict], cid: str) -> dict | None:
    for c in chars:
        if c.get("id") == cid:
            return c
    return None


def match_character(text: str, chars: list[dict] | None = None) -> dict | None:
    """Match a known cast name with word-boundary safety.

    Avoids fatal false hits like alias ``cha`` matching ``character``/``change``,
    or ``gina`` matching inside ``original``.
    """
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
            # Require at least 4 chars, or a multi-token name (e.g. "han semi")
            tokens = nn.split()
            if len(nn.replace(" ", "")) < 4 and len(tokens) < 2:
                continue
            # "Flamme from frieren" — do not pick the show title as the character
            if re.search(rf"\bfrom\s+{re.escape(nn)}\b", low):
                continue
            hit = False
            if nn == low:
                hit = True
            elif f" {nn} " in f" {low} ":
                hit = True
            elif len(tokens) >= 2 and low.endswith(f" {nn}"):
                # "... named Cha Hae In"
                hit = True
            elif len(tokens) >= 2 and low.startswith(f"{nn} "):
                hit = True
            else:
                # Contiguous compact match only for longer ids (nb_frieren, parkheejin)
                nc = nn.replace(" ", "")
                compact = low.replace(" ", "")
                if len(nc) >= 7 and nc in compact:
                    hit = True
            if hit and len(nn) > best_len:
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
    # Bare "from" is too broad ("recreate from studio_agent_00031") — require cast phrasing
    from_show_phrasing = bool(
        re.search(
            r"\b(?:character|someone|somebody|anybody|anyone|girl|boy|woman|man)\s+from\b",
            low,
        )
        or re.search(r"\bfrom\s+(?:the\s+)?(?:show|series|anime)\b", low)
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


def directive_for_nari(
    request: str,
    resolved: dict[str, Any],
    *,
    locks: list[str] | None = None,
) -> str:
    """Lock cast tokens so Nari cannot drop the character."""
    ch = resolved.get("character")
    locks = locks or []
    if not ch:
        return request
    helpers = (ch.get("caption_helpers") or "").strip()
    parts = [
        f"Character={ch['display_name']}",
        f"trigger={ch.get('trigger')}",
        f"Keep trigger token `{ch.get('trigger')}` in the positive prompt.",
        "Do not invent a different character. Do not ask questions.",
    ]
    if "pose" in locks:
        parts.append("LOCK pose from the stage-one reference — do not change pose.")
    if "scene" in locks:
        parts.append("LOCK scene/setting from the stage-one reference — do not change background.")
    if helpers:
        parts.append(f"look_tags={helpers}")
    parts.append(
        "waijfu_alpha: write a short vulgar scene description PLUS sex-act tags "
        "(e.g. on her hands and knees, looking back over her shoulder, a man behind "
        "her holding her hips while he fucks her in her ass, doggystyle, anal sex). "
        "Hole swap: anal sex/anal penetration vs vaginal sex/vaginal penetration. "
        "Framing: side view / man's POV — never say camera."
    )
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
