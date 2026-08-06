"""Wild Fern city keepers → Saloon-style low-denoise soften + anti-flare AD.

Skip aftercare. Gate before promoting over forge_soften masters / game CGs.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests
from PIL import Image

FORGE = "http://127.0.0.1:7860"
CKPT = "waijfu_alpha.safetensors"
FORGE_DIR = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften"
)
OUT = FORGE_DIR / "_saloon_soften"
SEED = 62024
DENOISE = 0.15
STEPS = 28
CFG = 5.0

NEG = (
    "overexposed, harsh specular, oily skin glare, blown highlights, "
    "lens flare, eye flare, sparkle eyes, glowing eyes, starburst eyes, "
    "plastic skin, blurry, soft focus, bad anatomy, extra fingers, "
    "camera, dslr, camcorder, watermark, text, "
    "cum, semen, man, male, penis, cock, 1boy"
)
AD_NEG = (
    "lens flare, eye flare, bright catchlights, sparkle eyes, glowing eyes, "
    "starburst, star pupils, overexposed eyes, specular eyes, oily glare"
)
AD_EYES = (
    "natural anime eyes, soft diffuse catchlights, detailed iris, "
    "round pupils, clean eyes, no glare, no flare"
)

JOBS = [
    dict(
        id="01_kiss",
        src=FORGE_DIR / "Movie_WildFern_01_kiss_forge_soften.png",
        prompt=(
            "<lora:Fern_id_v1:0.75> <lora:Darkness_id_v1:0.75> "
            "masterpiece, best quality, anime++, "
            "soft diffused lighting, matte skin, reduced specular, "
            "natural eyes, clean iris, round pupils, no glare, "
            "detailed nipples, textured areola, sharp focus, "
            "2girls, nb_fern, Fern, purple hair, purple eyes, "
            "nbk_darkness, Darkness, blonde hair, blue eyes, "
            "both completely nude, kissing, "
            "dark wood loft bedroom background unchanged"
        ),
        ad_face=True,
        ad_prompt=(
            "anime faces, purple eyes, blue eyes, soft diffuse catchlights, "
            "detailed iris, round pupils, clean eyes, no glare, natural skin"
        ),
    ),
    dict(
        id="02_fern_licks",
        src=FORGE_DIR / "Movie_WildFern_02_fern_licks_forge_soften.png",
        prompt=(
            "<lora:Fern_id_v1:0.8> "
            "masterpiece, best quality, anime++, "
            "soft diffused lighting, matte skin, reduced specular, "
            "natural eyes, clean iris, round pupils, no glare, "
            "detailed nipples, textured areola, sharp focus, "
            "1girl, nb_fern, Fern, purple hair, purple eyes, completely nude, "
            "dark wood loft bedroom background unchanged"
        ),
        ad_face=True,
        ad_prompt=(
            "Fern face, purple eyes, soft diffuse catchlights, "
            "detailed iris, round pupils, clean eyes, no glare, natural skin"
        ),
    ),
    dict(
        id="04_fern_revcowgirl",
        src=FORGE_DIR / "Movie_WildFern_04_fern_revcowgirl_forge_soften.png",
        prompt=(
            "<lora:Fern_id_v1:0.8> "
            "masterpiece, best quality, anime++, "
            "soft diffused lighting, matte skin, reduced specular, "
            "natural eyes, clean iris, round pupils, no glare, "
            "detailed nipples, textured areola, sharp focus, "
            "1girl, nb_fern, Fern, purple hair, purple eyes, completely nude, "
            "dark wood loft bedroom background unchanged"
        ),
        ad_face=True,
        ad_prompt=(
            "Fern face, purple eyes, soft diffuse catchlights, "
            "detailed iris, round pupils, clean eyes, no glare, natural skin"
        ),
    ),
    dict(
        id="05_fern_doggy",
        src=FORGE_DIR / "Movie_WildFern_05_fern_doggy_forge_soften.png",
        prompt=(
            "<lora:Fern_id_v1:0.75> <lora:Darkness_id_v1:0.75> "
            "masterpiece, best quality, anime++, "
            "soft diffused lighting, matte skin, reduced specular, "
            "natural eyes, clean iris, round pupils, no glare, "
            "detailed nipples, textured areola, sharp focus, "
            "2girls, nb_fern, Fern, purple hair, purple eyes, "
            "nbk_darkness, Darkness, blonde hair, blue eyes, "
            "both completely nude, "
            "dark wood loft bedroom background unchanged"
        ),
        ad_face=True,
        ad_prompt=(
            "anime faces, purple eyes, blue eyes, soft diffuse catchlights, "
            "detailed iris, round pupils, clean eyes, no glare, natural skin"
        ),
    ),
    dict(
        id="facesit",
        src=FORGE_DIR / "facesit_darkness_pov_city_KEEP.png",
        prompt=(
            "<lora:Facesitting:0.45> <lora:Fern_id_v1:0.8> "
            "masterpiece, best quality, anime++, "
            "soft diffused lighting, matte skin, reduced specular, "
            "natural eyes, clean iris, round pupils, no glare, "
            "detailed nipples, textured areola, sharp focus, "
            "1girl, nb_fern, Fern, purple hair, purple eyes, completely nude, "
            "blonde bangs, blue eyes looking up at bottom edge, "
            "dark wood loft bedroom background unchanged"
        ),
        ad_face=True,
        ad_prompt=(
            "Fern face, purple eyes, soft diffuse catchlights, "
            "detailed iris, round pupils, clean eyes, no glare, natural skin"
        ),
    ),
]


def ad_script(job: dict) -> dict:
    if not job.get("ad_face"):
        return {"ADetailer": {"args": [False]}}
    # Face AD with anti-flare (Saloon SS02 body recipe). Eyes-only model optional.
    return {
        "ADetailer": {
            "args": [
                {
                    "ad_model": "face_yolov8n.pt",
                    "ad_prompt": job["ad_prompt"] + ", no glare, no flare",
                    "ad_negative_prompt": AD_NEG,
                    "ad_confidence": 0.25,
                    "ad_dilate_erode": 4,
                    "ad_mask_blur": 4,
                    "ad_denoising_strength": 0.30,
                    "ad_inpaint_only_masked": True,
                    "ad_inpaint_padding": 32,
                }
            ]
        }
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    results = []
    print(f"=== Wild Fern Saloon soften d={DENOISE} ===", flush=True)
    for job in JOBS:
        src = job["src"]
        if not src.is_file():
            print("MISSING", src, flush=True)
            results.append({"id": job["id"], "ok": False, "error": "missing"})
            return 1
        with Image.open(src) as im:
            w, h = im.size
            rgb = im.convert("RGB")
        tmp = OUT / f"_{job['id']}_rgb.png"
        rgb.save(tmp, format="PNG")
        print(f"{job['id']} <- {src.name} {w}x{h}", flush=True)
        payload = {
            "init_images": [base64.b64encode(tmp.read_bytes()).decode()],
            "prompt": job["prompt"],
            "negative_prompt": NEG,
            "denoising_strength": DENOISE,
            "steps": STEPS,
            "cfg_scale": CFG,
            "width": w,
            "height": h,
            "seed": SEED,
            "sampler_name": "Euler a",
            "restore_faces": False,
            "override_settings": {"sd_model_checkpoint": CKPT},
            "override_settings_restore_afterwards": True,
            "alwayson_scripts": ad_script(job),
        }
        r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
        r.raise_for_status()
        dest = OUT / f"{job['id']}.png"
        dest.write_bytes(base64.b64decode(r.json()["images"][0].split(",", 1)[-1]))
        (OUT / f"{job['id']}.json").write_text(
            json.dumps(
                {
                    "id": job["id"],
                    "src": str(src),
                    "denoise": DENOISE,
                    "seed": SEED,
                    "prompt": job["prompt"],
                    "out": str(dest),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("  OK", dest.name, dest.stat().st_size, flush=True)
        results.append({"id": job["id"], "ok": True, "path": str(dest)})
    (OUT / "_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE — review", OUT, flush=True)
    print("NOT promoted to forge_soften masters / game — gate first", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
