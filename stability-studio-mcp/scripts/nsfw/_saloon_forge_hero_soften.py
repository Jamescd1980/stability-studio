"""Low-denoise Forge+ADetailer soften pass for Saloon hero stills (Wan-friendlier)."""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import refine_image_forge  # noqa: E402

PACK = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\scene_packs\Frieren Saloon"
)
OUT = PACK / "hero_forge"
GAME = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\Movie_Saloon")
FORGE = "http://192.168.50.57:7860"

# stem -> (source filename, game cg filename or None, mode)
# mode: oral = eyes-only ultra-low denoise; body = soft light + face ADetailer
JOBS = [
    ("BJ02", "BJ02.png", "saloon_bj02.png", "oral"),
    ("SS01", "SS01.png", "saloon_ss01.png", "body"),
    ("SS03_2", "SS03-2.png", "saloon_ss03_2.png", "body"),
    ("SS04_1", "SS04-1.png", "saloon_ss04.png", "body"),
    ("SS04_002", "SS04_002.png", "saloon_ss04_002.png", "body"),
]

PROMPT_BODY = (
    "masterpiece, best quality, anime++, Frieren, silver hair, green eyes, "
    "soft diffused lighting, gentle rim light, matte skin, reduced specular, "
    "natural eyes, clean iris, round pupils, consistent face, "
    "warm saloon wood background unchanged"
)
PROMPT_ORAL = (
    "masterpiece, best quality, anime++, Frieren, soft diffused lighting, "
    "matte skin, natural eyes, clean iris, round pupils, no glare"
)
NEG = (
    "overexposed, harsh specular, oily skin glare, blown highlights, "
    "lens flare, eye flare, sparkle eyes, glowing eyes, starburst eyes, "
    "plastic skin, blurry, bad anatomy, extra fingers, "
    "camera, dslr, camcorder, watermark, text"
)
AD_FACE = (
    "Frieren face, green eyes, soft diffuse catchlights, detailed iris, "
    "round pupils, clean eyes, soft lighting, natural skin"
)
AD_EYES = (
    "natural anime eyes, soft diffuse catchlights, detailed iris, "
    "round pupils, clean eyes, no glare, no flare"
)
AD_NEG = (
    "lens flare, eye flare, bright catchlights, sparkle eyes, glowing eyes, "
    "starburst, star pupils, overexposed eyes, specular eyes, oily glare"
)


def wait_forge() -> None:
    for _ in range(90):
        try:
            if requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=5).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError("Forge not up")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    wait_forge()
    cfg = load_config()
    cfg.setdefault("forge", {})
    cfg["forge"]["url"] = FORGE
    cfg["forge"]["generate_timeout_seconds"] = 2400
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": "waijfu_alpha.safetensors"},
        timeout=600,
    )

    results = []
    for stem, src_name, game_name, mode in JOBS:
        src = PACK / src_name
        if not src.is_file():
            print("MISSING", src_name, flush=True)
            results.append({"name": stem, "ok": False, "error": "missing"})
            continue
        dest = OUT / f"{stem}_forge_soften.png"
        print("===", stem, mode, flush=True)
        if mode == "oral":
            r = refine_image_forge(
                cfg,
                image_path=str(src),
                prompt=PROMPT_ORAL,
                negative_prompt=NEG,
                checkpoint="waijfu_alpha.safetensors",
                denoising_strength=0.08,
                steps=24,
                cfg_scale=5.0,
                seed=62024,
                adetailer=True,
                ad_model="mediapipe_face_mesh_eyes_only",
                ad_prompt=AD_EYES,
                ad_negative=AD_NEG,
                ad_denoising_strength=0.32,
                ad_dilate_erode=2,
                ad_mask_padding=20,
            )
        else:
            r = refine_image_forge(
                cfg,
                image_path=str(src),
                prompt=PROMPT_BODY,
                negative_prompt=NEG,
                checkpoint="waijfu_alpha.safetensors",
                denoising_strength=0.22,
                steps=28,
                cfg_scale=5.0,
                seed=62024,
                adetailer=True,
                ad_model="face_yolov8n.pt",
                ad_prompt=AD_FACE,
                ad_negative=AD_NEG,
                ad_denoising_strength=0.30,
                ad_dilate_erode=4,
                ad_mask_padding=32,
            )
        if not r.get("ok") or not r.get("saved_files"):
            print("FAIL", r.get("error"), flush=True)
            results.append({"name": stem, "ok": False, "error": r.get("error")})
            continue
        shutil.copy2(r["saved_files"][0], dest)
        # also keep a review copy next to pack originals
        if game_name and GAME.is_dir():
            # do not overwrite game until user gates — copy as *_forge_soften candidate
            cand = GAME / f"{Path(game_name).stem}_forge_soften.png"
            shutil.copy2(dest, cand)
        print("OK", dest, flush=True)
        results.append({"name": stem, "ok": True, "path": str(dest)})

    summary = OUT / "_forge_soften_batch.json"
    summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0 if all(x.get("ok") for x in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
