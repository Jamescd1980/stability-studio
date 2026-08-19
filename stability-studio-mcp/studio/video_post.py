"""Post-process video helpers (frame interpolation, local CUDA polish, etc.)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from studio.output_paths import deliver_files
from studio.video_upscale import (
    ROOT,
    post_python,
    resolve_rife_exe,
    resolve_seedvr2_paths,
    upscale_video_local,
    upscale_video_seedvr2,
)
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


def _interpolate_minterpolate(
    cfg: dict[str, Any],
    src: Path,
    dest: Path,
    *,
    fps: float,
    crf: int,
) -> dict[str, Any]:
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
    return {"method": "minterpolate"}


def _interpolate_rife(
    cfg: dict[str, Any],
    src: Path,
    dest: Path,
    *,
    fps: float,
    crf: int,
    rife_model: str = "",
    max_frames: int = 0,
) -> dict[str, Any]:
    pc = dict(cfg.get("local_post") or {})
    rife_exe = resolve_rife_exe(cfg)
    model = (rife_model or pc.get("rife_model") or "rife-v4.26").strip()
    worker = ROOT / "scripts" / "general" / "local_post" / "rife_interpolate.py"
    # Thin ffmpeg+rife driver — use .venv-post python (stdlib only needed).
    try:
        py = str(post_python(cfg))
    except FileNotFoundError:
        py = shutil.which("python") or sys.executable
    cmd = [
        py,
        str(worker),
        "--input",
        str(src),
        "--output",
        str(dest),
        "--rife-exe",
        str(rife_exe),
        "--target-fps",
        str(float(fps)),
        "--model",
        model,
        "--crf",
        str(int(crf)),
        "--max-frames",
        str(int(max_frames)),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2500:]
        raise RuntimeError(f"RIFE interpolate failed: {err}")
    line = (proc.stdout or "").strip().splitlines()[-1]
    payload = json.loads(line)
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error") or "RIFE failed")
    return payload


def interpolate_video(
    cfg: dict[str, Any],
    video_path: str | Path,
    *,
    target_fps: float = 24.0,
    method: str = "minterpolate",
    output_dir: Path | None = None,
    crf: int = 18,
    rife_model: str = "",
    max_frames: int = 0,
) -> dict[str, Any]:
    """
    Upsample frame rate.

    Methods:
      - minterpolate / ffmpeg / mci — stock ffmpeg MCI (CPU, legacy)
      - rife — RIFE-ncnn-vulkan on main-rig GPU (quality path)
    """
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video not found: {src}")

    method_key = (method or "minterpolate").strip().lower()
    if method_key not in {"minterpolate", "ffmpeg", "mci", "rife", "rife-ncnn", "rife_ncnn"}:
        raise ValueError("method must be 'minterpolate' or 'rife'")

    fps = float(target_fps)
    if fps < 1 or fps > 120:
        raise ValueError("target_fps must be between 1 and 120")

    info = probe_video(src)
    src_fps = float(info.get("fps") or 16)

    out_root = output_dir or src.parent
    out_root.mkdir(parents=True, exist_ok=True)
    tag = "rife" if method_key.startswith("rife") else "interp"
    dest = out_root / f"{src.stem}_{tag}_{int(fps)}fps.mp4"

    if method_key.startswith("rife"):
        detail = _interpolate_rife(
            cfg,
            src,
            dest,
            fps=fps,
            crf=crf,
            rife_model=rife_model,
            max_frames=max_frames,
        )
        used = "rife"
    else:
        detail = _interpolate_minterpolate(cfg, src, dest, fps=fps, crf=crf)
        used = "minterpolate"

    if not dest.is_file() or dest.stat().st_size < 500:
        raise RuntimeError(f"Interpolate produced no usable file: {dest}")

    saved = [str(dest)]
    saved, delivered = deliver_files(cfg, saved, bucket="temp")
    out_info = probe_video(dest)
    return {
        "ok": True,
        "method": used,
        "source": str(src),
        "source_fps": src_fps,
        "target_fps": fps,
        "saved_files": saved,
        "delivered_files": delivered,
        "probe": out_info,
        "detail": detail,
    }


def polish_wan_video(
    cfg: dict[str, Any],
    video_path: str | Path,
    *,
    target_fps: float = 24.0,
    upscale_model: str = "anime_sharp_2x",
    skip_interpolate: bool = False,
    skip_upscale: bool = False,
    crf: int = 17,
    interpolate_method: str = "minterpolate",
) -> dict[str, Any]:
    """
    Main-rig delivery polish: interpolate then CUDA upscale (AnimeSharp path).

    Generate/splice on comfybox first; run this on the locked master MP4.
    For RIFE+SeedVR2 quality path use polish_wan_best().
    """
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video not found: {src}")

    steps: list[dict[str, Any]] = []
    current = src

    if not skip_interpolate:
        interp = interpolate_video(
            cfg,
            current,
            target_fps=target_fps,
            method=interpolate_method,
            output_dir=current.parent,
            crf=crf,
        )
        steps.append({"step": "interpolate", **interp})
        current = Path(interp["saved_files"][0])

    if not skip_upscale:
        up = upscale_video_local(
            cfg,
            current,
            model=upscale_model,
            output_dir=current.parent,
            crf=crf,
        )
        steps.append({"step": "upscale", **up})
        current = Path(up["saved_files"][0])

    return {
        "ok": True,
        "source": str(src),
        "final": str(current),
        "saved_files": [str(current)],
        "probe": probe_video(current),
        "steps": steps,
        "path": "legacy_animesharp",
        "note": "Interp (minterpolate or rife) + AnimeSharp on 5060 Ti via .venv-post",
    }


def polish_wan_best(
    cfg: dict[str, Any],
    video_path: str | Path,
    *,
    target_fps: float = 24.0,
    skip_interpolate: bool = False,
    skip_upscale: bool = False,
    crf: int = 17,
    rife_model: str = "",
    seedvr2_resolution: int = 0,
    seedvr2_batch_size: int = 0,
    seedvr2_blocks_to_swap: int = -1,
    max_frames: int = 0,
) -> dict[str, Any]:
    """
    Quality polish path: RIFE-ncnn → SeedVR2 3B FP8 (16GB-safe defaults).

    Order: lock cut → RIFE → SeedVR2. AnimeSharp remains available via polish_wan_video.
    """
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video not found: {src}")

    # Fail fast if best stack missing
    resolve_rife_exe(cfg)
    resolve_seedvr2_paths(cfg)

    steps: list[dict[str, Any]] = []
    current = src
    pc = dict(cfg.get("local_post") or {})

    if not skip_interpolate:
        interp = interpolate_video(
            cfg,
            current,
            target_fps=target_fps,
            method="rife",
            output_dir=current.parent,
            crf=crf,
            rife_model=rife_model or str(pc.get("rife_model") or "rife-v4.26"),
            max_frames=max_frames,
        )
        steps.append({"step": "interpolate_rife", **interp})
        current = Path(interp["saved_files"][0])

    if not skip_upscale:
        up = upscale_video_seedvr2(
            cfg,
            current,
            output_dir=current.parent,
            resolution=seedvr2_resolution or int(pc.get("seedvr2_resolution") or 1080),
            batch_size=seedvr2_batch_size or int(pc.get("seedvr2_batch_size") or 5),
            blocks_to_swap=(
                seedvr2_blocks_to_swap
                if seedvr2_blocks_to_swap >= 0
                else int(pc.get("seedvr2_blocks_to_swap") or 16)
            ),
            load_cap=max_frames,
        )
        steps.append({"step": "upscale_seedvr2", **up})
        current = Path(up["saved_files"][0])

    return {
        "ok": True,
        "source": str(src),
        "final": str(current),
        "saved_files": [str(current)],
        "probe": probe_video(current),
        "steps": steps,
        "path": "best_free",
        "note": (
            "Best free local polish on 5060 Ti 16GB: RIFE-ncnn-vulkan → "
            "SeedVR2 3B FP8 (BlockSwap+VAE tile). AnimeSharp = polish_wan_video fallback."
        ),
    }
