"""Local splice helpers for Wan clips (concat, ping-pong, pose-matched loop)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from studio.output_paths import deliver_files
from studio.video_utils import concat_videos, probe_video

ROOT = Path(__file__).resolve().parents[1]


def _ffmpeg() -> str:
    return "ffmpeg"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def concat_video_clips(
    cfg: dict[str, Any],
    paths: list[str],
    *,
    output_path: str = "",
) -> dict[str, Any]:
    if len(paths) < 2:
        raise ValueError("Need at least two video paths to concat")
    srcs = [Path(p).expanduser().resolve() for p in paths]
    for s in srcs:
        if not s.is_file():
            raise FileNotFoundError(s)
    if output_path:
        dest = Path(output_path).expanduser().resolve()
    else:
        dest = srcs[0].parent / f"{srcs[0].stem}_concat.mp4"
    concat_videos(srcs, dest)
    saved, delivered = deliver_files(cfg, [str(dest)], bucket="temp")
    return {
        "ok": True,
        "saved_files": saved,
        "delivered_files": delivered,
        "probe": probe_video(Path(saved[0])),
        "inputs": [str(s) for s in srcs],
    }


def splice_pingpong(
    cfg: dict[str, Any],
    video_path: str,
    *,
    output_path: str = "",
    then_forward: bool = True,
) -> dict[str, Any]:
    """
    D-style extend: forward + reverse (+ optional forward again).

    Re-encodes reverse for reliable concat.
    """
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    work = src.parent / f"_{src.stem}_pingpong_work"
    work.mkdir(parents=True, exist_ok=True)
    fwd = work / "fwd.mp4"
    rev = work / "rev.mp4"
    # normalize encode
    _run(
        [
            _ffmpeg(),
            "-y",
            "-i",
            str(src),
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(fwd),
        ]
    )
    _run(
        [
            _ffmpeg(),
            "-y",
            "-i",
            str(fwd),
            "-vf",
            "reverse",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(rev),
        ]
    )
    parts = [fwd, rev]
    if then_forward:
        parts.append(fwd)
    dest = (
        Path(output_path).expanduser().resolve()
        if output_path
        else src.parent / f"{src.stem}_pingpong.mp4"
    )
    concat_videos(parts, dest)
    saved, delivered = deliver_files(cfg, [str(dest)], bucket="temp")
    return {
        "ok": True,
        "mode": "pingpong_then_forward" if then_forward else "pingpong",
        "saved_files": saved,
        "delivered_files": delivered,
        "probe": probe_video(Path(saved[0])),
        "source": str(src),
    }


def splice_crossfade_loop(
    cfg: dict[str, Any],
    video_path: str,
    *,
    fade_sec: float = 0.25,
    output_path: str = "",
) -> dict[str, Any]:
    """Soft E-style loop: two copies with xfade at the join."""
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    info = probe_video(src)
    dur = float(info["duration_sec"])
    fade = max(0.05, min(float(fade_sec), dur / 3))
    offset = max(0.01, dur - fade)
    dest = (
        Path(output_path).expanduser().resolve()
        if output_path
        else src.parent / f"{src.stem}_crossfade_loop.mp4"
    )
    _run(
        [
            _ffmpeg(),
            "-y",
            "-i",
            str(src),
            "-i",
            str(src),
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=fade:duration={fade}:offset={offset:.4f}",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ]
    )
    saved, delivered = deliver_files(cfg, [str(dest)], bucket="temp")
    return {
        "ok": True,
        "mode": "crossfade_loop",
        "fade_sec": fade,
        "saved_files": saved,
        "delivered_files": delivered,
        "probe": probe_video(Path(saved[0])),
        "source": str(src),
    }


def splice_pose_matched_loop(
    cfg: dict[str, Any],
    video_path: str,
    *,
    target_sec: float = 19.0,
    rewind_max: int = 12,
    output_path: str = "",
) -> dict[str, Any]:
    """Pose-matched D-style loop (rewind up to N frames for quieter joins)."""
    from studio.video_upscale import post_python

    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    dest = (
        Path(output_path).expanduser().resolve()
        if output_path
        else src.parent / f"{src.stem}_pose_loop_{int(target_sec)}s.mp4"
    )
    py = post_python(cfg)
    worker = ROOT / "scripts" / "local_post" / "pose_match_loop.py"
    cmd = [
        str(py),
        str(worker),
        "--input",
        str(src),
        "--output",
        str(dest),
        "--target-sec",
        str(float(target_sec)),
        "--rewind-max",
        str(int(rewind_max)),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2500:]
        raise RuntimeError(f"pose_matched_loop failed: {err}")
    payload = json.loads((proc.stdout or "").strip().splitlines()[-1])
    saved, delivered = deliver_files(cfg, [str(dest)], bucket="temp")
    payload["saved_files"] = saved
    payload["delivered_files"] = delivered
    payload["probe"] = probe_video(Path(saved[0]))
    return payload
