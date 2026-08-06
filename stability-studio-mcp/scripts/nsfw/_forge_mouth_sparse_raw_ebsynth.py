"""Mouth-only sparse Forge on raw Wan → EBSynth (no SeedVR).

Keys every 4th frame @ d~0.15; eyes stay source via mouth-ellipse composite.
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
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\forge_refine\kiss_00133_mouth_sparse_raw"
)
OUT = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\forge_refine\FD_kissing_00133_forge_mouth_sparse_ebsynth_d015.mp4"
)
EBSYNTH = Path(r"D:\studio-agent\stability-studio-mcp\tools\ebsynth\ebsynth.exe")

FRAMES = 48
KEY_EVERY = 4
FPS = 16.0
DENOISE = 0.15
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


def extract_guide(n: int) -> list[Path]:
    guide = WORK / "guide"
    guide.mkdir(parents=True, exist_ok=True)
    for old in guide.glob("*.png"):
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
            str(guide / "g%04d.png"),
        ],
        check=True,
        capture_output=True,
    )
    frames = sorted(guide.glob("g*.png"))
    print(f"guide (raw Wan): {len(frames)}", flush=True)
    return frames


def mouth_mask(h: int, w: int) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = MASK_CX * w, MASK_CY * h
    rx, ry = MASK_RX * w, MASK_RY * h
    m = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
    return np.clip(m, 0, 1).astype(np.float32)


def composite_mouth(guide: Path, forged: Path, dest: Path) -> None:
    g_im = Image.open(guide).convert("RGB")
    f_im = Image.open(forged).convert("RGB").resize(g_im.size, Image.Resampling.LANCZOS)
    g = np.asarray(g_im, dtype=np.float32)
    f = np.asarray(f_im, dtype=np.float32)
    m = mouth_mask(g.shape[0], g.shape[1])[:, :, None]
    out = g * (1.0 - m) + f * m
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dest)


def forge_keys(guide: list[Path]) -> dict[int, Path]:
    cfg = load_config()
    raw_dir = WORK / "forge_raw"
    key_dir = WORK / "forge_keys_mouth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    key_dir.mkdir(parents=True, exist_ok=True)

    key_idxs = list(range(0, len(guide), KEY_EVERY))
    if key_idxs[-1] != len(guide) - 1:
        key_idxs.append(len(guide) - 1)

    forged: dict[int, Path] = {}
    for i, idx in enumerate(key_idxs):
        dest = key_dir / f"k{idx:04d}.png"
        if dest.is_file() and dest.stat().st_size > 1000:
            forged[idx] = dest
            print(f"skip key {i+1}/{len(key_idxs)} n={idx}", flush=True)
            continue

        raw = raw_dir / f"r{idx:04d}.png"
        if not (raw.is_file() and raw.stat().st_size > 1000):
            r = refine_image_forge(
                cfg,
                image_path=str(guide[idx]),
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
                raise RuntimeError(f"forge failed n={idx}")
            out_path = Path((r.get("saved_files") or [None])[0] or "")
            if not out_path.is_file():
                for k in ("path", "output_path", "refined_path", "image_path"):
                    if r.get(k):
                        out_path = Path(str(r[k]))
                        break
            if not out_path.is_file():
                raise RuntimeError(f"no forge out n={idx}")
            raw.write_bytes(out_path.read_bytes())

        composite_mouth(guide[idx], raw, dest)
        forged[idx] = dest
        print(f"mouth key {i+1}/{len(key_idxs)} n={idx} d={DENOISE}", flush=True)
    return forged


def nearest_key(idx: int, keys: list[int]) -> int:
    return min(keys, key=lambda k: (abs(k - idx), k))


def ebsynth_propagate(guide: list[Path], forged: dict[int, Path]) -> list[Path]:
    if not EBSYNTH.is_file():
        raise FileNotFoundError(str(EBSYNTH))
    out_dir = WORK / "ebsynth"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("o*.png"):
        old.unlink()
    keys = sorted(forged)
    outs: list[Path] = []
    for i, g in enumerate(guide):
        dest = out_dir / f"o{i:04d}.png"
        k = nearest_key(i, keys)
        cmd = [
            str(EBSYNTH),
            "-style",
            str(forged[k]),
            "-guide",
            str(guide[k]),
            str(g),
            "-output",
            str(dest),
            "-backend",
            "cuda",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not dest.is_file():
            cmd[-1] = "cpu"
            r2 = subprocess.run(cmd, capture_output=True, text=True)
            if r2.returncode != 0 or not dest.is_file():
                raise RuntimeError(f"ebsynth i={i}: {(r2.stderr or r.stderr or '')[-600:]}")
        outs.append(dest)
        if i % 4 == 0 or i + 1 == len(guide):
            print(f"ebsynth {i+1}/{len(guide)} (key={k})", flush=True)
    return outs


def encode(frames: list[Path]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(frames[0].parent / "o%04d.png")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            pattern,
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
                "denoise": DENOISE,
                "key_every": KEY_EVERY,
                "out": str(OUT),
            },
            indent=2,
        )
    )


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    # fresh keys this run
    for sub in ("forge_raw", "forge_keys_mouth", "ebsynth"):
        d = WORK / sub
        if d.is_dir():
            for p in d.glob("*"):
                if p.is_file():
                    p.unlink()
    guide = extract_guide(FRAMES)
    forged = forge_keys(guide)
    outs = ebsynth_propagate(guide, forged)
    encode(outs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
