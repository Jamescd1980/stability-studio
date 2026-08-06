"""Lightweight intent classification for spoken commands.

Keeps fast on-device shortcuts; conversation goes to Myra (local) or Jan (studio)
depending on which wake word fired.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

NOTE_TRIGGERS = (
    "write this down", "take a note", "make a note", "note that",
    "remember this", "remember that", "jot this down", "add a note",
)
RECORD_TRIGGERS = (
    "make a recording", "make recording", "start a recording", "start recording",
    "begin recording", "begin a recording", "record this", "record a take",
    "record that", "take a recording", "start the recording",
)
GENERATE_TRIGGERS = (
    "generate", "render", "draw ", "make an image", "make a picture",
    "create an image", "create a picture", "paint ", "generate an image",
)
POSE_TRIGGERS = (
    "capture my pose", "use this pose", "capture pose", "take my pose",
    "use my pose", "grab my pose",
)
WEATHER_TRIGGERS = (
    "weather", "temperature", "how's the weather", "how is the weather",
    "forecast",
)
HEADLINE_TRIGGERS = (
    "headlines", "news headlines", "what's in the news", "whats in the news",
    "news today", "top news",
)
# Clock/date must never depend on the LLM naming a tool ("get data time").
DATETIME_TRIGGERS = (
    "what time is it", "what's the time", "whats the time", "what is the time",
    "what time", "current time", "tell me the time", "do you know the time",
    "what day is it", "what's the date", "whats the date", "what is the date",
    "what's today's date", "whats todays date", "what's the day", "whats the day",
    "tell me the date", "what's today", "whats today",
)
_DATETIME_RE = re.compile(
    r"\b(?:"
    r"what(?:'s|s|\s+is)?\s+(?:the\s+)?(?:time|date|day)(?:\s+is\s+it)?"
    r"|what\s+time(?:\s+is\s+it)?"
    r"|current\s+time"
    r"|tell\s+me\s+the\s+(?:time|date)"
    r")\b",
    re.I,
)
READ_TRIGGERS = (
    "read this book", "read the book", "read this chapter", "read the chapter",
    "read chapter", "read the new chapter", "read me the", "read me a",
    "read aloud", "reed chapter", "reed the chapter", "red chapter",
)
# STT often mangles "read chapter 1" → "Re-chapter 1" / "reed chapter one".
# Require a read-ish verb or re-chapter; bare "chapter one" alone is too greedy.
_READ_CHAPTER_RE = re.compile(
    r"(?:"
    r"\b(?:read|reed|red)\b.*\bchapter\b"
    r"|\bre-?chapter\b"
    r"|\b(?:read|reed)\s+(?:the\s+)?(?:new|latest|last)\s+chapter\b"
    r"|\b(?:read|reed)\s+(?:the\s+)?book\b"
    r")",
    re.I,
)
ASK_JAN_TRIGGERS = (
    "ask jan", "tell jan", "have jan", "get jan to", "ask jan to",
    "ask nari", "tell nari", "have nari", "get nari to", "ask nari to",
    # No hey_nari wake model yet — spoken after Hey Myra
    "hey nari", "hey jan", "talk to nari", "talk to jan",
    "switch to nari", "open nari",
)
ASK_ORLA_TRIGGERS = (
    "ask orla", "tell orla", "have orla", "get orla to", "ask orla to",
    "ask orluh", "have orluh", "tell orluh",  # TTS/STT of Orla
    "ask oral", "have oral", "tell oral", "ask orlo", "have orlo",
    "ask o'er", "have o'er", "ask o er", "have o er",
    # No hey_orla wake model yet — spoken after Hey Myra
    "hey orla", "hey orluh", "talk to orla", "talk to orluh",
    "switch to orla", "open orla",
)
# STT mangling of "Orla" in free speech (oral / orlo / o'er / o er).
_ORLA_NAME_RE = re.compile(
    r"\b(?:orla|orluh|oral|orlo|o'?er|o\s+er)\b",
    re.I,
)
PHONETIC_REWRITE_TRIGGERS = (
    "phonetically", "phonetic", "for read back", "for readback",
    "rewrite chapter", "prepare chapter for", "prepare for read",
)
SEARCH_TRIGGERS = (
    "search online", "research online", "look up", "look this up", "look that up",
    "look it up", "web search", "search the web", "google ",
)
# Deeper research → Nari (not Pi gofor)
RESEARCH_TRIGGERS = (
    "find out about", "research this", "figure this out", "dig into",
)
WEB_LOOKUP_TRIGGERS = (
    "look this up", "look that up", "look it up", "look up",
    "search online", "web search", "search the web", "google ",
)
RECREATE_TRIGGERS = (
    "recreate", "re-create", "re create", "try again", "redo that", "remake that",
    "same image but", "recreate image", "recreate that", "recreate the image",
)
# Must mention changing/swapping the character — bare "same scene" is a scene answer.
CAST_SWAP_TRIGGERS = (
    "change the character", "change character", "swap character", "swap the character",
)
CAST_SWAP_KEEP_TRIGGERS = (
    "keep the pose", "keep pose", "same pose", "keep the scene", "keep scene",
    "same scene", "same layout", "same pose and scene",
)
CAST_BATCH_TRIGGERS = (
    "one of each", "whole cast", "everyone from", "all the cast",
    "all characters from", "cast of ", "one image of each",
)
REFERENCE_TRIGGERS = (
    "grab reference images", "find reference images", "get reference images",
    "download reference images", "save reference images", "look up images",
    "find images of", "grab images", "reference images", "reference image",
    "grab references", "grab reference", "save reference", "download reference",
    "find reference", "get reference", "reference art",
)
# Display / night mode (Myra's ultrawide panel)
SCREENSAVER_ON_TRIGGERS = (
    "enable screensaver", "turn on screensaver", "start screensaver",
    "blank the screen", "blank screen", "blank the display", "blank the monitor",
    "turn off the screen", "turn off the display", "turn off the monitor",
    "screen off", "display off", "monitor off", "go dark",
)
SCREENSAVER_OFF_TRIGGERS = (
    "disable screensaver", "turn off screensaver", "stop screensaver",
    "wake the screen", "wake screen", "wake the display", "wake the monitor",
    "turn on the screen", "turn on the display", "turn on the monitor",
    "screen on", "display on", "monitor on",
)
COMFYBOX_SHOW_TRIGGERS = (
    "display comfybox status", "show comfybox status", "comfybox status",
    "display comfybox", "show comfybox", "open comfybox status",
    "show the comfybox monitor", "display the comfybox monitor",
    "show comfy box status", "display comfy box status", "comfy box status",
    "display a comfy box", "show a comfy box", "display the comfy box",
    "show the comfy box", "display comfy box", "show comfy box",
    "comfy box", "comfybox",
    # Hailo STT often hears Comfy → Compy / coffee
    "display compy box", "show compy box", "compy box status", "compy box",
    "display coffee box", "show coffee box", "coffee box status",
    "show gpu status", "display gpu status", "show training status",
)
# STT: ComfyBox → "comfy box" / "compy box" / "coffee box" / glued "compibox".
_COMFYBOX_SHOW_RE = re.compile(
    r"\b(?:display|show|open)\b.{0,40}\b(?:comfy|compy|coffee|compi)\b"
    r"|\b(?:comfy|compy|coffee|compi)\s*box\b"
    r"|\b(?:comfybox|compibox|compybox)\b",
    re.I,
)
COMFYBOX_HIDE_TRIGGERS = (
    "hide comfybox", "close comfybox", "dismiss comfybox",
    "hide comfybox status", "close comfybox status",
    "hide comfy box", "close comfy box",
    "hide status", "close status", "close the status", "hide the status",
    "close status display", "hide status display",
    "show clock", "show the clock", "show my clock",
    "show idle", "idle screen", "home screen",
    "show myra", "show my face", "back to myra",
)


@dataclass
class Intent:
    kind: str            # note | record | generate | image_brief | recreate | cast_swap | cast_batch | web_lookup | pose | weather | headlines | datetime | read | ask_jan | ask_orla | search | reference | screensaver_on | screensaver_off | comfybox_status | hide_display | conversation
    text: str            # cleaned payload (command stripped)
    raw: str
    persona: str = "myra"  # myra | jan | orla — set by wake word


def _strip_prefix(text: str, triggers: tuple[str, ...]) -> str:
    low = text.lower()
    for t in triggers:
        idx = low.find(t)
        if idx != -1:
            return text[idx + len(t):].strip(" ,.:;-")
    return text.strip()


_WEATHER_LOC_RE = re.compile(
    r"\b(?:in|for|at)\s+(.+)$",
    re.IGNORECASE,
)
_WEATHER_LOC_FLUFF_RE = re.compile(
    r"\b(?:"
    r"today|tonight|tomorrow|please|right\s+now|"
    r"this\s+(?:morning|afternoon|evening|weekend)|"
    r"for\s+today|for\s+tonight"
    r")\b.*$",
    re.IGNORECASE,
)


def _extract_weather_location(low: str) -> str:
    """Pull a place from phrases like 'forecast today in Casper, Wy'."""
    m = _WEATHER_LOC_RE.search(low)
    if not m:
        return ""
    loc = m.group(1).strip(" .?!,")
    loc = _WEATHER_LOC_FLUFF_RE.sub("", loc).strip(" .?!,")
    # Drop leading time words if the user said "in today Casper" (rare STT mess)
    loc = re.sub(
        r"^(?:today|tonight|tomorrow|this\s+(?:morning|afternoon|evening))\s+",
        "",
        loc,
        flags=re.I,
    ).strip(" .?!,")
    return loc


def classify(text: str, persona: str = "myra") -> Intent:
    raw = text.strip()
    low = raw.lower()
    persona = (persona or "myra").lower()
    if not low:
        return Intent("conversation", "", raw, persona=persona)

    if any(t in low for t in POSE_TRIGGERS):
        return Intent("pose", _strip_prefix(raw, POSE_TRIGGERS), raw, persona=persona)

    if any(t in low for t in NOTE_TRIGGERS):
        return Intent("note", _strip_prefix(raw, NOTE_TRIGGERS), raw, persona=persona)

    if any(t in low for t in RECORD_TRIGGERS):
        return Intent("record", _strip_prefix(raw, RECORD_TRIGGERS), raw, persona=persona)

    # Phonetic rewrite is Orla's job — catch before plain "read chapter".
    if any(t in low for t in PHONETIC_REWRITE_TRIGGERS) and "chapter" in low:
        return Intent("ask_orla", raw, raw, persona=persona)

    # "…to Orla / have Orla display / send the last image to Orla" — polish lane,
    # even if the sentence also says "have Nari".
    if _ORLA_NAME_RE.search(low) and any(
        k in low
        for k in (
            "display", "show", "open", "send", "over to", "hand off", "handoff",
            "give it to", "pass it", "look at",
        )
    ):
        return Intent("ask_orla", raw, raw, persona=persona)

    if any(t in low for t in ASK_ORLA_TRIGGERS):
        payload = _strip_prefix(raw, ASK_ORLA_TRIGGERS)
        # Bare "hey orla" / "talk to orla" → open Orla chat
        if not payload.strip() or payload.strip().lower() in {"please", "now"}:
            return Intent(
                "ask_orla",
                "You're on with Orla. Ask what they need in one short line.",
                raw,
                persona=persona,
            )
        return Intent("ask_orla", payload, raw, persona=persona)

    if any(t in low for t in ASK_JAN_TRIGGERS):
        payload = _strip_prefix(raw, ASK_JAN_TRIGGERS)
        if any(
            k in low
            for k in (
                "image", "picture", "generate", "draw", "paint", "recreate",
                "cast", "character",
            )
        ):
            return Intent("image_brief", payload or raw, raw, persona=persona)
        if not payload.strip() or payload.strip().lower() in {"please", "now"}:
            return Intent(
                "ask_jan",
                "You're on with Nari. What should we create?",
                raw,
                persona=persona,
            )
        return Intent("ask_jan", payload, raw, persona=persona)

    if any(t in low for t in REFERENCE_TRIGGERS):
        payload = _strip_prefix(raw, REFERENCE_TRIGGERS) or raw
        payload = re.sub(r"^(?:of|for|about)\s+", "", payload, flags=re.I).strip(" ,.:;-")
        return Intent("reference", payload or raw, raw, persona=persona)

    # Weather / headlines before search+read so "what's the weather" and
    # "read me the headlines" don't get stolen by search/read triggers.
    if any(t in low for t in WEATHER_TRIGGERS):
        return Intent("weather", _extract_weather_location(low), raw, persona=persona)

    if any(t in low for t in HEADLINE_TRIGGERS):
        return Intent("headlines", "", raw, persona=persona)

    if any(t in low for t in DATETIME_TRIGGERS) or _DATETIME_RE.search(low):
        return Intent("datetime", "", raw, persona=persona)

    # Display controls before search so "turn off the screen" isn't research.
    if any(t in low for t in COMFYBOX_HIDE_TRIGGERS):
        return Intent("hide_display", "", raw, persona=persona)
    if any(t in low for t in COMFYBOX_SHOW_TRIGGERS) or _COMFYBOX_SHOW_RE.search(low):
        return Intent("comfybox_status", "", raw, persona=persona)
    if any(t in low for t in SCREENSAVER_ON_TRIGGERS):
        return Intent("screensaver_on", "", raw, persona=persona)
    if any(t in low for t in SCREENSAVER_OFF_TRIGGERS):
        return Intent("screensaver_off", "", raw, persona=persona)

    # Short web lookup on Pi tool — never myra-gofor
    if any(t in low for t in WEB_LOOKUP_TRIGGERS):
        q = _strip_prefix(raw, WEB_LOOKUP_TRIGGERS)
        q = re.sub(r"^(?:for\s+me|please)\s+", "", q, flags=re.I).strip(" ,.:;-")
        return Intent("web_lookup", q or raw, raw, persona=persona)

    if any(t in low for t in RESEARCH_TRIGGERS):
        return Intent("ask_jan", raw, raw, persona=persona)

    if persona in {"jan", "nari"} and any(t in low for t in SEARCH_TRIGGERS):
        return Intent("search", raw, raw, persona=persona)

    if any(t in low for t in READ_TRIGGERS) or _READ_CHAPTER_RE.search(low):
        return Intent("read", raw, raw, persona=persona)

    if any(t in low for t in CAST_BATCH_TRIGGERS):
        return Intent("cast_batch", raw, raw, persona=persona)

    if any(t in low for t in CAST_SWAP_TRIGGERS) or (
        any(t in low for t in CAST_SWAP_KEEP_TRIGGERS)
        and re.search(r"\b(?:change|swap)\b", low)
        and "character" in low
    ):
        return Intent("cast_swap", raw, raw, persona=persona)

    if any(t in low for t in RECREATE_TRIGGERS):
        return Intent("recreate", raw, raw, persona=persona)

    # Generation → guided brief (thin Myra; Nari expands at the end)
    if any(re.search(rf"\b{re.escape(t.strip())}\b", low[:50]) for t in GENERATE_TRIGGERS):
        return Intent(
            "image_brief",
            _strip_prefix(raw, GENERATE_TRIGGERS),
            raw,
            persona=persona,
        )

    if persona in {"jan", "nari"} and any(
        k in low for k in ("image", "picture", "prompt", "storyboard", "inpaint", "edit the")
    ):
        return Intent("image_brief", raw, raw, persona=persona)
    if persona == "orla" and any(
        k in low for k in ("image", "display", "show", "open", "upscale", "newest", "last")
    ):
        return Intent("ask_orla", raw, raw, persona=persona)

    return Intent("conversation", raw, raw, persona=persona)
