"""Wild Fern eyes-only cleanup — 3 plates, lock Fern purple / Darkness blue.

Ultra-low global denoise + ADetailer face (anti-flare). Aftercare skipped.
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
OUT = FORGE_DIR / "_eye_clean"
SEED = 62024
# Lock body/BG — eyes via AD only
DENOISE = 0.06
AD_DENOISE = 0.30

NEG = (
    "lens flare, eye flare, sparkle eyes, glowing eyes, starburst eyes, "
    "star pupils, bright catchlights, overexposed eyes, specular eyes, "
    "oily glare, blown highlights, "
    "camera, dslr, blurry, bad anatomy"
)
AD_NEG = (
    "lens flare, eye flare, bright catchlights, sparkle eyes, glowing eyes, "
    "starburst, star pupils, overexposed eyes, specular eyes, oily glare, "
    "wrong eye color, heterochromia, red eyes, green eyes, yellow eyes"
)

# Dual-face / facesit — the three that need eye cleanup most
JOBS = [
    dict(
        id="01_kiss",
        src=FORGE_DIR / "Movie_WildFern_01_kiss_forge_soften.png",
        prompt=(
            "masterpiece, best quality, anime++, "
            "2girls kissing, soft lighting, matte skin, "
            "natural eyes, clean iris, round pupils, no glare, "
            "Fern purple eyes, Darkness blue eyes, "
            "background and bodies unchanged"
        ),
        ad_prompt=(
            "two anime faces, Fern purple irises, Darkness blue irises, "
            "soft diffuse catchlights, detailed iris, round pupils, "
            "clean eyes, no glare, no flare, correct eye colors"
        ),
    ),
    dict(
        id="05_fern_doggy",
        src=FORGE_DIR / "Movie_WildFern_05_fern_doggy_forge_soften.png",
        prompt=(
            "masterpiece, best quality, anime++, "
            "2girls, soft lighting, matte skin, "
            "natural eyes, clean iris, round pupils, no glare, "
            "Fern purple eyes, Darkness blue eyes, "
            "background and bodies unchanged"
        ),
        ad_prompt=(
            "two anime faces, Fern purple irises, Darkness blue irises, "
            "soft diffuse catchlights, detailed iris, round pupils, "
            "clean eyes, no glare, no flare, correct eye colors"
        ),
    ),
    dict(
        id="facesit",
        src=FORGE_DIR / "facesit_darkness_pov_city_KEEP.png",
        prompt=(
            "masterpiece, best quality, anime++, "
            "1girl facesitting, soft lighting, matte skin, "
            "natural eyes, clean iris, round pupils, no glare, "
            "Fern purple eyes looking down, "
            "blonde bangs blue eyes looking up at bottom edge, "
            "background and body unchanged"
        ),
        ad_prompt=(
            "Fern face, purple irises, soft diffuse catchlights, "
            "detailed iris, round pupils, clean eyes, no glare, no flare"
        ),
    ),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    # Prefer eyes-only model if installed
    try:
        models = requests.get(f"{FORGE}/sdapi/v1/scripts", timeout=60).json()
    except Exception:
        models = {}
    ad_model = "mediapipe_face_mesh_eyes_only"
    # Fall back silently via face model if eyes-only missing — Forge errors otherwise
    # Probe ADetailer model list if available
    ad_model_use = "face_yolov8n.pt"
    try:
        # some forks expose /adetailer/v1/ad_model
        r = requests.get(f"{FORGE}/adetailer/v1/ad_model", timeout=30)
        if r.ok:
            names = r.json() if isinstance(r.json(), list) else r.json().get("ad_model", [])
            if any("eyes_only" in str(x) for x in names):
                ad_model_use = "mediapipe_face_mesh_eyes_only"
            print("AD models sample", list(names)[:8], "using", ad_model_use, flush=True)
    except Exception as e:
        print("AD model probe skip", e, "using", ad_model_use, flush=True)

    results = []
    print(f"=== WF eye clean d={DENOISE} ad={AD_DENOISE} model={ad_model_use} ===", flush=True)
    for job in JOBS:
        src = job["src"]
        if not src.is_file():
            print("MISSING", src, flush=True)
            return 1
        with Image.open(src) as im:
            w, h = im.size
            rgb = im.convert("RGB")
        tmp = OUT / f"_{job['id']}_rgb.png"
        rgb.save(tmp, format="PNG")
        print(f"{job['id']} <- {src.name}", flush=True)
        payload = {
            "init_images": [base64.b64encode(tmp.read_bytes()).decode()],
            "prompt": job["prompt"],
            "negative_prompt": NEG,
            "denoising_strength": DENOISE,
            "steps": 24,
            "cfg_scale": 5.0,
            "width": w,
            "height": h,
            "seed": SEED,
            "sampler_name": "Euler a",
            "restore_faces": False,
            "override_settings": {"sd_model_checkpoint": CKPT},
            "override_settings_restore_afterwards": True,
            "alwayson_scripts": {
                "ADetailer": {
                    "args": [
                        {
                            "ad_model": ad_model_use,
                            "ad_prompt": job["ad_prompt"],
                            "ad_negative_prompt": AD_NEG,
                            "ad_confidence": 0.25,
                            "ad_dilate_erode": 2 if "eyes" in ad_model_use else 4,
                            "ad_mask_blur": 4,
                            "ad_denoising_strength": AD_DENOISE,
                            "ad_inpaint_only_masked": True,
                            "ad_inpaint_padding": 20 if "eyes" in ad_model_use else 28,
                        }
                    ]
                }
            },
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
                    "ad_denoise": AD_DENOISE,
                    "ad_model": ad_model_use,
                    "prompt": job["prompt"],
                    "ad_prompt": job["ad_prompt"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("  OK", dest.name, dest.stat().st_size, flush=True)
        results.append({"id": job["id"], "ok": True, "path": str(dest)})
    (OUT / "_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE review", OUT, flush=True)
    print("NOT promoted — gate first", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
