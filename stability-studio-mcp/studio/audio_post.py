"""MOSS audio post-processing and voice-design helpers."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Matches MOSS Audio Tokenizer / SoundEffect constant.
TOKENS_PER_SECOND = 12.5

_DURATION_HINT_RE = re.compile(
    r"\b("
    r"about\s+\d+(?:\s*(?:to|-)\s*\d+)?\s*seconds?|"
    r"\d+(?:\.\d+)?\s*seconds?|"
    r"short\s+clip|long\s+clip|"
    r"(?:unhurried|relaxed|slow|quick|fast)\s+pace|"
    r"no\s+long\s+pauses|"
    r"starts?\s+at|"
    r"wait\s+\d+"
    r")\b",
    re.IGNORECASE,
)


def sanitize_voice_instruction(instruction: str) -> str:
    """Remove timing/duration hints — VoiceGenerator treats them as behavior, not metadata."""
    cleaned = _DURATION_HINT_RE.sub("", instruction)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ,.")


def polish_voice_instruction(instruction: str, text: str) -> str:
    """VoiceGenerator dramatizes 'relaxed/calm' as long pre-speech pauses on short lines."""
    cleaned = sanitize_voice_instruction(instruction)
    cleaned = re.sub(r"\bcalm and relaxed\b", "warm steady", cleaned, flags=re.I)
    cleaned = re.sub(r"\brelaxed\b", "steady", cleaned, flags=re.I)
    words = len(text.split())
    if words <= 6 and "no long pause" not in cleaned.lower():
        cleaned = f"{cleaned}, brief natural delivery, no long pause before the words"
    return cleaned.strip(" ,.")


def seconds_to_audio_tokens(seconds: float) -> int:
    """MOSS codec frame rate: 12.5 audio tokens per second."""
    return max(1, int(float(seconds) * TOKENS_PER_SECOND))


def estimate_voice_max_tokens(
    text: str,
    *,
    duration_seconds: float | None = None,
    padding_seconds: float = 0.75,
) -> int:
    """Cap max_new_tokens — use explicit duration when set, else estimate from text."""
    if duration_seconds is not None:
        target = seconds_to_audio_tokens(duration_seconds)
        return max(target + 16, min(512, target + 32))
    words = max(1, len(text.split()))
    if words <= 4:
        est_seconds = max(1.2, words * 0.28 + 0.35)
        tokens = seconds_to_audio_tokens(est_seconds)
        return max(48, min(80, tokens))
    est_seconds = max(1.0, words * 0.35 + padding_seconds)
    tokens = seconds_to_audio_tokens(est_seconds)
    return max(72, min(256, tokens))


def comfy_python(cfg: dict[str, Any]) -> Path:
    return Path(cfg["stability_matrix"]["packages"]["comfyui"]) / "venv" / "Scripts" / "python.exe"


def trim_to_main_speech(
    path: Path,
    cfg: dict[str, Any],
    *,
    peak_ratio: float = 0.55,
    pad_seconds: float = 0.5,
) -> Path:
    """Keep main speech and add natural head/tail room (~0.5s each side by default)."""
    py = comfy_python(cfg)
    if not py.is_file() or not path.is_file():
        return path

    script = r"""
import sys
from pathlib import Path
import librosa
import numpy as np
import soundfile as sf

src = Path(sys.argv[1])
peak_ratio = float(sys.argv[2])
pad_seconds = float(sys.argv[3])
y, sr = librosa.load(src, sr=None, mono=True)
pad = int(pad_seconds * sr)
hop = 512
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
peak = float(np.max(rms)) or 1.0
threshold = peak * peak_ratio
main_start = 0
for i in range(len(rms)):
    if rms[i] < threshold:
        continue
    end = min(len(rms), i + 5)
    if np.mean(rms[i:end]) >= threshold * 0.85:
        main_start = i * hop
        break
body = y[main_start:]
body, _ = librosa.effects.trim(body, top_db=28)
if len(body) == 0:
    raise SystemExit(0)
main_end = main_start + len(body)
head = y[max(0, main_start - pad):main_start]
tail = y[main_end:min(len(y), main_end + pad)]
if len(head) < pad:
    head = np.concatenate([np.zeros(pad - len(head), dtype=y.dtype), head])
if len(tail) < pad:
    tail = np.concatenate([tail, np.zeros(pad - len(tail), dtype=y.dtype)])
out = np.concatenate([head, body, tail])
sf.write(src, out, sr)
"""
    subprocess.run(
        [str(py), "-c", script, str(path), str(peak_ratio), str(pad_seconds)],
        check=True,
        capture_output=True,
        text=True,
    )
    return path


def trim_leading_trailing_silence(path: Path, cfg: dict[str, Any], *, top_db: int = 30) -> Path:
    """Normalize MOSS voice-design clips: drop long preamble, keep padded speech."""
    return trim_to_main_speech(path, cfg)
