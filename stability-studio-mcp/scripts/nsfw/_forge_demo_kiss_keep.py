"""Multi-pass Forge demo on FD_kissing_KEEP — quality then eyes-only."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import forge_is_reachable, forge_url, refine_image_forge  # noqa: E402

SRC = Path(
    r"D:\ComfyBox Images and Videos\Images\proof_queue\fern_darkness\KEEPERS\FD_kissing_KEEP.png"
)
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\proof_queue\fern_darkness\KEEPERS\_forge_demo"
)

PROMPT = (
    "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
    "2girls, fern, darkness, blonde ponytail, purple hair, nude, tongue kiss, "
    "detailed lips, detailed eyes, purple eyes, blue eyes, soft lamp light, "
    "bedroom loft, wet skin, clean lineart"
)
NEG = (
    "lowres, blurry, deformed face, bad anatomy, cum, semen, facial, bukkake, "
    "excessive saliva, spit torrent, drool puddle, orange slime, goo, "
    "brown eyes, hazel eyes, glowing eyes, star pupils, watermark, text, jpeg artifacts"
)
AD_POS = (
    "detailed face, beautiful detailed eyes, sharp iris, clear catchlights, "
    "detailed eyelashes, purple eyes, blue eyes, anime face, smooth skin"
)
AD_NEG = (
    "blurry face, deformed face, brown eyes, hazel eyes, glowing eyes, "
    "star pupils, cum, semen, facial"
)
EYES_POS = (
    "beautiful detailed eyes, sharp iris, clear catchlights, detailed eyelashes, "
    "purple eyes, blue eyes, anime eyes"
)
EYES_NEG = "brown eyes, hazel eyes, glowing eyes, star pupils, blank eyes, deformed eyes"


def run(cfg: dict, label: str, image: Path, **kw) -> Path:
    print(f"\n=== {label} ===", flush=True)
    r = refine_image_forge(cfg, image_path=str(image), **kw)
    print({k: r.get(k) for k in ("ok", "error", "saved_files", "adetailer")}, flush=True)
    if not r.get("ok"):
        raise SystemExit(f"fail {label}: {r}")
    src = Path(r["saved_files"][0])
    dest = OUT / f"FD_kissing_KEEP_{label}.png"
    shutil.copy2(src, dest)
    print("saved", dest, flush=True)
    return dest


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    print("forge", forge_url(cfg), forge_is_reachable(cfg), flush=True)
    if not forge_is_reachable(cfg):
        return 1

    p1 = run(
        cfg,
        "pass1_d028_faceAD",
        SRC,
        prompt=PROMPT,
        negative_prompt=NEG,
        checkpoint="waijfu_alpha.safetensors",
        denoising_strength=0.28,
        steps=28,
        cfg_scale=5.5,
        seed=42,
        adetailer=True,
        ad_prompt=AD_POS,
        ad_negative=AD_NEG,
        ad_model="face_yolov8n.pt",
        ad_denoising_strength=0.35,
    )
    p2 = run(
        cfg,
        "pass2_eyesOnly",
        p1,
        prompt=PROMPT,
        negative_prompt=NEG,
        checkpoint="waijfu_alpha.safetensors",
        denoising_strength=0.08,
        steps=20,
        cfg_scale=5.0,
        seed=42,
        adetailer=True,
        ad_prompt=EYES_POS,
        ad_negative=EYES_NEG,
        ad_model="mediapipe_face_mesh_eyes_only",
        ad_denoising_strength=0.28,
    )
    p_gentle = run(
        cfg,
        "alt_d018_faceAD",
        SRC,
        prompt=PROMPT,
        negative_prompt=NEG,
        checkpoint="waijfu_alpha.safetensors",
        denoising_strength=0.18,
        steps=28,
        cfg_scale=5.5,
        seed=42,
        adetailer=True,
        ad_prompt=AD_POS,
        ad_negative=AD_NEG,
        ad_model="face_yolov8n.pt",
        ad_denoising_strength=0.30,
    )
    print("\nDONE", flush=True)
    for p in (SRC, p1, p2, p_gentle):
        print(p, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
