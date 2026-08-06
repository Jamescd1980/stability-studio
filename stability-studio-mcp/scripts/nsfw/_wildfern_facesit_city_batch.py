"""Wild Fern facesit — user loft template + city skyline (no trees). txt2img only."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests

FORGE = "http://127.0.0.1:7860"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
CKPT = "waijfu_alpha.safetensors"

# User template — town loft, city skyline (no trees)
LOFT = (
    "loft bedroom at night, pale wood plank walls, two framed pictures on wall, "
    "cream bedside lamps, wooden window, night sky city skyline, "
    "purple sheets, warm lamp light, "
)
QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
)

NEG = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "man, male, penis, cock, 1boy, "
    "cum, semen, male cum, white stains, white splatters, "
    "bukkake, aftersex, fluids, fluid, "
    "pine trees, trees outside window, forest, evergreen, "
    "camera, dslr, daytime, clothes, lingerie, pubic hair, "
    "small breasts, flat chest"
)
NEG_POV = (
    NEG
    + ", blonde on top, "
    "blue eyes on Fern, purple eyes under, "
    "purple bangs under, black hair under, two Ferns, "
    "closed eyes, eyes closed"
)
NEG_REV = (
    NEG
    + ", blonde on top, blonde ass, blonde back, "
    "looking back, looking over shoulder, looking at viewer, "
    "Fern face, face of top girl, eyes looking at viewer, "
    "purple hair under, side view, profile view"
)

AD_OFF = {"ADetailer": {"args": [False]}}


def face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for n in ("Facesitting", "povFacesitting"):
        if n in names:
            return n
    raise RuntimeError(f"no Facesitting LoRA: {sorted(names)}")


def txt2img(*, name: str, prompt: str, neg: str, seed: int, w: int = 1024, h: int = 1024) -> Path:
    out = OUT / f"{name}.png"
    payload = {
        "prompt": prompt,
        "negative_prompt": neg,
        "steps": 32,
        "cfg_scale": 6.0,
        "width": w,
        "height": h,
        "seed": seed,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_OFF,
    }
    print(f"=== {name} seed={seed}", flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/txt2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    out.write_bytes(raw)
    (OUT / f"{name}.json").write_text(
        json.dumps({"name": name, "seed": seed, "prompt": prompt}, indent=2),
        encoding="utf-8",
    )
    print("OK", out, len(raw), flush=True)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = face_tag()
    lora_pov = f"<lora:{face}:0.55> <lora:Fern_id_v1:0.9> "
    lora_rev = f"<lora:{face}:0.5> <lora:Fern_id_v1:0.9> "

    # --- Reverse (user prompt) ---
    rev_core = (
        QUALITY
        + LOFT
        + "close rear view, ass focus, solo focus, 1girl, nb_fern, "
        "long purple hair, completely nude, large breasts, bare hips and ass, "
        "sitting on blondes face, blondes mouth in pussy, lips sucking clit, "
        "wet pussy, cunnilingus, reverse facesitting"
    )
    for i, seed in enumerate((59001, 59011, 59021), 1):
        txt2img(
            name=f"facesit_reverse_ass_chin_v{i}",
            prompt=lora_rev + rev_core,
            neg=NEG_REV,
            seed=seed,
        )

    # --- Darkness POV from same loft template ---
    pov_jobs = [
        dict(
            name="facesit_darkness_pov_v1",
            seed=59101,
            prompt=(
                lora_pov
                + QUALITY
                + LOFT
                + "View from below looking up, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, long purple hair, purple eyes, "
                "completely nude, large breasts, "
                "sitting on a face, looking down at viewer, flushed cheeks, "
                "blonde bangs and blue eyes at bottom of frame, "
                "wet pussy, cunnilingus"
            ),
        ),
        dict(
            name="facesit_darkness_pov_v2",
            seed=59111,
            prompt=(
                lora_pov
                + QUALITY
                + LOFT
                + "View from below, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
                "completely nude, large breasts, "
                "straddling a face, looking down at viewer, mouth open, "
                "only blonde bangs and blue eyes under her pussy, "
                "wet pussy, pussy juice, cunnilingus"
            ),
        ),
        dict(
            name="facesit_darkness_pov_v3",
            seed=59121,
            h=1152,
            prompt=(
                lora_pov
                + QUALITY
                + LOFT
                + "low angle looking up, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
                "completely nude, large breasts, "
                "pussy on face, looking down at viewer, pleasure face, "
                "blonde bangs, blue eyes looking up at bottom edge, "
                "wet pussy, cunnilingus"
            ),
        ),
    ]
    for j in pov_jobs:
        txt2img(
            name=j["name"],
            prompt=j["prompt"],
            neg=NEG_POV,
            seed=j["seed"],
            w=1024,
            h=j.get("h", 1024),
        )

    print("DONE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
