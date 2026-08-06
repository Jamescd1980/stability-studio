"""Experiment: Forge img2img each frame of a short clip, then re-encode.

Usage (Forge must already be up on comfybox):
  python _forge_clip_refine_exp.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import refine_image_forge  # noqa: E402

# Input = SeedVR keeper (eyes already good). Forge probe for mouth/tongue detail.
VIDEO = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\seedvr\FD_kissing_00133_seedvr2_1080.mp4"
)
WORK = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\forge_refine\kiss_00133_seedvr_frames"
)
OUT = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\forge_refine\FD_kissing_00133_seedvr_forge_d018_3s.mp4"
)
FRAMES = 48  # 3s @ 16fps
FPS = 16.0
DENOISE = 0.18  # keep eyes; nudge mouth detail
SEED = 42
PROMPT = (
    "masterpiece, best quality, anime++, 2girls kissing, tongue kiss, "
    "detailed mouth, detailed tongue, natural eyes, soft lighting, clean lineart"
)
NEGATIVE = (
    "blurry, low quality, deformed eyes, blank eyes, glowing eyes, "
    "lens flare, eye flare, bright catchlights, sparkle eyes, shiny eyes, "
    "specular highlight in eyes, overexposed eyes, light reflection in eyes, "
    "starburst eyes, glowing pupils, extra limbs, bad anatomy, watermark, "
    "asymmetrical eyes"
)
AD_PROMPT = (
    "natural eyes, soft diffuse lighting on face, detailed mouth, detailed tongue, "
    "no glare"
)
AD_NEGATIVE = (
    "lens flare, eye flare, bright catchlights, sparkle eyes, glowing eyes, "
    "specular eyes, overexposed eyes, starburst"
)


def extract() -> list[Path]:
    src = WORK / "src"
    out = WORK / "forge"
    src.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    for old in src.glob("*.png"):
        old.unlink()
    # first 48 frames
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(VIDEO),
            "-vf",
            f"select='lt(n\\,{FRAMES})'",
            "-vsync",
            "0",
            str(src / "f%04d.png"),
        ],
        check=True,
        capture_output=True,
    )
    frames = sorted(src.glob("f*.png"))
    print(f"extracted {len(frames)} frames -> {src}", flush=True)
    return frames


def main() -> int:
    cfg = load_config()
    frames = extract()
    out_dir = WORK / "forge"
    saved: list[Path] = []
    for i, fp in enumerate(frames):
        dest = out_dir / f"o{i:04d}.png"
        if dest.is_file() and dest.stat().st_size > 1000:
            saved.append(dest)
            print(f"skip existing {i+1}/{len(frames)}", flush=True)
            continue
        r = refine_image_forge(
            cfg,
            image_path=str(fp),
            prompt=PROMPT,
            negative_prompt=NEGATIVE,
            denoising_strength=DENOISE,
            steps=24,
            cfg_scale=5.0,
            seed=SEED,
            adetailer=True,
            ad_prompt=AD_PROMPT,
            ad_negative=AD_NEGATIVE,
            ad_denoising_strength=0.25,
            ad_model="face_yolov8n.pt",
        )
        if not r.get("ok"):
            print(json.dumps(r, indent=2), flush=True)
            return 1
        # copy result to ordered name
        out_path = Path(r.get("saved_files", [None])[0] or r.get("image_path") or "")
        if not out_path.is_file():
            # forge_backend may return different keys
            for k in ("path", "output_path", "refined_path"):
                if r.get(k):
                    out_path = Path(str(r[k]))
                    break
        if not out_path.is_file():
            # search newest in delivery Images
            print("WARN missing out; keys=", list(r.keys()), flush=True)
            return 1
        dest.write_bytes(out_path.read_bytes())
        saved.append(dest)
        print(f"forge {i+1}/{len(frames)} -> {dest.name}", flush=True)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(out_dir / "o%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "14",
            str(OUT),
        ],
        check=True,
        capture_output=True,
    )
    print(json.dumps({"ok": True, "frames": len(saved), "out": str(OUT), "denoise": DENOISE}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
