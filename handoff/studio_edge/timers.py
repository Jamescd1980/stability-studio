"""Local timers / reminders for Myra (no cloud)."""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("studio_edge.timers")

_WORD_MINUTES = {
    "half a minute": 0.5,
    "a minute": 1,
    "one minute": 1,
    "two minutes": 2,
    "three minutes": 3,
    "four minutes": 4,
    "five minutes": 5,
    "ten minutes": 10,
    "fifteen minutes": 15,
    "twenty minutes": 20,
    "thirty minutes": 30,
    "an hour": 60,
    "one hour": 60,
    "two hours": 120,
}

_lock = threading.Lock()
_speak: Callable[[str], None] | None = None
_thread: threading.Thread | None = None
_stop = threading.Event()


def _state_path(cfg: dict) -> Path:
    raw = (cfg.get("room_tools") or {}).get("timers", {}).get("state_file")
    if raw:
        return Path(raw).expanduser()
    return Path("~/studio-edge/state/timers.json").expanduser()


def _load(cfg: dict) -> list[dict[str, Any]]:
    path = _state_path(cfg)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("timers") or [])
    except (OSError, ValueError) as exc:
        log.warning("Timer load failed: %s", exc)
        return []


def _save(cfg: dict, timers: list[dict[str, Any]]) -> None:
    path = _state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"timers": timers}, indent=2), encoding="utf-8")


def parse_duration_seconds(text: str) -> int | None:
    """Parse '20 minutes', 'in 5 minutes', '90 seconds', '1 hour'."""
    q = (text or "").strip().lower()
    if not q:
        return None
    for phrase, mins in _WORD_MINUTES.items():
        if phrase in q:
            return int(mins * 60)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)\b", q)
    if not m:
        m = re.search(r"\bin\s+(\d+(?:\.\d+)?)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)?\b", q)
        if not m:
            return None
        amount = float(m.group(1))
        unit = (m.group(2) or "minutes").lower()
    else:
        amount = float(m.group(1))
        unit = m.group(2).lower()
    if unit.startswith("sec"):
        return max(1, int(amount))
    if unit.startswith("min"):
        return max(1, int(amount * 60))
    if unit.startswith("hour") or unit.startswith("hr"):
        return max(1, int(amount * 3600))
    return max(1, int(amount * 60))


def set_timer(cfg: dict, *, duration_text: str = "", seconds: int = 0, label: str = "") -> str:
    if not (cfg.get("room_tools") or {}).get("timers", {}).get("enabled", True):
        return "Timers are turned off in my config."
    secs = int(seconds) if seconds and int(seconds) > 0 else 0
    if secs <= 0:
        secs = parse_duration_seconds(duration_text) or 0
    if secs <= 0:
        return "Tell me how long, like twenty minutes or 90 seconds."
    max_s = int((cfg.get("room_tools") or {}).get("timers", {}).get("max_seconds", 24 * 3600))
    secs = min(secs, max_s)
    label = (label or duration_text or "timer").strip()
    # Strip leading "remind me in ..."
    label = re.sub(r"^(remind me( to)?|set a timer( for)?|timer( for)?)\s+", "", label, flags=re.I)
    due = datetime.now() + timedelta(seconds=secs)
    entry = {
        "id": uuid.uuid4().hex[:8],
        "label": label[:120] or "timer",
        "due_ts": due.timestamp(),
        "due_iso": due.isoformat(timespec="seconds"),
        "created_iso": datetime.now().isoformat(timespec="seconds"),
    }
    with _lock:
        timers = _load(cfg)
        timers.append(entry)
        _save(cfg, timers)
    if secs < 120:
        when = f"{secs} seconds"
    elif secs < 3600:
        when = f"{secs // 60} minutes"
    else:
        when = f"{secs / 3600:.1f} hours".replace(".0 hours", " hours")
    return f"Okay. Timer set for {when}. I'll announce: {entry['label']}."


def list_timers(cfg: dict) -> str:
    with _lock:
        timers = _load(cfg)
    now = time.time()
    active = [t for t in timers if float(t.get("due_ts") or 0) > now]
    if not active:
        return "You don't have any timers running."
    active.sort(key=lambda t: float(t.get("due_ts") or 0))
    parts = []
    for t in active[:5]:
        left = max(0, int(float(t["due_ts"]) - now))
        if left < 120:
            left_s = f"{left} seconds"
        else:
            left_s = f"{left // 60} minutes"
        parts.append(f"{t.get('label', 'timer')} in {left_s}")
    return "Active timers: " + "; ".join(parts) + "."


def cancel_timers(cfg: dict, label_query: str = "") -> str:
    q = (label_query or "").strip().lower()
    with _lock:
        timers = _load(cfg)
        if not timers:
            return "There are no timers to cancel."
        if not q or q in {"all", "everything"}:
            n = len(timers)
            _save(cfg, [])
            return f"Cancelled {n} timer{'s' if n != 1 else ''}."
        keep = []
        removed = 0
        for t in timers:
            if q in str(t.get("label", "")).lower() or q == str(t.get("id", "")).lower():
                removed += 1
            else:
                keep.append(t)
        _save(cfg, keep)
    if removed:
        return f"Cancelled {removed} timer{'s' if removed != 1 else ''}."
    return "I couldn't find a matching timer."


def pop_due(cfg: dict) -> list[dict[str, Any]]:
    now = time.time()
    with _lock:
        timers = _load(cfg)
        due = [t for t in timers if float(t.get("due_ts") or 0) <= now]
        if not due:
            return []
        keep = [t for t in timers if float(t.get("due_ts") or 0) > now]
        _save(cfg, keep)
        return due


def start_watcher(cfg: dict, speak: Callable[[str], None]) -> None:
    """Background thread: announce due timers. Idempotent."""
    global _speak, _thread
    _speak = speak
    if _thread and _thread.is_alive():
        return
    _stop.clear()

    def _loop() -> None:
        while not _stop.is_set():
            try:
                due = pop_due(cfg)
                for t in due:
                    msg = f"Timer done. {t.get('label', 'Your timer')}."
                    log.info("Timer fired: %s", t)
                    if _speak:
                        try:
                            _speak(msg)
                        except Exception as exc:  # noqa: BLE001
                            log.warning("Timer speak failed: %s", exc)
            except Exception as exc:  # noqa: BLE001
                log.warning("Timer watcher error: %s", exc)
            _stop.wait(1.0)

    _thread = threading.Thread(target=_loop, name="myra-timers", daemon=True)
    _thread.start()


def stop_watcher() -> None:
    _stop.set()
