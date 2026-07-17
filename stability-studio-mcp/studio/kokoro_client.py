"""Kokoro narrate TTS client — HTTP service on generation host :8090 (CPU, no GPU lock)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from studio.output_paths import deliver_files


def _kokoro_config(cfg: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "enabled": True,
        "url": "",
        "voice": "am_michael",
        "speed": 0.87,
        "timeout_seconds": 300,
        "pause_period_s": 0.45,
        "pause_comma_s": 0.22,
        "pause_paragraph_s": 0.7,
        "doc": "AUDIO-KOKORO.md",
    }
    # Prefer kokoro: ; fall back to narrate: for studio-edge parity
    merged = dict(defaults)
    merged.update(cfg.get("narrate") or {})
    merged.update(cfg.get("kokoro") or {})
    return merged


def kokoro_url(cfg: dict[str, Any]) -> str:
    g = _kokoro_config(cfg)
    if not g.get("enabled", True):
        return ""
    explicit = str(g.get("url") or "").rstrip("/")
    if explicit:
        return explicit
    comfy = str((cfg.get("comfyui") or {}).get("url") or "")
    parsed = urlparse(comfy)
    host = parsed.hostname
    if not host or host in {"127.0.0.1", "localhost"}:
        return ""
    scheme = parsed.scheme or "http"
    return f"{scheme}://{host}:8090"


def kokoro_is_reachable(cfg: dict[str, Any], *, timeout: float = 3.0) -> bool:
    url = kokoro_url(cfg)
    if not url:
        return False
    try:
        r = requests.get(f"{url}/health", timeout=timeout)
        if not r.ok:
            return False
        data = r.json()
        return bool(data.get("ok", True))
    except (requests.RequestException, ValueError):
        return False


def inspect_kokoro_backend(cfg: dict[str, Any]) -> dict[str, Any]:
    g = _kokoro_config(cfg)
    url = kokoro_url(cfg)
    running = kokoro_is_reachable(cfg) if url else False
    health: dict[str, Any] = {}
    if running and url:
        try:
            health = requests.get(f"{url}/health", timeout=3).json()
        except (requests.RequestException, ValueError):
            health = {}
    return {
        "enabled": bool(g.get("enabled", True)),
        "url": url or None,
        "running": running,
        "default_voice": g.get("voice") or health.get("default_voice"),
        "default_speed": g.get("speed"),
        "voice_count": health.get("voice_count"),
        "gpu_lock": False,
        "note": "CPU Kokoro narrate — OK while Forge or ComfyUI holds the GPU",
        "tools": ["check_kokoro_backend", "list_kokoro_voices", "generate_speech_kokoro"],
        "doc": g.get("doc") or "AUDIO-KOKORO.md",
    }


def list_kokoro_voices(cfg: dict[str, Any]) -> dict[str, Any]:
    url = kokoro_url(cfg)
    if not url:
        raise RuntimeError("kokoro.url not set (and cannot derive from comfyui.url)")
    r = requests.get(f"{url}/v1/voices", timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        "ok": True,
        "url": url,
        "voices": data.get("voices") or [],
        "default": data.get("default") or _kokoro_config(cfg).get("voice"),
    }


def synthesize_kokoro(
    cfg: dict[str, Any],
    text: str,
    *,
    voice: str = "",
    speed: float | None = None,
    output_dir: Path | None = None,
    filename: str = "",
) -> dict[str, Any]:
    """POST /v1/tts → WAV file under outputs/ (+ delivery audio/temp)."""
    g = _kokoro_config(cfg)
    url = kokoro_url(cfg)
    if not url:
        raise RuntimeError("kokoro.url not set — add kokoro.url to config.yaml")
    body = (text or "").strip()
    if not body:
        raise ValueError("text is required")

    voice_id = (voice or str(g.get("voice") or "am_michael")).strip()
    spd = float(speed if speed is not None else g.get("speed") or 0.87)
    timeout = float(g.get("timeout_seconds") or 300)

    r = requests.post(
        f"{url}/v1/tts",
        json={
            "text": body,
            "voice": voice_id,
            "speed": spd,
            "pause_period_s": float(g.get("pause_period_s") or 0.45),
            "pause_comma_s": float(g.get("pause_comma_s") or 0.22),
            "pause_paragraph_s": float(g.get("pause_paragraph_s") or 0.7),
        },
        timeout=timeout,
    )
    r.raise_for_status()

    out_root = output_dir or Path(cfg.get("_root", ".")) / "outputs"
    out_root.mkdir(parents=True, exist_ok=True)
    if filename:
        stem = Path(filename).stem
    else:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", body[:40]).strip("_") or "speech"
        stem = f"kokoro_{slug}"
    dest = out_root / f"{stem}.wav"
    dest.write_bytes(r.content)

    saved = [str(dest)]
    saved, delivered = deliver_files(cfg, saved, bucket="audio")
    return {
        "ok": True,
        "backend": "kokoro",
        "url": url,
        "voice": voice_id,
        "speed": spd,
        "text": body,
        "saved_files": saved,
        "delivered_files": delivered,
        "bytes": len(r.content),
    }
