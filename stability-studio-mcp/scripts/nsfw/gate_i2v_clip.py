"""Quick identity gate for Wan I2V chain links.

Compares start still vs extracted frames (MSE). Exit 0 if f0 ok; prints mid/last.
Does not approve — human still decides. Use before chaining.

Example:
  py -3 gate_i2v_clip.py --start still.png --video clip.mp4
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def _frame(video: Path, n: int, dest: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"select=eq(n\\,{n})",
            "-vframes",
            "1",
            "-q:v",
            "2",
            str(dest),
        ],
        capture_output=True,
        check=False,
    )


def _mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2))


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate I2V clip vs start still (MSE)")
    ap.add_argument("--start", required=True, type=Path)
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--f0-max", type=float, default=80.0, help="max total MSE for frame 0")
    args = ap.parse_args()

    if not args.start.is_file() or not args.video.is_file():
        print("missing start or video", file=sys.stderr)
        return 2

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            str(args.video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    nframes = 65
    raw = (probe.stdout or "").strip().splitlines()
    if raw and raw[0].isdigit():
        nframes = int(raw[0])
    last_i = max(0, nframes - 1)
    mid_i = nframes // 2
    one_s = min(16, last_i)

    start = np.asarray(Image.open(args.start).convert("RGB").resize((720, 720)))
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        scores = {}
        for label, idx in (("f0", 0), ("t1s", one_s), ("mid", mid_i), ("last", last_i)):
            dest = td_path / f"{label}.png"
            _frame(args.video, idx, dest)
            if not dest.is_file():
                print(f"extract fail {label} n={idx}")
                return 2
            im = np.asarray(Image.open(dest).convert("RGB").resize((720, 720)))
            scores[label] = _mse(start, im)
            print(f"{label} n={idx} mse={scores[label]:.1f}")

    ok_f0 = scores["f0"] <= args.f0_max
    # Soft warn if 1s or mid exploded vs f0
    warn = scores["t1s"] > max(500.0, scores["f0"] * 20) or scores["mid"] > max(
        800.0, scores["f0"] * 30
    )
    print(
        "GATE",
        "PASS_F0" if ok_f0 else "FAIL_F0",
        "WARN_DRIFT" if warn else "ok_drift",
        f"(f0_max={args.f0_max})",
    )
    if not ok_f0:
        return 1
    if warn:
        return 3  # f0 ok but drift — do not chain without human look
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
