"""Try hard-cut vs crossfade joins between Original Orla and Passable."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ORIG = Path(r"c:\Users\Creel\Downloads\Original Orla clip.mp4")
PAS = Path(r"c:\Users\Creel\Downloads\Passable.mp4")
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Orla\_work")
WORK = Path(r"D:\ComfyBox Images and Videos\Video\Orla\drafts")


def run(cmd: list[str]) -> int:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL", cmd[:8], (r.stderr or "")[-600:])
    return r.returncode


def join_mse(a: Path, b: Path, tag: str) -> float:
    fa = OUT_DIR / f"_joinA_{tag}.png"
    fb = OUT_DIR / f"_joinB_{tag}.png"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-sseof",
            "-0.05",
            "-i",
            str(a),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(fa),
        ]
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-ss",
            "0",
            "-i",
            str(b),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(fb),
        ]
    )
    ia = np.asarray(Image.open(fa).convert("RGB").resize((960, 540)), dtype=np.float32)
    ib = np.asarray(Image.open(fb).convert("RGB").resize((960, 540)), dtype=np.float32)
    return float(np.mean((ia - ib) ** 2))


def hard_concat(pas1080: Path, a_end: float, b_start: float, name: str) -> Path:
    a = OUT_DIR / f"_a_{name}.mp4"
    b = OUT_DIR / f"_b_{name}.mp4"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(ORIG),
            "-t",
            str(a_end),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "17",
            "-r",
            "24",
            "-an",
            str(a),
        ]
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-ss",
            str(b_start),
            "-i",
            str(pas1080),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "17",
            "-r",
            "24",
            "-an",
            str(b),
        ]
    )
    lst = OUT_DIR / f"_list_{name}.txt"
    # ffmpeg concat demuxer wants escaped single quotes on Windows paths carefully
    lst.write_text(
        f"file '{a.resolve().as_posix()}'\nfile '{b.resolve().as_posix()}'\n",
        encoding="utf-8",
    )
    dest = WORK / f"orla_splice_hard_{name}.mp4"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(dest),
        ]
    )
    mse = join_mse(a, b, name)
    print(f"HARD {name}: A..{a_end} | B@{b_start}..  join_mse={mse:.1f} -> {dest}")
    return dest


def xfade(pas1080: Path, a_end: float, b_start: float, fade: float, name: str) -> Path:
    b = OUT_DIR / f"_bx_{name}.mp4"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-ss",
            str(b_start),
            "-i",
            str(pas1080),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "17",
            "-r",
            "24",
            "-an",
            str(b),
        ]
    )
    offset = max(0.0, a_end - fade)
    dest = WORK / f"orla_splice_xfade_{name}.mp4"
    fc = (
        f"[0:v]trim=0:{a_end},setpts=PTS-STARTPTS[v0];"
        f"[1:v]setpts=PTS-STARTPTS[v1];"
        f"[v0][v1]xfade=transition=fade:duration={fade}:offset={offset}[v]"
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(ORIG),
            "-i",
            str(b),
            "-filter_complex",
            fc,
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "17",
            "-r",
            "24",
            "-an",
            str(dest),
        ]
    )
    print(f"XFADE {name}: A..{a_end} fade={fade}s B@{b_start} -> {dest} ok={dest.is_file()}")
    return dest


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    pas1080 = OUT_DIR / "passable_1080.mp4"
    print("Upscale Passable -> 1080p…")
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(PAS),
            "-vf",
            "scale=1920:1080:flags=lanczos",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "17",
            "-r",
            "24",
            "-an",
            str(pas1080),
        ]
    )
    hard_concat(pas1080, 5.0, 4.5, "a5p45")
    hard_concat(pas1080, 5.5, 5.25, "a55p525")
    hard_concat(pas1080, 6.0, 4.5, "a6p45")
    xfade(pas1080, 5.0, 4.5, 0.35, "a5p45_f35")
    xfade(pas1080, 5.5, 5.25, 0.5, "a55p525_f50")
    xfade(pas1080, 5.0, 4.5, 0.6, "a5p45_f60")
    # dissolve-ish longer softener
    xfade(pas1080, 5.25, 4.75, 0.75, "a525p475_f75")
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
