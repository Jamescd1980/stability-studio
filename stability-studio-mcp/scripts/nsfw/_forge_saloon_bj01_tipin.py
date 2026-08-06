"""Forge Saloon BJ01 tip-in start still — ADetailer OFF, cock locked in mouth."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import forge_is_reachable, forge_url, refine_image_forge  # noqa: E402

SRC = Path(
    r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon\Ready for Post Production"
    r"\_bj01_forge\BJ01_start_tipin_f0041.png"
)
OUT = Path(
    r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon\Ready for Post Production"
    r"\_bj01_forge"
)

PROMPT = (
    "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
    "nb_frieren, frieren, elf girl, long silver white hair, twin tails, pointed ears, "
    "red teardrop earrings, pale skin, green eyes, nude, "
    "View from mans POV, looking up at viewer, "
    "blowjob, fellatio, thick cock in mouth, lips wrapped around cock, "
    "cock head inside mouth, shaft in mouth, oral sex, "
    "soft lamp light, wooden saloon interior, clean lineart"
)
NEG = (
    "lowres, blurry, deformed face, bad anatomy, "
    "penis outside mouth, cock outside mouth, tip outside mouth, glans outside, "
    "empty mouth, closed mouth, removed penis, floating penis, "
    "cum, semen, facial, bukkake, "
    "brown eyes, hazel eyes, glowing eyes, star pupils, "
    "camera, dslr, watermark, text, jpeg artifacts"
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    print("forge", forge_url(cfg), forge_is_reachable(cfg), flush=True)
    if not forge_is_reachable(cfg):
        return 1
    if not SRC.is_file():
        print("missing", SRC, flush=True)
        return 1

    results = []
    for denoise, seed, label in (
        (0.22, 42, "forge_d022_noAD"),
        (0.28, 42, "forge_d028_noAD"),
    ):
        print(f"\n=== {label} ===", flush=True)
        r = refine_image_forge(
            cfg,
            image_path=str(SRC),
            prompt=PROMPT,
            negative_prompt=NEG,
            checkpoint="waijfu_alpha.safetensors",
            denoising_strength=denoise,
            steps=28,
            cfg_scale=5.5,
            seed=seed,
            adetailer=False,
        )
        print({k: r.get(k) for k in ("ok", "error", "saved_files", "adetailer")}, flush=True)
        if not r.get("ok"):
            print(r, flush=True)
            return 1
        dest = OUT / f"BJ01_start_tipin_f0041_{label}.png"
        shutil.copy2(r["saved_files"][0], dest)
        print("saved", dest, flush=True)
        results.append(dest)

    print("\nDONE", flush=True)
    for p in results:
        print(p, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
