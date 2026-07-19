"""Myra's room toolkit — weather, headlines, datetime, search, read-aloud (no studio MCP)."""
from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[misc, assignment]

log = logging.getLogger("studio_edge.room_tools")

# Set by read_aloud() so TTS can prefer a pre-rendered WAV on comfybox.
last_read_stem: str = ""

# Spoken chapter / book requests often look like: "read chapter 3", "read the new chapter"
_CHAPTER_RE = re.compile(
    r"(?:chapter|ch\.?|re-?chapter)\s*(\d+)|(?:new|latest|last)\s+chapter",
    re.IGNORECASE,
)
_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
}


def _chapter_num_from_stem(stem: str) -> int | None:
    """Extract chapter index from filenames like ch01_title or chapter_3."""
    m = re.match(r"^ch(?:apter)?[_\-.]?(\d+)(?:[_\-.]|$)", stem, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:^|[_\-.])chapter[_\-.]?(\d+)(?:[_\-.]|$)", stem, re.I)
    if m:
        return int(m.group(1))
    return None


def _spoken_chapter_num(query: str) -> int | None:
    """Parse 'chapter 1', 're-chapter one', etc."""
    q = (query or "").strip().lower()
    m = _CHAPTER_RE.search(q)
    if m and m.group(1):
        return int(m.group(1))
    m = re.search(r"(?:chapter|ch\.?|re-?chapter)\s+([a-z]+)\b", q, re.I)
    if m:
        return _WORD_NUMBERS.get(m.group(1).lower())
    return None


def _chapter_files_sorted(directory: Path) -> list[Path]:
    """Chapter text files ordered by numeric chapter index (not mtime)."""
    files = _list_text_files(directory)
    keyed: list[tuple[int, Path]] = []
    for p in files:
        num = _chapter_num_from_stem(p.stem)
        if num is not None:
            keyed.append((num, p))
    keyed.sort(key=lambda t: t[0])
    return [p for _, p in keyed]


def _f_to_spoken(temp_f: str | int | float | None) -> str:
    try:
        n = int(round(float(temp_f)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    return f"{n} degrees"


def get_weather(location: str = "", *, timeout_s: float = 10.0) -> str:
    """Current conditions + today's forecast via wttr.in (no API key). Speakable."""
    requested = (location or "").strip()
    loc = requested or "current"
    # Expand common US state abbreviations so wttr resolves the city, not a suburb.
    loc_query = re.sub(r",?\s*\bwy\b\.?$", ", Wyoming", loc, flags=re.I)
    loc_query = re.sub(r",?\s*\bco\b\.?$", ", Colorado", loc_query, flags=re.I)
    url = f"https://wttr.in/{quote(loc_query)}?format=j1"
    try:
        r = requests.get(url, timeout=timeout_s, headers={"User-Agent": "studio-edge/myra"})
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("Weather fetch failed: %s", exc)
        return "I couldn't reach the weather service."

    try:
        area = (data.get("nearest_area") or [{}])[0]
        area_name = (area.get("areaName") or [{}])[0].get("value") or loc_query
        region = (area.get("region") or [{}])[0].get("value") or ""
        # Prefer the place the user asked for when they named one.
        if requested and requested.lower() not in {"current", "here"}:
            place = requested
            # Title-case lightly for TTS if it came from STT lowercase
            if place == place.lower():
                place = place.title()
        else:
            place = f"{area_name}, {region}" if region else str(area_name)

        cur = (data.get("current_condition") or [{}])[0]
        desc = ((cur.get("weatherDesc") or [{}])[0].get("value") or "unknown conditions").strip().rstrip(",")
        now_f = _f_to_spoken(cur.get("temp_F"))
        feels_f = _f_to_spoken(cur.get("FeelsLikeF"))

        today = (data.get("weather") or [{}])[0]
        high = _f_to_spoken(today.get("maxtempF"))
        low = _f_to_spoken(today.get("mintempF"))
        # Midday chance of rain if present
        chance = ""
        for slot in today.get("hourly") or []:
            if str(slot.get("time")) in {"1200", "1500"}:
                c = slot.get("chanceofrain")
                if c is not None and str(c).isdigit() and int(c) >= 20:
                    chance = f" Chance of rain {int(c)} percent."
                break

        parts = [f"Weather for {place}: {desc}"]
        if now_f:
            parts[0] += f", {now_f}"
            if feels_f and feels_f != now_f:
                parts[0] += f", feels like {feels_f}"
        parts[0] += "."
        if high and low:
            parts.append(f"Today high {high}, low {low}.{chance}")
        elif high:
            parts.append(f"Today high {high}.{chance}")
        return " ".join(parts)
    except (IndexError, KeyError, TypeError) as exc:
        log.warning("Weather parse failed: %s", exc)
        return "I couldn't get a weather report right now."


def get_headlines(feeds: list[str] | None = None, *, limit: int = 5, timeout_s: float = 8.0) -> str:
    """Top headlines from RSS feeds. Returns a short spoken summary."""
    feeds = feeds or [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ]
    titles: list[str] = []
    for feed in feeds:
        if len(titles) >= limit:
            break
        try:
            r = requests.get(feed, timeout=timeout_s, headers={"User-Agent": "studio-edge/myra"})
            r.raise_for_status()
            root = ET.fromstring(r.content)
            # RSS 2.0 or Atom
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items:
                title_el = item.find("title")
                if title_el is None:
                    title_el = item.find("{http://www.w3.org/2005/Atom}title")
                if title_el is not None and (title_el.text or "").strip():
                    titles.append(title_el.text.strip())
                    if len(titles) >= limit:
                        break
        except Exception as exc:  # noqa: BLE001
            log.warning("Headline feed failed (%s): %s", feed, exc)

    if not titles:
        return "I couldn't load any headlines right now."
    spoken = "; ".join(titles[:limit])
    return f"Top headlines: {spoken}."


def _list_text_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    exts = {".txt", ".md", ".markdown", ".text"}
    files = [p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in exts]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def resolve_read_target(query: str, cfg: dict) -> Path | None:
    """Pick a chapter/book file from books_dir / chapters_dir based on spoken query."""
    read_cfg = cfg.get("room_tools", {}).get("read_aloud", {}) or {}
    chapters = Path(os.path.expanduser(read_cfg.get("chapters_dir", "~/studio-books/chapters")))
    books = Path(os.path.expanduser(read_cfg.get("books_dir", "~/studio-books")))

    q = (query or "").strip().lower()
    chapter_files = _chapter_files_sorted(chapters) if chapters.exists() else []
    book_files = _chapter_files_sorted(books) if books.exists() else []

    want = _spoken_chapter_num(q)
    if want is not None:
        for pool in (chapter_files, book_files):
            for p in pool:
                if _chapter_num_from_stem(p.stem) == want:
                    return p

    m = _CHAPTER_RE.search(q)
    if m or "new chapter" in q or "latest chapter" in q or "last chapter" in q:
        if chapter_files:
            return chapter_files[-1]
        if book_files:
            return book_files[-1]

    # Fuzzy: any filename token in the query
    for pool in (chapter_files, book_files):
        for p in pool:
            stem = p.stem.lower().replace("_", " ").replace("-", " ")
            if stem and stem in q:
                return p
            token = stem.split()[0] if stem.split() else ""
            if len(token) > 3 and token in q:
                return p

    if "book" in q or "chapter" in q or "read" in q:
        if chapter_files:
            return chapter_files[0]
        if book_files:
            return book_files[0]
    return None


def read_aloud_excerpt(path: Path, *, max_chars: int = 1200) -> str:
    """Load text for TTS; truncate long files with a spoken cue."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        log.error("Read failed %s: %s", path, exc)
        return "I couldn't open that file."
    if not text:
        return "That file is empty."
    # Soft strip markdown headings for speech
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^\s*#{1,6}\s*", "", line)
        lines.append(line)
    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        cut = text[:max_chars]
        # break on sentence if possible
        for sep in (". ", "! ", "? ", "\n"):
            idx = cut.rfind(sep)
            if idx > max_chars // 2:
                cut = cut[: idx + 1]
                break
        return f"From {path.stem}. {cut} That's enough for now — ask me to continue if you want more."
    return f"From {path.stem}. {text}"


def read_aloud(query: str, cfg: dict) -> str:
    global last_read_stem
    path = resolve_read_target(query, cfg)
    if path is None:
        last_read_stem = ""
        read_cfg = cfg.get("room_tools", {}).get("read_aloud", {}) or {}
        chapters = read_cfg.get("chapters_dir", "~/studio-books/chapters")
        return (
            f"I couldn't find a chapter to read. "
            f"Put text files in {chapters}, then say read chapter one, or read the new chapter."
        )
    max_chars = int((cfg.get("room_tools", {}).get("read_aloud") or {}).get("max_chars", 1200))
    log.info("Reading aloud: %s", path)
    last_read_stem = path.stem
    return read_aloud_excerpt(path, max_chars=max_chars)


def get_datetime(timezone: str = "America/Denver") -> str:
    """Speakable local date and time. Always uses the Pi clock; never invents."""
    tz_name = (timezone or "America/Denver").strip() or "America/Denver"
    try:
        if ZoneInfo is not None:
            now = datetime.now(ZoneInfo(tz_name))
        else:
            now = datetime.now().astimezone()
    except Exception as exc:  # noqa: BLE001
        log.warning("Timezone %s failed: %s", tz_name, exc)
        now = datetime.now().astimezone()
    # Prefer system-local if ZoneInfo drifts vs OS (Pi timedatectl is source of truth).
    try:
        local = datetime.now().astimezone()
        if abs((local - now).total_seconds()) > 120:
            log.warning(
                "ZoneInfo %s off by %ss vs system local; using system local",
                tz_name,
                int((local - now).total_seconds()),
            )
            now = local
    except Exception:  # noqa: BLE001
        pass
    hour = now.strftime("%I").lstrip("0") or "12"
    minute = now.strftime("%M")
    ampm = now.strftime("%p")
    day = now.strftime("%A")
    date = now.strftime("%B %d, %Y")
    # Explicit AM/PM words help Piper / STT sanity ("ten thirty-six A M").
    return f"It's {day}, {date}, {hour}:{minute} {ampm}."


def _tvmaze_lookup(query: str) -> str:
    """Best-effort TV schedule answer via TVmaze (no API key)."""
    q = (query or "").strip()
    if not q:
        return ""
    try:
        r = requests.get(
            "https://api.tvmaze.com/search/shows",
            params={"q": q},
            timeout=10,
            headers={"User-Agent": "studio-edge/myra"},
        )
        r.raise_for_status()
        hits = r.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("TVmaze search failed: %s", exc)
        return ""
    if not isinstance(hits, list) or not hits:
        return ""
    show = (hits[0] or {}).get("show") or {}
    name = show.get("name") or q
    status = show.get("status") or "unknown status"
    network = ((show.get("network") or {}) or {}).get("name") or ""
    web = ((show.get("webChannel") or {}) or {}).get("name") or ""
    channel = network or web or "an unknown channel"
    schedule = show.get("schedule") or {}
    days = schedule.get("days") or []
    time_s = schedule.get("time") or ""
    when = ""
    if days and time_s:
        when = f" It usually airs {', '.join(days)} at {time_s}."
    elif days:
        when = f" It usually airs on {', '.join(days)}."
    premiered = show.get("premiered") or ""
    bit = f"{name} is {status} on {channel}.{when}"
    if premiered:
        bit += f" Premiered {premiered}."
    return bit.strip()


def web_search(query: str, *, max_results: int = 3) -> str:
    """Lightweight look-up: TVmaze for shows, DuckDuckGo Instant Answer otherwise."""
    q = (query or "").strip()
    if not q:
        return "I need something to search for."

    low = q.lower()
    if any(
        k in low
        for k in (
            "air",
            "airs",
            "channel",
            "episode",
            "season",
            "tv show",
            "series",
            "streaming",
            "on hulu",
            "on netflix",
            "on max",
            "on disney",
        )
    ):
        # Strip filler for TVmaze
        show_q = re.sub(
            r"\b(when|where|what|channel|does|do|is|the|show|tv|air|airs|airing|on)\b",
            " ",
            q,
            flags=re.I,
        )
        show_q = re.sub(r"\s+", " ", show_q).strip() or q
        tv = _tvmaze_lookup(show_q)
        if tv:
            return tv

    # DuckDuckGo Instant Answer (no key)
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": q, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10,
            headers={"User-Agent": "studio-edge/myra"},
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("DuckDuckGo failed: %s", exc)
        return "I couldn't reach the search service."

    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        # Keep spoken answers short
        if len(abstract) > 420:
            abstract = abstract[:417].rsplit(" ", 1)[0] + "…"
        source = (data.get("AbstractSource") or "").strip()
        return f"{abstract}" + (f" Source: {source}." if source else "")

    topics = data.get("RelatedTopics") or []
    bits: list[str] = []
    for item in topics:
        if not isinstance(item, dict):
            continue
        text = (item.get("Text") or "").strip()
        if text:
            bits.append(text.split(" - ")[0][:160])
        if len(bits) >= max(1, min(max_results, 3)):
            break
    if bits:
        return "Here's what I found: " + "; ".join(bits) + "."
    return f"I couldn't find a clear answer for {q}."


# Tool schemas for Ollama / OpenAI-compatible function calling
TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get current weather and today's forecast for a city or region. "
                "Use when the user asks about weather, temperature, or forecast. "
                "Always pass the city they named (e.g. Casper, Wyoming)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or place name, including state if given. Empty = default location from config.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_headlines",
            "description": "Fetch a few current news headlines. Use for news, headlines, or what's in the news.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": (
                "Return the current local day, date, and time as a spoken sentence. "
                "Call this tool for time/date questions. Never invent a time. "
                "Never speak the tool name aloud — only speak the tool result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone, e.g. America/Denver. Empty = config default.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Look up a simple fact or TV/show airing info (channel, schedule, status). "
                "Use for when does X air, what channel, where can I watch, or short web facts. "
                "Not for image generation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'The Last of Us season 2 air time channel'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_aloud",
            "description": "Read a book chapter or manuscript file aloud. Use for read this chapter, read the book, read chapter N.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to read, e.g. chapter 3, new chapter, or a book title.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": (
                "Set a local timer or reminder. Use for remind me in 20 minutes, set a timer for 5 minutes, "
                "timer 90 seconds. No internet required."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_text": {
                        "type": "string",
                        "description": "How long, e.g. '20 minutes' or 'in 90 seconds'.",
                    },
                    "label": {
                        "type": "string",
                        "description": "Optional label, e.g. 'check the oven' or 'coffee'.",
                    },
                },
                "required": ["duration_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_timers",
            "description": "List active local timers.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_timer",
            "description": "Cancel a timer by label, or cancel all timers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label_query": {
                        "type": "string",
                        "description": "Label fragment to match, or 'all'.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Write a short note to the local notes file. Use for write this down, note that, remember this.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The note text to save."}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_notes",
            "description": "Read the most recent local notes aloud/summarize path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many recent lines (default 5).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "thermostat_status",
            "description": "House thermostat status. Not live until Home Assistant is wired.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "thermostat_set",
            "description": "Set thermostat temperature. Stub until Home Assistant is wired.",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature_f": {"type": "number"},
                    "mode": {"type": "string", "description": "heat, cool, auto, off"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_next",
            "description": "Next calendar event. Stub until calendar is wired.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lights_control",
            "description": "Control lights. Stub until Home Assistant is wired.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "on, off, dim"},
                    "room": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "traffic_eta",
            "description": "Traffic / drive ETA. Stub until maps API is wired.",
            "parameters": {
                "type": "object",
                "properties": {"destination": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "package_status",
            "description": "Package tracking. Stub until carrier API is wired.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "studio_mcp_status",
            "description": "Whether Nari can reach Windows studio MCP tools yet.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_nari",
            "description": (
                "Send work to Nari on ComfyBox (create image, Forge refine, Wan clip, "
                "style/prompt planning for generation). Use when the user says have Nari, "
                "make an image, refine, Forge, short clip, or Comfy. Not for upscale/RIFE."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "What Nari should do, in plain language.",
                    }
                },
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_orla",
            "description": (
                "Send work to Orla on the Windows main PC (open/display still or clip, "
                "upscale, RIFE/interp, ffmpeg polish, Kokoro prep, rewrite chapter phonetically "
                "for read back). Use when the user says have Orla, open the image, show it, "
                "upscale, interpolate, or rewrite a chapter phonetically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "What Orla should do, in plain language.",
                    }
                },
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_jan",
            "description": (
                "Deprecated alias for ask_nari (studio create brain). Same destination."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "What the studio brain should do, in plain language.",
                    }
                },
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enable_screensaver",
            "description": (
                "Blank Myra's monitor and enable the screensaver for sleep / night. "
                "Use for enable screensaver, blank the screen, turn off the screen, go dark."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disable_screensaver",
            "description": (
                "Wake Myra's monitor and disable the screensaver. "
                "Use for wake the screen, turn on the screen, disable screensaver."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_comfybox_status",
            "description": (
                "Show the full-screen ComfyBox GPU/status monitor on Myra's display. "
                "Use for display ComfyBox status, show ComfyBox, GPU status, training status."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hide_comfybox_status",
            "description": (
                "Hide ComfyBox status and return to Myra's idle clock face. "
                "Also use for show clock, home screen, show Myra."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _orla_tools_post(tools_url: str, payload: dict, *, timeout_s: float = 15.0) -> dict:
    url = (tools_url or "").rstrip("/") + "/action"
    try:
        r = requests.post(url, json=payload, timeout=timeout_s)
        data = r.json()
        return data if isinstance(data, dict) else {"ok": False, "error": "bad response"}
    except (requests.RequestException, ValueError) as exc:
        log.warning("Orla tools failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def run_tool(name: str, arguments: dict, cfg: dict, jan_brain, orla_brain=None) -> str:
    """Execute a room tool. ask_nari→Nari, ask_orla→Orla (+ tools sidecar when needed)."""
    args = arguments or {}
    room = cfg.get("room_tools") or {}

    if name == "get_weather":
        if not room.get("weather", {}).get("enabled", True):
            return "Weather is turned off in my config."
        loc = (args.get("location") or "").strip() or room.get("weather", {}).get("default_location", "")
        return get_weather(loc)

    if name == "get_headlines":
        if not room.get("headlines", {}).get("enabled", True):
            return "Headlines are turned off in my config."
        feeds = room.get("headlines", {}).get("feeds")
        limit = int(room.get("headlines", {}).get("limit", 5))
        return get_headlines(feeds, limit=limit)

    if name == "get_datetime":
        if not room.get("datetime", {}).get("enabled", True):
            return "Date and time lookup is turned off in my config."
        tz = (args.get("timezone") or "").strip() or room.get("datetime", {}).get(
            "timezone", "America/Denver"
        )
        return get_datetime(tz)

    if name == "web_search":
        if not room.get("web_search", {}).get("enabled", True):
            return "Web search is turned off in my config."
        q = (args.get("query") or args.get("request") or "").strip()
        limit = int(room.get("web_search", {}).get("max_results", 3))
        return web_search(q, max_results=limit)

    if name == "read_aloud":
        if not room.get("read_aloud", {}).get("enabled", True):
            return "Read aloud is turned off in my config."
        return read_aloud(args.get("query") or args.get("request") or "", cfg)

    if name in {"ask_jan", "ask_nari"}:
        request = (args.get("request") or "").strip()
        if not request:
            return "I need something to ask Nari."
        if jan_brain is None:
            return "Nari isn't configured."
        from . import generate as gen_mod

        low = request.lower()
        # Hand-off / display of an existing still is Orla — never a new generate.
        if re.search(r"\b(?:orla|orluh|oral|orlo|o'?er|o\s+er)\b", low) and any(
            k in low
            for k in (
                "display", "show", "open", "send", "over to", "hand off",
                "last image", "the image", "newest", "next", "previous",
            )
        ):
            return run_tool(
                "ask_orla",
                {"request": request},
                cfg,
                jan_brain,
                orla_brain=orla_brain,
            )
        # Video / Forge refine are not the still generate.py path.
        if any(k in low for k in ("refine", "forge", "adetailer")) and not any(
            k in low for k in ("make an image", "generate", "draw", "paint")
        ):
            return (
                "Forge refine isn't on the voice still path yet. "
                "Ask from the Windows studio agent, or say generate an image for a new still."
            )
        if any(k in low for k in ("wan", "i2v", "video clip", "make a video", "make a clip")):
            return (
                "Wan clips aren't on the voice still path yet. "
                "Use the Windows studio agent for video, or ask for a still image."
            )
        create_keys = (
            "draw", "render", "generate", "paint", "comfy",
            "make an image", "make a picture", "create an image", "create a picture",
        )
        # Bare "image" alone is too greedy ("send the last image to Orla").
        if any(k in low for k in create_keys) or (
            ("image" in low or "picture" in low or "still" in low)
            and not any(
                k in low
                for k in ("last image", "the image", "send", "display", "show", "open", "over to")
            )
        ):
            return gen_mod.generate(jan_brain, request, cfg)
        return jan_brain.ask(
            "The user spoke to Myra (gofor) and asked you (Nari) to help. "
            f"Request: {request}. "
            "Reply in one to three short spoken sentences. No markdown."
        )

    if name == "ask_orla":
        request = (args.get("request") or "").strip()
        if not request:
            return "I need something to ask Orla."
        orla_cfg = cfg.get("orla") or {}
        if not orla_cfg.get("enabled", True):
            return "Orla is turned off in my config."
        low = request.lower()
        tools_url = str(orla_cfg.get("tools_url") or "http://192.168.50.42:11436")
        action_bits: list[str] = []

        # Phonetic chapter prep — resolve text on Pi, Orla rewrites on Windows.
        if any(
            k in low
            for k in (
                "phonetic",
                "phonetically",
                "read back",
                "readback",
                "rewrite chapter",
                "prepare chapter",
            )
        ):
            path = resolve_read_target(request, cfg)
            if path is None:
                return (
                    "I couldn't find that chapter to rewrite. "
                    "Say rewrite chapter two phonetically for read back."
                )
            try:
                chapter_text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                log.warning("Chapter read failed: %s", exc)
                return "I couldn't open that chapter file."
            # Cap payload size for LAN rewrite
            max_chars = int(orla_cfg.get("phonetic_max_chars") or 12000)
            if len(chapter_text) > max_chars:
                chapter_text = chapter_text[:max_chars]
            result = _orla_tools_post(
                tools_url,
                {
                    "action": "phonetic_rewrite",
                    "stem": path.stem,
                    "chapter": _spoken_chapter_num(low) or _chapter_num_from_stem(path.stem),
                    "text": chapter_text,
                    "also_speak": any(k in low for k in ("speak", "narrate", "kokoro", "read it")),
                },
                timeout_s=float(orla_cfg.get("phonetic_timeout_s") or 180),
            )
            if result.get("ok"):
                out = result.get("path") or "phonetic file"
                msg = f"Orla rewrote {path.stem} for read back. Saved as {out}."
                if result.get("wav"):
                    msg += f" Kokoro WAV at {result['wav']}."
                return msg
            return (
                f"Orla couldn't finish the phonetic rewrite: "
                f"{result.get('error', 'tools offline')}."
            )

        # Gallery vocab:
        #   last image     = last one displayed (history)
        #   newest image   = by file date/time
        #   next/previous  = walk current batch in creation order
        gallery_hit = any(
            k in low
            for k in (
                "open", "display", "show", "look at", "send",
                "last image", "newest", "next", "previous", "prev",
            )
        )
        if gallery_hit:
            kind = "video" if any(k in low for k in ("clip", "video", "movie")) else "image"
            if re.search(r"\b(?:next|forward)\b", low):
                selector = "next"
            elif re.search(r"\b(?:previous|prev|go back)\b", low):
                selector = "previous"
            elif re.search(r"\b(?:newest|most recent)\b", low):
                selector = "newest"
            elif re.search(r"\blast\b", low):
                selector = "last_displayed"
            else:
                # "display the image" / handoff without last|newest → newest by date
                selector = "newest"
            result = _orla_tools_post(
                tools_url,
                {
                    "action": "open",
                    "kind": kind,
                    "selector": selector,
                    "request": request,
                },
            )
            if result.get("ok"):
                sel = result.get("selector") or selector
                label = {
                    "last_displayed": "last displayed",
                    "newest": "newest",
                    "next": "next in batch",
                    "previous": "previous in batch",
                }.get(sel, sel)
                action_bits.append(
                    f"Opened the {label} {result.get('kind', kind)} on the main PC."
                )
            else:
                action_bits.append(
                    f"I couldn't open it yet: {result.get('error', 'Orla tools offline')}."
                )
        if any(k in low for k in ("upscale", "interp", "interpolate", "rife", "ffmpeg", "polish")):
            action_bits.append(
                "Upscale and interp tools are queued for Orla next — not fully wired yet."
            )
        if orla_brain is not None:
            try:
                chat = orla_brain.ask(
                    "The user spoke to Myra and asked you (Orla) to help. "
                    f"Request: {request}. "
                    "Reply in one to three short spoken sentences. No markdown."
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Orla chat failed: %s", exc)
                chat = ""
            if chat and action_bits:
                return f"{' '.join(action_bits)} {chat}"
            if chat:
                return chat
        if action_bits:
            return " ".join(action_bits)
        return "Orla isn't reachable right now. Is Ollama running on the main PC?"

    if name == "enable_screensaver":
        from . import display as display_mod

        return display_mod.enable_screensaver(cfg)

    if name == "disable_screensaver":
        from . import display as display_mod

        return display_mod.disable_screensaver(cfg)

    if name == "show_comfybox_status":
        from . import display as display_mod

        return display_mod.show_comfybox_status(cfg)

    if name == "hide_comfybox_status":
        from . import display as display_mod

        return display_mod.hide_comfybox_status(cfg)

    if name == "set_timer":
        from . import timers as timers_mod

        return timers_mod.set_timer(
            cfg,
            duration_text=str(args.get("duration_text") or args.get("duration") or ""),
            seconds=int(args.get("seconds") or 0),
            label=str(args.get("label") or ""),
        )

    if name == "list_timers":
        from . import timers as timers_mod

        return timers_mod.list_timers(cfg)

    if name == "cancel_timer":
        from . import timers as timers_mod

        return timers_mod.cancel_timers(cfg, str(args.get("label_query") or args.get("label") or ""))

    if name == "add_note":
        if not room.get("notes", {}).get("enabled", True):
            return "Notes are turned off in my config."
        from . import notes as notes_mod

        text = (args.get("text") or args.get("note") or "").strip()
        if not text:
            return "What should I write down?"
        notes_cfg = cfg.get("notes") or {}
        path = notes_mod.append_note(
            text,
            notes_cfg.get("local_dir", "~/studio-notes"),
            notes_cfg.get("filename", "voice-notes.md"),
            notes_cfg.get("sync_dir", "") or "",
        )
        return "Got it. I wrote that down." if path else "I couldn't save the note."

    if name == "read_notes":
        if not room.get("notes", {}).get("enabled", True):
            return "Notes are turned off in my config."
        notes_cfg = cfg.get("notes") or {}
        path = Path(os.path.expanduser(notes_cfg.get("local_dir", "~/studio-notes"))) / notes_cfg.get(
            "filename", "voice-notes.md"
        )
        if not path.is_file():
            return "You don't have any notes yet."
        try:
            lines = [
                ln.strip()
                for ln in path.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
        except OSError:
            return "I couldn't read your notes file."
        if not lines:
            return "Your notes file is empty."
        limit = int(args.get("limit") or 5)
        recent = lines[-max(1, min(limit, 12)) :]
        return "Recent notes: " + " ".join(recent)

    if name == "thermostat_status":
        from .integrations import stubs

        return stubs.thermostat_status(cfg)

    if name == "thermostat_set":
        from .integrations import stubs

        temp = args.get("temperature_f")
        try:
            temp_f = float(temp) if temp is not None else None
        except (TypeError, ValueError):
            temp_f = None
        return stubs.thermostat_set(cfg, temperature_f=temp_f, mode=str(args.get("mode") or ""))

    if name == "calendar_next":
        from .integrations import stubs

        return stubs.calendar_next(cfg)

    if name == "lights_control":
        from .integrations import stubs

        return stubs.lights_control(
            cfg, action=str(args.get("action") or ""), room=str(args.get("room") or "")
        )

    if name == "traffic_eta":
        from .integrations import stubs

        return stubs.traffic_eta(cfg, destination=str(args.get("destination") or ""))

    if name == "package_status":
        from .integrations import stubs

        return stubs.package_status(cfg, query=str(args.get("query") or ""))

    if name == "studio_mcp_status":
        from .integrations import stubs

        return stubs.studio_mcp_bridge_status(cfg)

    return f"I don't know the tool {name}."
