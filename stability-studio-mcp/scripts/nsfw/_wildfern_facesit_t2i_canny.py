"""Facesit: true txt2img + ControlNet canny (pose from guide). Night loft, not blown."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests
from PIL import Image

FORGE = "http://127.0.0.1:7860"
CKPT = "waijfu_alpha.safetensors"
SEED = 63201

GUIDE = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften\_bgcity_i2i\_finish"
    r"\facesit_darkness_pov_v3_d65.png"
)
OUT = GUIDE.parent

# Pose from canny only. No Darkness ID LoRA — roles locked in one clear sentence.
PROMPT = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
    "loft bedroom at night, dark interior, low key lighting, "
    "warm dark brown vertical wood panel walls, wood grain, "
    "single cream lamp with soft warm yellow glow, dark wood nightstand, "
    "wooden window showing black night sky and city skyline with lit windows, "
    "no trees, urban night, "
    "white rumpled sheets, white pillows, dark wood headboard on the right, "
    "dim warm lamp light, deep shadows, natural contrast, matte skin, "
    "View from below looking up, "
    "nb_fern with purple hair and purple eyes and large breasts, "
    "sitting on the face of a blonde girl with blue eyes and large breasts, "
    "facesitting, pussy licking, wet pussy, "
    "completely nude, looking down at viewer"
)
NEG = (
    "daytime, daylight, bright room, overexposed, blown highlights, harsh glare, "
    "washed out, bloom, oily skin glare, plastic shine, pale overbright skin, "
    "bright white skin, high key lighting, sunny, morning light, "
    "purple walls, lavender walls, pale wood, "
    "pine trees, trees outside window, forest, evergreen, woods, "
    "cum, semen, white stains, fluids, fluid, "
    "camera, dslr, camcorder, "
    "blonde on top, blonde girl sitting, blonde girl on top, blonde hair on top, "
    "yellow hair sitting, golden hair on top, "
    "purple hair under, purple bangs under, purple eyes under, "
    "blue eyes on Fern, blue eyes looking down, "
    "black hair under, brown hair under, orange hair, ginger hair, "
    "two Ferns, two purple girls, "
    "closed eyes, eyes closed, "
    "man, male, penis, cock, 1boy, clothes, lingerie, pubic hair"
)


def face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for n in ("Facesitting", "povFacesitting"):
        if n in names:
            return n
    raise RuntimeError("no Facesitting LoRA")


def main() -> int:
    if not GUIDE.is_file():
        raise FileNotFoundError(GUIDE)
    face = face_tag()
    with Image.open(GUIDE) as im:
        w, h = im.size
    tmp = OUT / "_rgb" / "facesit_canny_guide.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    Image.open(GUIDE).convert("RGB").save(tmp)
    b64 = base64.b64encode(tmp.read_bytes()).decode()

    prompt = f"<lora:{face}:0.55> <lora:Fern_id_v1:0.9> " + PROMPT
    unit = {
        "enabled": True,
        "module": "canny",
        "model": "controlnet-canny-sdxl-1.0",
        "weight": 0.85,
        "image": b64,
        "resize_mode": "Crop and Resize",
        "low_vram": False,
        "processor_res": 1024,
        "threshold_a": 100,
        "threshold_b": 200,
        "guidance_start": 0.0,
        "guidance_end": 0.8,
        "control_mode": "Balanced",
        "pixel_perfect": True,
    }
    # depth off — canny pose only
    payload = {
        "prompt": prompt,
        "negative_prompt": NEG,
        "steps": 32,
        "cfg_scale": 5.5,
        "width": w,
        "height": h,
        "seed": SEED,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": {
            "ControlNet": {"args": [unit]},
            "ADetailer": {"args": [False]},
        },
    }
    print("=== T2I + ControlNet canny (night) ===", flush=True)
    print("guide", GUIDE, flush=True)
    print("seed", SEED, "size", w, h, flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/txt2img", json=payload, timeout=1800)
    r.raise_for_status()
    dest = OUT / f"facesit_t2i_canny_blonde_s{SEED}.png"
    dest.write_bytes(base64.b64decode(r.json()["images"][0].split(",", 1)[-1]))
    (OUT / f"{dest.stem}.json").write_text(
        json.dumps(
            {
                "mode": "txt2img+canny",
                "seed": SEED,
                "guide": str(GUIDE),
                "canny_weight": 0.85,
                "depth": False,
                "prompt": prompt,
                "negative": NEG,
                "out": str(dest),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("OK", dest, dest.stat().st_size, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
