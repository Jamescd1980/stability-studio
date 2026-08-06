"""Main-rig face restore via real EBSynth CLI (PatchMatch).

OpenCV still-face alpha paste is NOT EBSynth — dual-face contact motion makes it
trash (frozen key faces over thrusting bodies). Default: fail if ebsynth.exe missing.

Usage:
  python _ebsynth_face_restore.py --video GUIDE.mp4 --key STILL.png --out OUT.mp4
  # throwaway only:
  python _ebsynth_face_restore.py ... --allow-opencv-fallback
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

EBSYNTH_CANDIDATES = [
    Path(r"D:\studio-agent\stability-studio-mcp\tools\ebsynth\ebsynth.exe"),
    Path(r"D:\studio-agent\stability-studio-mcp\tools\ebsynth\bin\ebsynth.exe"),
    Path(r"C:\Program Files\EbSynth\EbSynth.exe"),
]


def find_ebsynth() -> Path | None:
    for p in EBSYNTH_CANDIDATES:
        if p.is_file():
            return p
    which = shutil.which("ebsynth")
    return Path(which) if which else None


def extract_frames(video: Path, frames_dir: Path) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.png"):
        old.unlink()
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vsync",
            "0",
            str(frames_dir / "f%04d.png"),
        ],
        check=True,
        capture_output=True,
    )
    return sorted(frames_dir.glob("f*.png"))


def face_mask(h: int, w: int) -> np.ndarray:
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    face_w = np.clip((0.52 - yy) / 0.12, 0, 1)
    face_w = np.repeat(face_w, w, axis=1)
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    cx = np.exp(-((xx - 0.45) ** 2) / (2 * 0.22**2))
    cx = np.repeat(cx, h, axis=0)
    return np.clip(face_w * (0.55 + 0.45 * cx), 0, 1).astype(np.float32)


def restore_opencv(key: Path, frames: list[Path], out_frames: Path) -> None:
    """Static still-face paste. Probe-only — does not track head motion."""
    print(
        "WARNING: OpenCV face-lock is NOT EBSynth (no PatchMatch). "
        "Do not ship / gate this output as a restore keeper.",
        flush=True,
    )
    out_frames.mkdir(parents=True, exist_ok=True)
    key_im = Image.open(key).convert("RGB")
    # match first frame size
    f0 = Image.open(frames[0]).convert("RGB")
    key_im = key_im.resize(f0.size, Image.Resampling.LANCZOS)
    s = np.asarray(key_im, dtype=np.float32)
    m = face_mask(f0.size[1], f0.size[0])[:, :, None]
    for i, fp in enumerate(frames):
        g = np.asarray(Image.open(fp).convert("RGB"), dtype=np.float32)
        if g.shape[:2] != s.shape[:2]:
            g_im = Image.open(fp).convert("RGB").resize(key_im.size, Image.Resampling.LANCZOS)
            g = np.asarray(g_im, dtype=np.float32)
        blend = g * (1 - m) + s * m
        out = Image.fromarray(np.clip(blend, 0, 255).astype(np.uint8))
        # light smooth on seam
        out = out.filter(ImageFilter.SMOOTH)
        dest = out_frames / f"o{i:04d}.png"
        out.save(dest)
        if i % 10 == 0:
            print(f"  opencv_probe {i+1}/{len(frames)}", flush=True)


def run_ebsynth_cli(exe: Path, key: Path, frames: list[Path], out_frames: Path) -> None:
    """Style=key still; guide source=key, guide target=video frame (jamriska CLI)."""
    out_frames.mkdir(parents=True, exist_ok=True)
    f0 = Image.open(frames[0]).convert("RGB")
    style_path = out_frames.parent / "_style_resized.png"
    Image.open(key).convert("RGB").resize(f0.size, Image.Resampling.LANCZOS).save(style_path)
    for i, guide in enumerate(frames):
        dest = out_frames / f"o{i:04d}.png"
        # -guide needs <source> <target> (not a single path)
        cmd = [
            str(exe),
            "-style",
            str(style_path),
            "-guide",
            str(style_path),
            str(guide),
            "-output",
            str(dest),
            "-backend",
            "cuda",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not dest.is_file():
            cmd_cpu = cmd[:-2] + ["cpu"]  # retry cpu if cuda fails
            r2 = subprocess.run(cmd_cpu, capture_output=True, text=True)
            if r2.returncode != 0 or not dest.is_file():
                raise RuntimeError(
                    f"ebsynth failed frame {i}: {r.stderr or r.stdout} | {r2.stderr or r2.stdout}"
                )
        if i % 5 == 0 or i + 1 == len(frames):
            print(f"  ebsynth {i+1}/{len(frames)}", flush=True)


def encode_video(frames_dir: Path, fps: float, out_mp4: Path) -> None:
    pattern = str(frames_dir / "o%04d.png")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "14",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--key", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--work", type=Path, default=None)
    ap.add_argument("--fps", type=float, default=16.0)
    ap.add_argument(
        "--allow-opencv-fallback",
        action="store_true",
        help="Probe-only static face paste if ebsynth.exe missing. Never ship.",
    )
    args = ap.parse_args()

    work = args.work or args.out.parent / f"_ebsynth_{args.out.stem}"
    guide_dir = work / "guide"
    out_dir = work / "out"
    frames = extract_frames(args.video, guide_dir)
    print(f"frames={len(frames)} work={work}", flush=True)

    exe = find_ebsynth()
    if exe:
        print(f"using EBSynth CLI {exe}", flush=True)
        try:
            run_ebsynth_cli(exe, args.key, frames, out_dir)
        except Exception as exc:
            if not args.allow_opencv_fallback:
                print(
                    f"EBSynth CLI failed ({exc}). "
                    "Refusing OpenCV fallback (use --allow-opencv-fallback for probes only).",
                    flush=True,
                )
                return 2
            print(f"EBSynth CLI failed ({exc}); OpenCV probe fallback", flush=True)
            restore_opencv(args.key, frames, out_dir)
    elif args.allow_opencv_fallback:
        restore_opencv(args.key, frames, out_dir)
    else:
        print(
            "ERROR: ebsynth.exe not found. Place jamriska win64 binary at "
            r"D:\studio-agent\stability-studio-mcp\tools\ebsynth\ebsynth.exe "
            "(PyPI package is a stub). OpenCV face paste is NOT equivalent — "
            "pass --allow-opencv-fallback only for throwaway probes.",
            flush=True,
        )
        return 2

    encode_video(out_dir, args.fps, args.out)
    print(f"wrote {args.out} size={args.out.stat().st_size}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
