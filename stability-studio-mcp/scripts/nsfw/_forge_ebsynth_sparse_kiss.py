"""Option A: Forge every Nth frame (low denoise, no AD) → EBSynth onto SeedVR guide.

Temporal motion stays SeedVR; sparse Forge keys carry mouth detail without per-frame flicker.
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

VIDEO = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\seedvr\FD_kissing_00133_seedvr2_1080.mp4"
)
WORK = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\forge_refine\kiss_00133_sparse"
)
OUT = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work\forge_refine\FD_kissing_00133_seedvr_forge_sparse_ebsynth.mp4"
)
EBSYNTH = Path(r"D:\studio-agent\stability-studio-mcp\tools\ebsynth\ebsynth.exe")

FRAMES = 48  # first 3s @ 16fps
KEY_EVERY = 4
FPS = 16.0
DENOISE = 0.10
SEED = 42

PROMPT = (
    "masterpiece, best quality, anime++, 2girls kissing, lips touching, "
    "subtle tongue, detailed mouth, purple eyes, blue eyes, soft lighting, clean lineart"
)
NEGATIVE = (
    "blurry, low quality, deformed eyes, blank eyes, glowing eyes, brown eyes, "
    "amber eyes, hazel eyes, red eyes, lens flare, eye flare, bright catchlights, "
    "sparkle eyes, cum, semen, facial, bukkake, spit, drool, saliva trail, "
    "excessive saliva, dripping saliva, extra limbs, bad anatomy, watermark"
)


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
    print(f"guide frames: {len(frames)}", flush=True)
    return frames


def forge_keys(guide: list[Path]) -> dict[int, Path]:
    cfg = load_config()
    keys_dir = WORK / "forge_keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    key_idxs = list(range(0, len(guide), KEY_EVERY))
    if key_idxs[-1] != len(guide) - 1:
        key_idxs.append(len(guide) - 1)
    forged: dict[int, Path] = {}
    for i, idx in enumerate(key_idxs):
        dest = keys_dir / f"k{idx:04d}.png"
        if dest.is_file() and dest.stat().st_size > 1000:
            forged[idx] = dest
            print(f"skip forge key {i+1}/{len(key_idxs)} n={idx}", flush=True)
            continue
        r = refine_image_forge(
            cfg,
            image_path=str(guide[idx]),
            prompt=PROMPT,
            negative_prompt=NEGATIVE,
            denoising_strength=DENOISE,
            steps=20,
            cfg_scale=5.0,
            seed=SEED,
            adetailer=False,
            checkpoint="waijfu_alpha.safetensors",
        )
        if not r.get("ok"):
            print(json.dumps(r, indent=2), flush=True)
            raise RuntimeError(f"forge failed at frame {idx}")
        out_path = Path((r.get("saved_files") or [None])[0] or "")
        if not out_path.is_file():
            for k in ("path", "output_path", "refined_path", "image_path"):
                if r.get(k):
                    out_path = Path(str(r[k]))
                    break
        if not out_path.is_file():
            raise RuntimeError(f"no forge output for frame {idx}: {list(r.keys())}")
        dest.write_bytes(out_path.read_bytes())
        forged[idx] = dest
        print(f"forge key {i+1}/{len(key_idxs)} n={idx} -> {dest.name}", flush=True)
    return forged


def nearest_key(idx: int, keys: list[int]) -> int:
    return min(keys, key=lambda k: (abs(k - idx), k))


def ebsynth_propagate(guide: list[Path], forged: dict[int, Path]) -> list[Path]:
    if not EBSYNTH.is_file():
        raise FileNotFoundError(f"ebsynth missing: {EBSYNTH}")
    out_dir = WORK / "ebsynth"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("o*.png"):
        old.unlink()
    keys = sorted(forged)
    outs: list[Path] = []
    for i, g in enumerate(guide):
        dest = out_dir / f"o{i:04d}.png"
        k = nearest_key(i, keys)
        style = forged[k]
        guide_src = guide[k]
        # style=forged key; guide maps original-at-key → original-at-i
        cmd = [
            str(EBSYNTH),
            "-style",
            str(style),
            "-guide",
            str(guide_src),
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
                raise RuntimeError(
                    f"ebsynth failed i={i} key={k}: {(r2.stderr or r.stderr or '')[-800:]}"
                )
        outs.append(dest)
        if i % 4 == 0 or i == len(guide) - 1:
            print(f"ebsynth {i+1}/{len(guide)} (key={k})", flush=True)
    return outs


def encode(frames: list[Path]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # frames already o0000.png sequential
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
    print(json.dumps({"ok": True, "keys": KEY_EVERY, "denoise": DENOISE, "out": str(OUT)}, indent=2))


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    guide = extract_guide(FRAMES)
    if len(guide) < 2:
        raise RuntimeError("not enough guide frames")
    forged = forge_keys(guide)
    outs = ebsynth_propagate(guide, forged)
    encode(outs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
