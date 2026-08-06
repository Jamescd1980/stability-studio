"""Eyes-only Forge pass to kill eye flare on Wild Fern forge upscales."""
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

REVIEW = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\review"
)
GAME = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\Movie_WildFern")
FORGE = "http://192.168.50.57:7860"

JOBS = [
    ("fern_licks_forge_v1.png", "Movie_WildFern_01_fern_licks.png", "fern_licks_forge_v2"),
    ("fern_facesit_forge_v1.png", "Movie_WildFern_02_darkness_licks.png", "fern_facesit_forge_v2"),
    ("fern_revcowgirl_forge_v1.png", "Movie_WildFern_03_fern_revcowgirl.png", "fern_revcowgirl_forge_v2"),
    ("fern_doggy_forge_v1.png", "Movie_WildFern_04_fern_doggy.png", "fern_doggy_forge_v2"),
    ("fern_aftercare_forge_v1.png", "Movie_WildFern_05_aftercare.png", "fern_aftercare_forge_v2"),
]

PROMPT = (
    "masterpiece, best quality, anime++, natural eyes, soft lighting, "
    "clean iris, round pupils, no glare"
)
NEG = (
    "lens flare, eye flare, bright catchlights, sparkle eyes, shiny eyes, "
    "glowing eyes, specular highlight in eyes, overexposed eyes, "
    "starburst eyes, glowing pupils, star pupils, heart pupils, "
    "light reflection in eyes, blurry, bad anatomy"
)
AD_PROMPT = (
    "natural anime eyes, soft diffuse catchlights, detailed iris, "
    "round pupils, clean eyes, no glare, no flare"
)
AD_NEG = (
    "lens flare, eye flare, bright catchlights, sparkle eyes, glowing eyes, "
    "starburst, star pupils, overexposed eyes, specular eyes"
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
    for src_name, game_name, out_stem in JOBS:
        src = REVIEW / src_name
        if not src.is_file():
            print("MISSING", src_name, flush=True)
            results.append({"name": out_stem, "ok": False})
            continue
        dest = REVIEW / f"{out_stem}.png"
        print("===", out_stem, flush=True)
        r = refine_image_forge(
            cfg,
            image_path=str(src),
            prompt=PROMPT,
            negative_prompt=NEG,
            checkpoint="waijfu_alpha.safetensors",
            denoising_strength=0.06,
            steps=24,
            cfg_scale=5.0,
            seed=47101,
            adetailer=True,
            ad_model="mediapipe_face_mesh_eyes_only",
            ad_prompt=AD_PROMPT,
            ad_negative=AD_NEG,
            ad_denoising_strength=0.36,
            ad_dilate_erode=2,
            ad_mask_padding=20,
        )
        if not r.get("ok") or not r.get("saved_files"):
            print("FAIL", r.get("error"), flush=True)
            results.append({"name": out_stem, "ok": False, "error": r.get("error")})
            continue
        shutil.copy2(r["saved_files"][0], dest)
        shutil.copy2(dest, GAME / game_name)
        print("OK", dest.name, "->", game_name, flush=True)
        results.append({"name": out_stem, "ok": True, "path": str(dest)})
    (REVIEW / "_forge_deflare_batch.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0 if all(x.get("ok") for x in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
