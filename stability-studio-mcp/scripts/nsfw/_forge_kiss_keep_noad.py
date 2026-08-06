"""Light Forge touch on FD_kissing_KEEP — ADetailer off, low denoise."""
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
    "2girls, fern, darkness, blonde ponytail, purple hair, nude, "
    "closed mouth kiss, lips pressed together, soft closed lips, "
    "natural eyes, purple eyes, blue eyes, soft lamp light, bedroom loft, wet skin, clean lineart"
)
NEG = (
    "lowres, blurry, deformed face, bad anatomy, cum, semen, facial, bukkake, "
    "open mouth, tongue, tongue out, french kiss, excessive saliva, spit, drool, "
    "eye makeup, heavy makeup, eyeliner, eyeshadow, mascara, smokey eyes, "
    "brown eyes, hazel eyes, glowing eyes, star pupils, watermark, text, jpeg artifacts"
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    print("forge", forge_url(cfg), forge_is_reachable(cfg), flush=True)
    if not forge_is_reachable(cfg):
        return 1

    for denoise, seed in ((0.10, 42), (0.14, 42)):
        label = f"noAD_d{str(denoise).replace('.', '')}_s{seed}"
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
        dest = OUT / f"FD_kissing_KEEP_{label}.png"
        shutil.copy2(r["saved_files"][0], dest)
        print("saved", dest, flush=True)

    print("\nDONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
