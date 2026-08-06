# -*- coding: utf-8 -*-
"""RIFE-ncnn-vulkan frame interpolation worker (main-rig Vulkan / 5060 Ti)."""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _probe_fps(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    if "/" in out:
        num, den = out.split("/", 1)
        if float(den):
            return float(num) / float(den)
    return float(out or 16)


def _count_pngs(folder: Path) -> int:
    return len(list(folder.glob("*.png")))


def interpolate(
    src: Path,
    dest: Path,
    rife_exe: Path,
    *,
    target_fps: float = 24.0,
    model: str = "rife-v4.26",
    crf: int = 17,
    max_frames: int = 0,
) -> dict:
    if not rife_exe.is_file():
        raise FileNotFoundError(f"rife-ncnn-vulkan not found: {rife_exe}")
    model_dir = rife_exe.parent / model
    if not model_dir.is_dir():
        raise FileNotFoundError(f"RIFE model folder missing: {model_dir}")

    src_fps = _probe_fps(src)
    tmp = Path(tempfile.mkdtemp(prefix="wan_rife_"))
    in_frames = tmp / "in"
    out_frames = tmp / "out"
    in_frames.mkdir()
    out_frames.mkdir()
    try:
        extract = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vsync",
            "0",
            str(in_frames / "%08d.png"),
        ]
        subprocess.run(extract, check=True, capture_output=True, text=True)
        n_in = _count_pngs(in_frames)
        if n_in == 0:
            raise RuntimeError("No frames extracted for RIFE")
        if max_frames and n_in > max_frames:
            # keep only first max_frames
            for p in sorted(in_frames.glob("*.png"))[max_frames:]:
                p.unlink()
            n_in = max_frames

        ratio = float(target_fps) / max(src_fps, 1e-6)
        n_out = max(n_in + 1, int(math.ceil(n_in * ratio)))

        rife_cmd = [
            str(rife_exe),
            "-i",
            str(in_frames),
            "-o",
            str(out_frames),
            "-n",
            str(n_out),
            "-m",
            str(model_dir),
        ]
        proc = subprocess.run(rife_cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "")[-2000:]
            raise RuntimeError(f"rife-ncnn-vulkan failed: {err}")

        n_done = _count_pngs(out_frames)
        if n_done < 2:
            raise RuntimeError(f"RIFE produced too few frames: {n_done}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        encode = [
            "ffmpeg",
            "-y",
            "-framerate",
            str(target_fps),
            "-i",
            str(out_frames / "%08d.png"),
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
        subprocess.run(encode, check=True, capture_output=True, text=True)
        if not dest.is_file() or dest.stat().st_size < 500:
            raise RuntimeError(f"RIFE encode produced no usable file: {dest}")

        return {
            "ok": True,
            "method": "rife",
            "model": model,
            "source": str(src),
            "output": str(dest),
            "source_fps": src_fps,
            "target_fps": float(target_fps),
            "frames_in": n_in,
            "frames_out": n_done,
            "rife_exe": str(rife_exe),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="RIFE-ncnn-vulkan video interpolate")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--rife-exe", required=True)
    ap.add_argument("--target-fps", type=float, default=24.0)
    ap.add_argument("--model", default="rife-v4.26")
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()
    try:
        payload = interpolate(
            Path(args.input),
            Path(args.output),
            Path(args.rife_exe),
            target_fps=args.target_fps,
            model=args.model,
            crf=args.crf,
            max_frames=args.max_frames,
        )
        print(json.dumps(payload))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
