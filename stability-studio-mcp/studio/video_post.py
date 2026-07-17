"""Post-process video helpers (frame interpolation, etc.)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from studio.output_paths import deliver_files
from studio.video_utils import probe_video


def _ffmpeg_bin(cfg: dict[str, Any] | None = None) -> str:
    if cfg:
        custom = (cfg.get("ffmpeg") or {}).get("path") or (cfg.get("tools") or {}).get("ffmpeg")
        if custom and Path(str(custom)).is_file():
            return str(custom)
    which = shutil.which("ffmpeg")
    if which:
        return which
    return "ffmpeg"


def interpolate_video(
    cfg: dict[str, Any],
    video_path: str | Path,
    *,
    target_fps: float = 24.0,
    method: str = "minterpolate",
    output_dir: Path | None = None,
    crf: int = 18,
) -> dict[str, Any]:
    """
    Upsample frame rate with ffmpeg minterpolate (mi_mode=mci).

    Saves next to the source (or output_dir) as ``{stem}_interp_{fps}fps.mp4``,
    then copies into delivery temp/ when configured.
    """
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video not found: {src}")

    method_key = (method or "minterpolate").strip().lower()
    if method_key not in {"minterpolate", "ffmpeg", "mci"}:
        raise ValueError("method must be 'minterpolate' (ffmpeg mi_mode=mci)")

    fps = float(target_fps)
    if fps < 1 or fps > 120:
        raise ValueError("target_fps must be between 1 and 120")

    info = probe_video(src)
    src_fps = float(info.get("fps") or 16)

    out_root = output_dir or src.parent
    out_root.mkdir(parents=True, exist_ok=True)
    dest = out_root / f"{src.stem}_interp_{int(fps)}fps.mp4"

    # mi_mode=mci = motion-compensated interpolation (closest to FILM/RIFE quality in stock ffmpeg)
    vf = f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    cmd = [
        _ffmpeg_bin(cfg),
        "-y",
        "-i",
        str(src),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        str(int(crf)),
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or str(exc))[-2000:]
        raise RuntimeError(f"ffmpeg interpolate failed: {err}") from exc

    if not dest.is_file() or dest.stat().st_size < 500:
        raise RuntimeError(f"Interpolate produced no usable file: {dest}")

    saved = [str(dest)]
    saved, delivered = deliver_files(cfg, saved, bucket="temp")
    out_info = probe_video(dest)
    return {
        "ok": True,
        "method": "minterpolate",
        "source": str(src),
        "source_fps": src_fps,
        "target_fps": fps,
        "saved_files": saved,
        "delivered_files": delivered,
        "probe": out_info,
    }
