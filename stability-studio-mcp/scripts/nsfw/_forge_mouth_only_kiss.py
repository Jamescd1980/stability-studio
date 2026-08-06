"""Forge-only mouth refine on raw Wan kiss (no SeedVR, no EBSynth).

Eyes stay from source via soft mouth-ellipse composite after each Forge pass.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import refine_image_forge  # noqa: E402

VIDEO = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\FD_kissing_00133.mp4"
)
WORK = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\forge_refine\kiss_00133_forge_mouth_only"
)
OUT = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\forge_refine\FD_kissing_00133_forge_mouth_d014_3s.mp4"
)

FRAMES = 48
FPS = 16.0
DENOISE = 0.14  # up from 0.10 mouth-sparse probe
SEED = 42

PROMPT = (
    "masterpiece, best quality, anime++, 2girls kissing, lips pressed together, "
    "detailed lips, clean mouth contact, soft lighting, clean lineart"
)
NEGATIVE = (
    "blurry, low quality, cum, semen, facial, bukkake, spit, drool, saliva trail, "
    "excessive saliva, dripping saliva, tongue blob, orange slime, goo, "
    "extra limbs, bad anatomy, watermark, deformed mouth"
)

MASK_CX, MASK_CY = 0.42, 0.40
MASK_RX, MASK_RY = 0.24, 0.16


def extract(n: int) -> list[Path]:
    src = WORK / "src"
    src.mkdir(parents=True, exist_ok=True)
    for old in src.glob("*.png"):
        old.unlink()
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(VIDEO),
            "-vf",
            f"select='lt(n\\,{n})'",
            "-vsync",
            "0",
            str(src / "f%04d.png"),
        ],
        check=True,
        capture_output=True,
    )
    frames = sorted(src.glob("f*.png"))
    print(f"extracted {len(frames)} from raw Wan", flush=True)
    return frames


def mouth_mask(h: int, w: int) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = MASK_CX * w, MASK_CY * h
    rx, ry = MASK_RX * w, MASK_RY * h
    m = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
    return np.clip(m, 0, 1).astype(np.float32)


def composite_mouth(src: Path, forged: Path, dest: Path) -> None:
    s_im = Image.open(src).convert("RGB")
    f_im = Image.open(forged).convert("RGB").resize(s_im.size, Image.Resampling.LANCZOS)
    s = np.asarray(s_im, dtype=np.float32)
    f = np.asarray(f_im, dtype=np.float32)
    m = mouth_mask(s.shape[0], s.shape[1])[:, :, None]
    out = s * (1.0 - m) + f * m
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dest)


def main() -> int:
    cfg = load_config()
    WORK.mkdir(parents=True, exist_ok=True)
    out_dir = WORK / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("o*.png"):
        old.unlink()

    frames = extract(FRAMES)
    for i, fp in enumerate(frames):
        dest = out_dir / f"o{i:04d}.png"
        if dest.is_file() and dest.stat().st_size > 1000:
            print(f"skip {i+1}/{len(frames)}", flush=True)
            continue
        r = refine_image_forge(
            cfg,
            image_path=str(fp),
            prompt=PROMPT,
            negative_prompt=NEGATIVE,
            denoising_strength=DENOISE,
            steps=22,
            cfg_scale=5.0,
            seed=SEED,
            adetailer=False,
            checkpoint="waijfu_alpha.safetensors",
        )
        if not r.get("ok"):
            print(json.dumps(r, indent=2), flush=True)
            return 1
        forged = Path((r.get("saved_files") or [None])[0] or "")
        if not forged.is_file():
            for k in ("path", "output_path", "refined_path", "image_path"):
                if r.get(k):
                    forged = Path(str(r[k]))
                    break
        if not forged.is_file():
            print("missing forge out", list(r.keys()), flush=True)
            return 1
        composite_mouth(fp, forged, dest)
        print(f"forge+mouth {i+1}/{len(frames)} d={DENOISE}", flush=True)

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
    print(
        json.dumps(
            {
                "ok": True,
                "source": "raw_wan",
                "seedvr": False,
                "ebsynth": False,
                "denoise": DENOISE,
                "out": str(OUT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
