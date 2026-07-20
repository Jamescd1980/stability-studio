"""Deterministic image brief — Pi state machine, no myra-gofor.

Myra asks short slot questions; Nari only expands the final locked packet.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from . import cast_resolve
from . import generate as gen_mod

log = logging.getLogger("studio_edge.image_brief")

_STYLE_RE = re.compile(
    r"\b(?:anime|waijfu|illustrious|realistic|photoreal|fantasy|cyberpunk)\b",
    re.I,
)
_SCENE_HINT_RE = re.compile(
    r"\b(?:beach|night|day|forest|room|bedroom|city|street|rain|snow|"
    r"standing|sitting|lying|pose|naked|nude|sex|kiss|outdoors|indoors)\b",
    re.I,
)
_RECREATE_RE = re.compile(
    r"\b(?:recreate|try\s+again|same\s+image|redo|remake)\b",
    re.I,
)
_ADJUST_RE = re.compile(
    r"\b(?:but\s+|except\s+|instead\s+|make\s+her|make\s+him|change\s+|"
    r"adjust|tweak|edit\s+this)\b",
    re.I,
)
_CAST_SWAP_RE = re.compile(
    r"\b(?:change\s+(?:the\s+)?character|swap\s+(?:the\s+)?character|"
    r"swap\s+to\s+\w+|"
    r"(?:keep|same)\s+(?:the\s+)?(?:pose|scene|layout).{0,40}"
    r"(?:change|swap).{0,20}character|"
    r"but\s+(?:as|with)\s+[A-Z])",
    re.I,
)
_SAME_AS_SOURCE_RE = re.compile(
    r"\b(?:same\s+(?:as\s+)?(?:the\s+)?(?:original|source|that|this)"
    r"(?:\s+(?:image|picture|one))?|"
    r"same\s+(?:exact\s+)?(?:scene|layout|pose)(?:\s+as\s+(?:the\s+)?"
    r"(?:original|source|that|this)(?:\s+(?:image|picture))?)?|"
    r"nothing\s+changes?|exact(?:ly)?\s+(?:the\s+)?same|"
    r"original\s+(?:fucking\s+)?(?:image|picture))\b",
    re.I,
)
_BATCH_RE = re.compile(
    r"\b(?:one\s+of\s+each|whole\s+cast|everyone\s+from|all\s+(?:the\s+)?"
    r"(?:cast|characters|girls|boys)\s+from|cast\s+of)\b",
    re.I,
)
_STUDIO_EDGE_RE = re.compile(
    r"\bstudio\s*(?:edge|agent)\s*[-,\s]*(?P<digits>\d{1,5})\b"
    r"|\b(?:image|file)\s*(?:number\s*)?(?P<n2>\d{1,5})\b",
    re.I,
)
_STUDIO_EDGE_SPOKEN_RE = re.compile(
    r"\bstudio\s*(?:edge|agent)\b[\s\S]{0,64}?\b"
    r"(?:zero|oh)\s+(?P<w>one|two|three|four|five|six|seven|eight|nine|ten"
    r"|\d{1,2})\b",
    re.I,
)
_SPOKEN_NUM = {
    "zero": 0, "oh": 0,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
}
# Longest-first so thirty/thirteen beat three/ten; no bare "o" (eats "one")
_SPOKEN_WORD = (
    r"(?:fifty|forty|thirty|twenty|nineteen|eighteen|seventeen|sixteen|"
    r"fifteen|fourteen|thirteen|twelve|eleven|ten|"
    r"nine|eight|seven|six|five|four|three|two|one|zero|oh)"
)
# "zero zero zero three one" / "thirty one"
_SPOKEN_ID_SEQ_RE = re.compile(
    rf"\b((?:{_SPOKEN_WORD}(?:[\s\-]+|$)){{2,8}})",
    re.I,
)
_WRONG_SOURCE_RE = re.compile(
    r"\b(?:wrong\s+(?:image|one|picture|file|number)|"
    r"not\s+(?:that|this|the)\s+(?:image|one|picture)|"
    r"different\s+image|other\s+image|"
    r"you(?:'re|\s+are)\s+using\s+the\s+wrong)\b",
    re.I,
)
_BARE_NO_RE = re.compile(r"^\s*no+[!.]*\s*$", re.I)
# "Fuck you" / "Fuck you Myra" / "Fuck you, Nari" (any short name)
_HARD_ABORT_RE = re.compile(
    r"\b(?:fuck\s+you(?:\s*,?\s*[A-Za-z][A-Za-z']{0,20})?|"
    r"fuck\s+this|fuck\s+off|screw\s+(?:this|you)|"
    r"shut\s+(?:the\s+fuck\s+)?up|kill\s+it|abort|"
    r"god\s*damn\s+it|stop\s+everything|stop\s+all)\b",
    re.I,
)
_ABORT_REPLY = "Sorry... I will stop and reset process."
_CANCEL_RE = re.compile(
    r"^\s*(?:cancel|never\s*mind|stop|forget\s+it)\s*[.!?]?\s*$",
    re.I,
)
# Set when user hard-aborts; main follow-up loop should exit immediately.
_ABORT_LATCH = False
_SKIP_RE = re.compile(
    r"^\s*(?:skip|none|no\s+style|default|whatever|you\s+pick)\s*[.!?]?\s*$",
    re.I,
)
_CONFIRM_RE = re.compile(
    r"^\s*(?:yes|yeah|yep|confirm|do\s+it|go\s+ahead|make\s+it|looks?\s+good)\s*[.!?]?\s*$",
    re.I,
)


_GOLD_RE = re.compile(
    r"\b(?:gold\s+standard|detail\s+hero|absurdres\s+quality|hero\s+quality)\b",
    re.I,
)
_CLOTHING_RE = re.compile(
    r"\b(?:naked|nude|nsfw|bikini|dress|robe|skirt|shirt|outfit|clothes?|"
    r"red|black|white|blue|green|pink|purple|gold)\b"
    r"|make\s+her\s+naked|change\s+(?:the\s+)?(?:dress|outfit|clothes?|color)",
    re.I,
)


@dataclass
class Brief:
    mode: str = "create"  # create|recreate|adjust|cast_swap|cast_batch
    style: str = ""
    character: str = ""
    scene: str = ""
    extras: str = ""
    quality: str = ""  # gold_standard | ""
    source_selector: str = ""  # last_displayed|newest|studio_agent_N (empty = ask)
    source_path: str = ""
    source_explicit: bool = False
    locks: list[str] = field(default_factory=list)
    batch_show: str = ""
    cast_ids: list[str] = field(default_factory=list)
    slot: str = ""  # next question key
    active: bool = False

    def to_packet(self) -> str:
        parts: list[str] = []
        if self.character:
            parts.append(f"Character={self.character}")
        if self.style:
            parts.append(f"Style={self.style}")
        if self.scene:
            parts.append(f"Scene={self.scene}")
        if self.extras:
            parts.append(f"Extras={self.extras}")
        if self.quality:
            parts.append(f"Quality={self.quality}")
        if self.locks:
            parts.append(f"Locks={','.join(self.locks)}")
        return "; ".join(parts) if parts else self.scene or self.character


_ACTIVE: Brief | None = None


def active() -> Brief | None:
    return _ACTIVE if _ACTIVE and _ACTIVE.active else None


def clear() -> None:
    global _ACTIVE
    _ACTIVE = None


def is_active() -> bool:
    return active() is not None


def consume_abort() -> bool:
    """True once after a hard abort (fuck you / stop everything)."""
    global _ABORT_LATCH
    if not _ABORT_LATCH:
        return False
    _ABORT_LATCH = False
    return True


def hard_abort(cfg: dict | None = None) -> str:
    """Cancel brief, interrupt Comfy, stop follow-up."""
    global _ABORT_LATCH
    _ABORT_LATCH = True
    clear()
    try:
        gen_mod.abort_jobs(cfg or {})
    except Exception as exc:  # noqa: BLE001
        log.warning("abort_jobs failed: %s", exc)
    try:
        from . import agent_pulse

        agent_pulse.set_status("myra", "listening", detail="Aborted")
        agent_pulse.set_status("nari", "ready", detail="")
        agent_pulse.set_status("orla", "ready", detail="")
    except Exception:
        pass
    return _ABORT_REPLY


def _set(brief: Brief) -> Brief:
    global _ACTIVE
    brief.active = True
    _ACTIVE = brief
    return brief


def detect_mode(text: str) -> str:
    low = text or ""
    if _BATCH_RE.search(low):
        return "cast_batch"
    if _CAST_SWAP_RE.search(low):
        return "cast_swap"
    # "re-create" / Hailo "he recreate"
    if re.search(r"\bre[\s\-]?create\b", low, re.I) or _RECREATE_RE.search(low):
        if _ADJUST_RE.search(low) and not _SAME_AS_SOURCE_RE.search(low):
            return "adjust"
        # Cast swap phrasing inside recreate → still recreate with locks
        if re.search(r"\bchange\s+(?:the\s+)?character\b", low, re.I):
            return "cast_swap"
        return "recreate"
    if _ADJUST_RE.search(low) and re.search(r"\b(?:image|picture|this|that)\b", low, re.I):
        return "adjust"
    return "create"


def _apply_same_as_source(brief: Brief, text: str) -> bool:
    """User wants pose/scene from the source image — not a new freeform scene."""
    if not _SAME_AS_SOURCE_RE.search(text or ""):
        return False
    brief.scene = "same as source image"
    for lock in ("pose", "scene"):
        if lock not in brief.locks:
            brief.locks.append(lock)
    return True


def _edge_id(n: int) -> str | None:
    """Canonical gallery id — always studio_agent_NNNNN."""
    if n is None or int(n) <= 0:
        return None
    return f"studio_agent_{int(n):05d}"


def _parse_spoken_id_sequence(text: str) -> str | None:
    """Parse 'zero zero zero three one' or 'thirty one' → studio_agent_NNNNN."""
    m = _SPOKEN_ID_SEQ_RE.search(text or "")
    if not m:
        return None
    words = re.findall(_SPOKEN_WORD, m.group(1), flags=re.I)
    if len(words) < 2:
        return None
    # Digit-by-digit (zero zero zero three one) vs compound (thirty one)
    vals = [_SPOKEN_NUM.get(w.lower(), -1) for w in words]
    if any(v < 0 for v in vals):
        return None
    if all(v <= 9 for v in vals):
        # leading zeros ok: 0,0,0,3,1 → 31
        n = 0
        for v in vals:
            n = n * 10 + v
        return _edge_id(n)
    # compound: thirty + one
    n = 0
    i = 0
    while i < len(vals):
        v = vals[i]
        if v >= 20 and i + 1 < len(vals) and vals[i + 1] <= 9:
            n = n * 100 + v + vals[i + 1]
            i += 2
        else:
            n = n * 100 + v if n else v
            i += 1
    return _edge_id(n)


def _parse_studio_edge(text: str) -> str | None:
    raw = text or ""
    # Full spoken digit runs first (zero zero zero three one / thirty one)
    seq = _parse_spoken_id_sequence(raw)
    if seq:
        return seq
    # Prefer spoken "zero three" over a mangled "0-0" stub
    m2 = _STUDIO_EDGE_SPOKEN_RE.search(raw)
    if m2:
        w = (m2.group("w") or "").lower()
        n = int(w) if w.isdigit() else _SPOKEN_NUM.get(w)
        if n is not None and int(n) > 0:
            return _edge_id(int(n))
    m = _STUDIO_EDGE_RE.search(raw)
    if m:
        digits = m.group("digits") or m.group("n2")
        if digits:
            # Keep value; reject all-zero STT stubs like "0000"
            if re.fullmatch(r"0+", digits):
                return None
            return _edge_id(int(digits))
    # Bare number while correcting source (31 / 00031)
    m3 = re.search(r"\b(0*[1-9]\d{0,4})\b", raw)
    if m3 and re.search(r"\b(?:studio|edge|agent|image|number|file)\b", raw, re.I):
        return _edge_id(int(m3.group(1)))
    return None


def _parse_source_answer(text: str) -> str | None:
    """Source-slot parser: studio agent id, newest, or last."""
    asked = gen_mod.correct_stt_names(text or "")
    if re.search(r"\bnewest\b", asked, re.I):
        return "newest"
    if re.search(r"\b(?:last|latest)\b", asked, re.I):
        return "last_displayed"
    se = _parse_studio_edge(asked)
    if se:
        return se
    # Bare digits / spoken id alone
    m = re.search(r"\b(0*[1-9]\d{0,4})\b", asked)
    if m:
        return _edge_id(int(m.group(1)))
    return _parse_spoken_id_sequence(asked)


def _source_ok(brief: Brief) -> bool:
    sel = (brief.source_selector or "").strip()
    if not sel:
        return False
    if sel.startswith("studio_agent_") or sel.startswith("studio_edge_"):
        try:
            return int(sel.rsplit("_", 1)[-1]) > 0
        except ValueError:
            return False
    return bool(brief.source_explicit and sel in {"newest", "last_displayed"})


def _extract_show(text: str) -> str:
    show = cast_resolve.match_show(text)
    return str(show["id"]) if show else ""


def _seed_from_utterance(brief: Brief, text: str) -> None:
    """Pull any slots already present so we can skip questions."""
    asked = gen_mod.correct_stt_names(text or "")
    m = _STYLE_RE.search(asked)
    if m and not brief.style:
        brief.style = m.group(0).lower()
    hit = cast_resolve.match_character(asked)
    if hit and not brief.character:
        brief.character = str(hit.get("display_name") or hit.get("id") or "")
    # Free "character named X" capture
    if not brief.character:
        m2 = re.search(
            r"\b(?:character\s+named|named)\s+([A-Za-z][A-Za-z0-9' \-]{1,40})",
            asked,
            re.I,
        )
        if m2:
            brief.character = m2.group(1).strip()
    if _apply_same_as_source(brief, asked):
        pass
    elif _SCENE_HINT_RE.search(asked) and not brief.scene:
        # Keep a cleaned scene phrase — drop ask-nari fluff
        scene = asked
        scene = re.sub(
            r"(?i)\b(?:ask|have|tell|get)\s+(?:nari|jan|nauri|naree)\b.*?\b(?:to|)\s*",
            "",
            scene,
        )
        scene = re.sub(
            r"(?i)\b(?:make|create|generate|draw)\s+(?:me\s+)?(?:an?\s+)?(?:image|picture)\s+(?:of\s+)?",
            "",
            scene,
        )
        brief.scene = scene.strip(" ,.:;-")[:240]
    se = _parse_studio_edge(asked)
    if se:
        brief.source_selector = se
        brief.source_explicit = True
    if re.search(r"\bnewest\b", asked, re.I):
        brief.source_selector = "newest"
        brief.source_explicit = True
    elif re.search(r"\b(?:last|latest)\s+(?:image|one|picture|displayed)\b", asked, re.I) or (
        re.search(r"\blast\b", asked, re.I) and re.search(r"\b(?:image|picture|displayed)\b", asked, re.I)
    ):
        brief.source_selector = "last_displayed"
        brief.source_explicit = True
    if re.search(r"\b(?:keep|same)\s+(?:the\s+)?pose\b", asked, re.I):
        if "pose" not in brief.locks:
            brief.locks.append("pose")
    if re.search(r"\b(?:keep|same)\s+(?:the\s+)?scene\b", asked, re.I):
        if "scene" not in brief.locks:
            brief.locks.append("scene")
    show = _extract_show(asked)
    if show and brief.mode == "cast_batch":
        brief.batch_show = show
    if _GOLD_RE.search(asked):
        brief.quality = "gold_standard"
    if _CLOTHING_RE.search(asked):
        # Keep clothing / color deltas in extras (don't wipe scene)
        bit = asked.strip()[:160]
        if bit and bit.lower() not in (brief.extras or "").lower():
            brief.extras = f"{brief.extras}; {bit}".strip("; ") if brief.extras else bit


def _next_slot(brief: Brief) -> str:
    if brief.mode in {"recreate", "adjust", "cast_swap", "cast_batch"}:
        if not _source_ok(brief):
            return "source"
    if brief.mode in {"recreate", "adjust"}:
        if not brief.scene and brief.mode == "adjust":
            return "adjust"
        return "confirm"
    if brief.mode == "cast_swap":
        if not brief.character:
            return "character"
        return "confirm"
    if brief.mode == "cast_batch":
        if not brief.batch_show:
            return "batch_show"
        return "confirm"
    # create — skip style when cast+scene already present (barge-in)
    if not brief.style and not (brief.character and brief.scene):
        return "style"
    if not brief.character:
        return "character"
    if not brief.scene:
        return "scene"
    if not brief.style:
        brief.style = "anime"
    return "confirm"


def _question(slot: str, brief: Brief) -> str:
    if slot == "style":
        return "What style? Anime, waijfu, or something else — or say skip."
    if slot == "character":
        return "Which character, or describe them? You can name a show and say random female."
    if slot == "scene":
        return "What's the scene or layout? Beach at night, standing, and so on."
    if slot == "adjust":
        return "What should I change from that image?"
    if slot == "source":
        return (
            "Which studio agent image? Say the full number — "
            "for example thirty-one, or zero zero zero three one."
        )
    if slot == "batch_show":
        return "Which show's cast should I batch? For example, Frieren."
    if slot == "confirm":
        if brief.mode == "cast_batch":
            ids = brief.cast_ids or cast_resolve.characters_for_show(brief.batch_show)
            n = len(ids)
            return (
                f"That's {n} stills from {brief.batch_show or 'that show'} "
                f"from {brief.source_selector or 'the base'}. Say yes to queue them."
            )
        if brief.mode == "cast_swap":
            locks = " and ".join(brief.locks) if brief.locks else "pose and scene"
            return (
                f"From {brief.source_selector}: keep {locks}, "
                f"change character to {brief.character}. Say yes to run it."
            )
        if brief.mode in {"recreate", "adjust"}:
            return (
                f"Recreate from {brief.source_selector}"
                + (f" with: {brief.scene}" if brief.scene else "")
                + ". Say yes to run it, or say wrong image to pick another."
            )
        pkt = brief.to_packet()
        return f"I'll make: {pkt}. Say yes to generate, or tell me what to change."
    return "What next?"


def start(text: str, *, mode: str | None = None) -> str:
    """Begin a brief from a create/recreate utterance."""
    brief = Brief(mode=mode or detect_mode(text))
    if brief.mode in {"cast_swap"} and not brief.locks:
        brief.locks = ["pose", "scene"]
    if brief.mode == "cast_batch" and not brief.locks:
        brief.locks = ["pose", "scene"]
    _seed_from_utterance(brief, text)
    if brief.mode == "cast_batch" and brief.batch_show:
        brief.cast_ids = cast_resolve.characters_for_show(brief.batch_show)
    brief.slot = _next_slot(brief)
    _set(brief)
    log.info("Brief start mode=%s slot=%s packet=%r", brief.mode, brief.slot, brief.to_packet())
    if brief.slot == "confirm":
        return _question("confirm", brief)
    # Skip empty style if user already gave character+scene
    return _question(brief.slot, brief)


def feed(text: str, brain, cfg: dict) -> str:
    """Continue or finish an active brief. Returns speakable reply."""
    brief = active()
    if not brief:
        return start(text)

    raw = (text or "").strip()
    if _HARD_ABORT_RE.search(raw):
        return hard_abort(cfg)
    if _CANCEL_RE.match(raw):
        clear()
        return "Okay, cancelled the image brief."

    slot = brief.slot or _next_slot(brief)

    # "Wrong image" anytime during recreate/swap → re-ask source
    if _WRONG_SOURCE_RE.search(raw) and brief.mode in {
        "recreate", "adjust", "cast_swap", "cast_batch",
    }:
        brief.source_selector = ""
        brief.source_explicit = False
        brief.slot = "source"
        _set(brief)
        # If they also spoke a new number in the same utterance, use it
        sel = _parse_source_answer(raw)
        if sel:
            brief.source_selector = sel
            brief.source_explicit = True
            brief.slot = _next_slot(brief)
            _set(brief)
            return _question(brief.slot, brief)
        return _question("source", brief)

    if slot == "style":
        if _SKIP_RE.match(raw):
            brief.style = "anime"
        else:
            m = _STYLE_RE.search(raw)
            brief.style = (m.group(0).lower() if m else raw.strip())[:40]
    elif slot == "character":
        asked = gen_mod.correct_stt_names(raw)
        # "change character to X" while already in character slot
        m_ch = re.search(
            r"\b(?:change\s+(?:the\s+)?character\s+to|character\s+(?:is|to|named))\s+(.+)",
            asked,
            re.I,
        )
        name_bit = (m_ch.group(1) if m_ch else asked).strip()
        # Prefer the name token before a description clause
        name_bit = re.split(
            r"\b(?:she|he|with|who|has|have|and)\b", name_bit, maxsplit=1, flags=re.I
        )[0].strip(" ,.:;-")
        hit = cast_resolve.match_character(name_bit) or cast_resolve.match_character(asked)
        if hit:
            brief.character = str(hit.get("display_name") or hit.get("id"))
        else:
            resolved = cast_resolve.resolve_cast(
                f"anime character named {name_bit or asked}"
            )
            if resolved.get("character"):
                brief.character = str(
                    resolved["character"].get("display_name")
                    or resolved["character"].get("id")
                )
            elif resolved.get("need_clarify"):
                return str(resolved.get("ask") or "Which character?")
            else:
                # Do NOT accept STT garbage ("Will you see actual character?") as a name
                looks_like_question = "?" in asked or re.search(
                    r"\b(?:will|what|which|who|did|can|see|actual)\b", asked, re.I
                )
                # "original" alone is a scene lock answer, not an OC
                if _SAME_AS_SOURCE_RE.search(asked) or re.search(
                    r"\boriginal\b", asked, re.I
                ):
                    return (
                        "I still need the character name. "
                        "Say Frieren, Fern, Ubel, or Park Heejin."
                    )
                oc_ok = (
                    len(asked) >= 24
                    and not looks_like_question
                    and re.search(
                        r"\b(?:girl|boy|woman|man|hair|eyes|oc)\b",
                        asked,
                        re.I,
                    )
                )
                if not oc_ok:
                    return (
                        "I didn't catch a cast name. "
                        "Say the character clearly — for example Ubel, Fern, or Frieren."
                    )
                brief.character = (name_bit or asked)[:80]
    elif slot == "scene":
        asked = gen_mod.correct_stt_names(raw)
        if not _apply_same_as_source(brief, asked):
            brief.scene = asked[:240]
    elif slot == "adjust":
        brief.scene = gen_mod.correct_stt_names(raw)[:240]
        brief.mode = "adjust"
    elif slot == "source":
        sel = _parse_source_answer(raw)
        if not sel:
            return (
                "I still need the studio agent number. "
                "Say thirty-one, or zero zero zero three one — not just no."
            )
        brief.source_selector = sel
        brief.source_explicit = True
        log.info("Brief source set to %s", sel)
    elif slot == "batch_show":
        brief.batch_show = _extract_show(raw) or raw.strip().lower().replace(" ", "_")
        brief.cast_ids = cast_resolve.characters_for_show(brief.batch_show)
        if not brief.cast_ids:
            return (
                f"I don't have a cast list for {brief.batch_show}. "
                "Try Frieren or Solo Leveling."
            )
    elif slot == "confirm":
        if not _CONFIRM_RE.match(raw):
            asked = gen_mod.correct_stt_names(raw)
            # Bare "no" at confirm → ask which image, don't loop the same prompt
            if _BARE_NO_RE.match(raw) or _WRONG_SOURCE_RE.search(asked):
                brief.source_selector = ""
                brief.source_explicit = False
                brief.slot = "source"
                _set(brief)
                return _question("source", brief)
            # New studio agent number spoken at confirm
            sel = _parse_source_answer(asked)
            if sel and (
                "studio" in asked.lower()
                or "agent" in asked.lower()
                or "edge" in asked.lower()
                or re.search(r"\b\d{2,5}\b", asked)
                or _parse_spoken_id_sequence(asked)
            ):
                brief.source_selector = sel
                brief.source_explicit = True
                brief.slot = "confirm"
                _set(brief)
                return _question("confirm", brief)
            # Explicit character correction at confirm
            if re.search(r"\b(?:change\s+(?:the\s+)?character|character\s+to)\b", asked, re.I):
                hit = cast_resolve.match_character(asked)
                if hit:
                    brief.character = str(hit.get("display_name") or hit.get("id"))
                    brief.slot = "confirm"
                    _set(brief)
                    return _question("confirm", brief)
                brief.slot = "character"
                _set(brief)
                return "Which character instead?"
            if _apply_same_as_source(brief, asked):
                # Still capture gold / clothing deltas on "same as original"
                if _GOLD_RE.search(asked):
                    brief.quality = "gold_standard"
                if _CLOTHING_RE.search(asked):
                    bit = asked.strip()[:160]
                    if bit and bit.lower() not in (brief.extras or "").lower():
                        brief.extras = (
                            f"{brief.extras}; {bit}".strip("; ")
                            if brief.extras
                            else bit
                        )
                brief.slot = "confirm"
                _set(brief)
                return _question("confirm", brief)
            # Treat as correction — re-seed and re-ask confirm
            _seed_from_utterance(brief, asked)
            if brief.mode == "create" and _SCENE_HINT_RE.search(asked) and not brief.scene:
                brief.scene = asked[:240]
            if not _source_ok(brief) and brief.mode in {
                "recreate", "adjust", "cast_swap", "cast_batch",
            }:
                brief.slot = "source"
                _set(brief)
                return _question("source", brief)
            brief.slot = "confirm"
            _set(brief)
            return _question("confirm", brief)
        if not _source_ok(brief) and brief.mode in {
            "recreate", "adjust", "cast_swap", "cast_batch",
        }:
            brief.slot = "source"
            _set(brief)
            return _question("source", brief)
        return _execute(brief, brain, cfg)

    brief.slot = _next_slot(brief)
    _set(brief)
    return _question(brief.slot, brief)


def _soft_fail_slot(reply: str) -> str | None:
    """If generate soft-failed, which brief slot to reopen (keep brief alive)."""
    low = (reply or "").lower()
    if not reply:
        return None
    if any(
        k in low
        for k in (
            "clearer scene",
            "need a scene",
            "what's the layout",
            "what should be happening",
            "scene or layout",
        )
    ):
        return "scene"
    if any(
        k in low
        for k in (
            "matched cast",
            "which character",
            "don't have a lora",
            "name the character",
            "cast name",
        )
    ):
        return "character"
    if "cancelled" in low:
        return None
    # Success-ish — clear
    if any(k in low for k in ("done.", "queued", "saved ", "stills")):
        return ""
    # Unknown failure — keep brief on confirm so user can retry
    if any(k in low for k in ("can't reach", "rejected", "error", "won't generate")):
        return "confirm"
    return ""


def _execute(brief: Brief, brain, cfg: dict) -> str:
    """Run generate / recreate / batch. Clear only on success or cancel."""
    reply = ""
    try:
        if brief.mode in {"recreate", "adjust"}:
            adjust = brief.scene if brief.mode == "adjust" else ""
            if brief.quality == "gold_standard" or brief.extras:
                bits = [adjust, brief.extras]
                if brief.quality == "gold_standard":
                    bits.append("gold standard, keep character pose and scene")
                adjust = ". ".join(b for b in bits if b)
            reply = gen_mod.recreate_or_adjust(
                brain,
                cfg,
                selector=brief.source_selector,
                adjust_text=adjust,
                locks=list(brief.locks),
            )
        elif brief.mode == "cast_swap":
            reply = gen_mod.cast_swap(
                brain,
                cfg,
                character=brief.character,
                selector=brief.source_selector,
                locks=list(brief.locks) or ["pose", "scene"],
            )
        elif brief.mode == "cast_batch":
            reply = gen_mod.cast_batch(
                brain,
                cfg,
                show_id=brief.batch_show,
                selector=brief.source_selector,
                locks=list(brief.locks) or ["pose", "scene"],
                cast_ids=list(brief.cast_ids),
            )
        else:
            if brief.character:
                hit = cast_resolve.match_character(brief.character)
                if not hit:
                    brief.slot = "character"
                    _set(brief)
                    return (
                        f"I still don't have a LoRA for {brief.character}. "
                        "Name the character clearly — for example Park Heejin."
                    )
            desc = f"{brief.character}. {brief.scene}".strip(". ")
            if brief.style:
                desc = f"{brief.style} style. {desc}"
            if brief.extras:
                desc = f"{desc}. {brief.extras}"
            if brief.quality == "gold_standard" or _GOLD_RE.search(desc):
                brief.quality = "gold_standard"
                if "gold standard" not in desc.lower():
                    desc = f"{desc}. gold standard"
            reply = gen_mod.generate(
                brain,
                desc,
                cfg,
                require_scene=True,
                scene_hint=brief.scene,
                locks=list(brief.locks),
                require_cast=bool(brief.character),
                quality=brief.quality or None,
            )
    except Exception as exc:  # noqa: BLE001
        log.exception("Brief execute failed: %s", exc)
        brief.slot = "confirm"
        _set(brief)
        try:
            from . import agent_pulse

            agent_pulse.set_status("nari", "ready", detail="")
        except Exception:
            pass
        return "That job failed. Say yes to try again, or cancel."

    slot = _soft_fail_slot(reply)
    if slot:  # reopen a slot — brief stays active
        brief.slot = slot
        _set(brief)
        try:
            from . import agent_pulse

            agent_pulse.set_status("nari", "ready", detail="Waiting on brief")
            agent_pulse.set_status("myra", "talking", detail=f"Brief: {slot}")
        except Exception:
            pass
        return reply
    # Success or empty-slot marker
    clear()
    try:
        from . import agent_pulse

        agent_pulse.set_status("nari", "ready", detail="")
        agent_pulse.set_status("myra", "listening", detail="Wake word")
    except Exception:
        pass
    return reply


def maybe_intercept(text: str) -> bool:
    """True if text should continue an active brief."""
    return is_active()


def wants_create_brief(text: str) -> bool:
    low = (text or "").lower()
    if detect_mode(text) != "create":
        return True  # recreate/swap/batch always brief-ish
    return any(
        k in low
        for k in (
            "make an image",
            "make a picture",
            "create an image",
            "create a picture",
            "generate an image",
            "draw me",
            "draw an",
        )
    )
