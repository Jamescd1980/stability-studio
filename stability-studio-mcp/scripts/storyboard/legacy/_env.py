"""Config-driven paths for legacy storyboard runners."""

from __future__ import annotations

from pathlib import Path

from studio.config import load_config


def _comfy_root() -> Path:
    cfg = load_config()
    return Path(cfg["stability_matrix"]["packages"]["comfyui"])


def comfy_python() -> Path:
    return _comfy_root() / "venv" / "Scripts" / "python.exe"


def imageio_ffmpeg() -> Path:
    return (
        _comfy_root()
        / "venv"
        / "Lib"
        / "site-packages"
        / "imageio_ffmpeg"
        / "binaries"
        / "ffmpeg-win-x86_64-v7.1.exe"
    )
