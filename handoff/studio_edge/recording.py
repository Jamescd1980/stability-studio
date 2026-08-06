"""Voice take recorder — announce when ready, then capture until silence."""
from __future__ import annotations

import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import audio as audio_mod

log = logging.getLogger("studio_edge.recording")

# Optional TTS hook so the room tool can say the ready line before capture.
_announce_fn: Callable[[str], None] | None = None


def set_announce_fn(fn: Callable[[str], None] | None) -> None:
    """Wire Myra's speaker so start_recording can say the ready line first."""
    global _announce_fn
    _announce_fn = fn


def _cfg(cfg: dict) -> dict:
    room = (cfg.get("room_tools") or {}).get("recording") or {}
    top = cfg.get("recording") or {}
    merged = {**room, **top}
    return merged


def _ready_line() -> str:
    return "Starting recording now"


def start_recording(cfg: dict, *, announce: bool = True) -> str:
    """Announce when ready (optional), record until silence, save a WAV take.

    Returns a short speakable status. On success the ready line is spoken first
    (when announce=True and a speaker hook is set, or always returned for TTS).
    """
    rec = _cfg(cfg)
    if not rec.get("enabled", True):
        return "Recording is turned off in my config."

    audio_cfg = cfg.get("audio") or {}
    sample_rate = int(rec.get("sample_rate") or audio_cfg.get("sample_rate") or 16000)
    capture_rate = rec.get("capture_rate", audio_cfg.get("capture_rate"))
    silence_s = float(rec.get("silence_timeout_s") or audio_cfg.get("silence_timeout_s") or 2.0)
    max_utt = float(rec.get("max_utterance_s") or 60)
    input_device = audio_cfg.get("input_device")
    post_announce_s = float(rec.get("post_announce_s") or 0.45)

    if announce:
        line = _ready_line()
        if _announce_fn is not None:
            try:
                _announce_fn(line)
            except Exception as exc:  # noqa: BLE001
                log.warning("Recording announce failed: %s", exc)
                return "I couldn't start the recorder."
            time.sleep(max(0.0, post_announce_s))
        else:
            # No live speaker — caller should speak this return (tool/LLM path).
            # Still capture now so the take is saved; phrase is included in reply.
            pass

    log.info(
        "Recording take (sr=%s silence=%.1fs max=%.0fs device=%s)",
        sample_rate,
        silence_s,
        max_utt,
        input_device,
    )
    try:
        audio = audio_mod.record_until_silence(
            sample_rate=sample_rate,
            silence_timeout_s=silence_s,
            max_utterance_s=max_utt,
            input_device=input_device,
            capture_rate=capture_rate,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Recording capture failed: %s", exc)
        return "I couldn't open the microphone."

    peak = audio_mod.peak_level(audio)
    if audio is None or getattr(audio, "size", 0) == 0 or peak < 200:
        log.warning("Recording near-silence (peak=%s)", peak)
        return "I didn't catch anything. Check the mic isn't muted."

    path = _save_take(audio, sample_rate, rec)
    if not path:
        return "I recorded that, but couldn't save the file."

    name = path.name
    log.info("Saved recording %s (peak=%s)", path, peak)
    if announce and _announce_fn is None:
        return f"{_ready_line()}. Got it. Saved as {name}."
    return f"Got it. Saved as {name}."


def _save_take(audio, sample_rate: int, rec: dict) -> Path | None:
    local_dir = Path(os.path.expanduser(str(rec.get("local_dir") or "~/studio-recordings")))
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.warning("Could not create recording dir %s: %s", local_dir, exc)
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = local_dir / f"take_{stamp}.wav"
    try:
        audio_mod.write_wav(str(dest), audio, sample_rate)
    except Exception as exc:  # noqa: BLE001
        log.warning("write_wav failed: %s", exc)
        return None

    sync_dir = str(rec.get("sync_dir") or "").strip()
    if sync_dir:
        try:
            sync_root = Path(os.path.expanduser(sync_dir))
            sync_root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, sync_root / dest.name)
        except OSError as exc:
            log.warning("Recording sync copy failed: %s", exc)

    return dest
