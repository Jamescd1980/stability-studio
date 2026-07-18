# -*- coding: utf-8 -*-
"""Pose-matched ping-pong loop builder (D-style) for Wan clips."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _probe(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=nb_frames,r_frame_rate,duration",
        "-of",
        "json",
        str(path),
    ]
    data = json.loads(subprocess.check_output(cmd, text=True))
    stream = (data.get("streams") or [{}])[0]
    fps = 16.0
    rate = stream.get("r_frame_rate", "16/1")
    if "/" in str(rate):
        num, den = str(rate).split("/", 1)
        if float(den):
            fps = float(num) / float(den)
    dur = float(stream.get("duration") or 0)
    frames = stream.get("nb_frames")
    count = int(frames) if frames not in (None, "N/A") else max(1, int(round(dur * fps)))
    return {"fps": fps, "duration_sec": dur, "frame_count": count}


def _gray(path: Path, size: int = 96) -> np.ndarray:
    arr = np.asarray(
        Image.open(path).convert("L").resize((size, size), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    return arr - arr.mean()


def _best_points(frames: list[Path], half_idx: int, rewind_max: int) -> tuple[int, int, float]:
    half_idx = min(max(half_idx, rewind_max + 2), len(frames) - 2)
    ends = list(range(max(rewind_max, half_idx - rewind_max), half_idx + 1))
    starts = list(range(0, min(rewind_max + 10, half_idx // 3)))
    feats = {i: _gray(frames[i]) for i in set(starts + ends)}
    best = (0, half_idx, 1e18)
    for s in starts:
        fs = feats[s]
        for e in ends:
            if e - s < 24:
                continue
            err = float(np.mean((fs - feats[e]) ** 2))
            if err < best[2]:
                best = (s, e, err)
    return best


def _frames_to_mp4(frames: list[Path], dest: Path, fps: float) -> None:
    tmp = dest.parent / f"_{dest.stem}_seq"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        for i, fr in enumerate(frames, start=1):
            (tmp / f"s_{i:04d}.png").write_bytes(fr.read_bytes())
        _run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-i",
                str(tmp / "s_%04d.png"),
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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _concat(paths: list[Path], dest: Path) -> None:
    list_file = dest.with_suffix(".txt")
    list_file.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in paths),
        encoding="utf-8",
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(dest),
        ]
    )


def build_loop(
    src: Path,
    dest: Path,
    *,
    target_sec: float = 19.0,
    rewind_max: int = 12,
) -> dict:
    info = _probe(src)
    fps = float(info["fps"])
    work = Path(tempfile.mkdtemp(prefix="pose_loop_"))
    try:
        frames_dir = work / "frames"
        frames_dir.mkdir()
        _run(["ffmpeg", "-y", "-i", str(src), str(frames_dir / "f_%04d.png")])
        frames = sorted(frames_dir.glob("f_*.png"))
        if len(frames) < 32:
            raise RuntimeError(f"Not enough frames in {src}")
        half = len(frames) // 2
        start_i, end_i, err = _best_points(frames, half, rewind_max)
        segment = frames[start_i : end_i + 1]
        fwd = work / "fwd.mp4"
        rev = work / "rev.mp4"
        _frames_to_mp4(segment, fwd, fps)
        _frames_to_mp4(list(reversed(segment[1:-1])), rev, fps)

        parts: list[Path] = []
        dur = 0.0
        cycle_i = 0
        while dur < target_sec - 0.05 and cycle_i < 30:
            chunk = [fwd, rev] if cycle_i % 2 == 0 else [fwd]
            for c in chunk:
                parts.append(c)
                pinfo = _probe(c)
                dur += float(pinfo["duration_sec"])
                if dur >= target_sec - 0.05:
                    break
            cycle_i += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        _concat(parts, dest)
        out = _probe(dest)
        return {
            "ok": True,
            "source": str(src),
            "dest": str(dest),
            "duration_sec": out["duration_sec"],
            "start_frame": start_i,
            "end_frame": end_i,
            "half_frame": half,
            "rewind_frames": half - end_i,
            "match_mse": err,
            "parts": len(parts),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--target-sec", type=float, default=19.0)
    ap.add_argument("--rewind-max", type=int, default=12)
    args = ap.parse_args()
    print(
        json.dumps(
            build_loop(
                Path(args.input),
                Path(args.output),
                target_sec=args.target_sec,
                rewind_max=args.rewind_max,
            )
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
