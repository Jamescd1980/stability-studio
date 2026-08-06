"""Retry facesit set keeping darkness_pov_v3. Dark wood BG, eye lock, no cum tags."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests
from PIL import Image

FORGE = "http://127.0.0.1:7860"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
POV_V3 = OUT / "facesit_darkness_pov_v3.png"
POV_SEED = OUT / "_seed_refs" / "pov_v3_seed.png"
# Reverse BG: approved facesit loft (will push walls to dark wood via prompt)
REV_SEED = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\Approved\Fern_Facesit_v10.png"
)
# Dark wood reference for BG language (kiss KEEP)
CKPT = "waijfu_alpha.safetensors"

# Dark wood loft — NOT purple/lavender walls (purple sheets OK)
LOFT = (
    "loft bedroom at night, dark wood panel walls, vertical dark wood planks, "
    "warm brown wood walls, dark wood ceiling beams, dark wood nightstands, "
    "two bedside lamps with cream shades warm glow, "
    "large wooden window, dark blue night sky with stars, pine tree silhouettes, "
    "purple bed sheets, dim warm night lighting, "
)
QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
)
BUST = "large breasts, big breasts, full breasts, heavy breasts, "
EYES_FERN = "purple eyes, violet eyes, "
EYES_DARK = "blue eyes, "

NEG_COMMON = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "man, male, penis, cock, 1boy, "
    "cum, semen, male cum, white splatters, cum on wall, cum on walls, "
    "bukkake, aftersex, ejaculate, fluids, fluid, "
    "purple walls, lavender walls, pink walls, painted purple wood, "
    "small breasts, flat chest, tiny breasts, "
    "camera, dslr, camcorder, lens, daytime, sunny window, "
    "clothes, lingerie, pubic hair"
)
NEG_POV = (
    NEG_COMMON
    + ", blonde on top, blonde sitting, "
    "blue eyes on Fern, blue eyes on top girl, "
    "purple eyes under, purple eyes on bottom, "
    "purple hair under, black hair under, two Ferns, "
    "closed eyes, eyes closed"
)
NEG_REV = (
    NEG_COMMON
    + ", blonde on top, blonde ass, blonde back, "
    "looking back, looking over shoulder, looking at viewer, "
    "face visible, eyes of top girl, portrait, "
    "purple hair under, Fern face"
)
AD_OFF = {"ADetailer": {"args": [False]}}


def _rgb_temp(path: Path, w: int, h: int) -> Path:
    tmp = OUT / "_tmp_init"
    tmp.mkdir(exist_ok=True)
    dest = tmp / f"{path.stem}_{w}x{h}.png"
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.size != (w, h):
            im = im.resize((w, h), Image.Resampling.LANCZOS)
        im.save(dest, format="PNG")
    return dest


def face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    if "Facesitting" in names:
        return "Facesitting"
    if "povFacesitting" in names:
        return "povFacesitting"
    raise RuntimeError(f"missing Facesitting: {sorted(names)}")


def img2img(
    *,
    name: str,
    init: Path,
    prompt: str,
    neg: str,
    seed: int,
    denoise: float,
    w: int,
    h: int,
) -> Path:
    out = OUT / f"{name}.png"
    init_rgb = _rgb_temp(init, w, h)
    payload = {
        "init_images": [base64.b64encode(init_rgb.read_bytes()).decode()],
        "prompt": prompt,
        "negative_prompt": neg,
        "denoising_strength": denoise,
        "steps": 36,
        "cfg_scale": 6.5,
        "width": w,
        "height": h,
        "seed": seed,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_OFF,
    }
    print(f"=== {name} d={denoise} seed={seed}", flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    out.write_bytes(raw)
    (OUT / f"{name}.json").write_text(
        json.dumps({"name": name, "seed": seed, "denoise": denoise, "prompt": prompt}, indent=2),
        encoding="utf-8",
    )
    print("OK", out, len(raw), flush=True)
    return out


def main() -> int:
    if not POV_V3.is_file() and not POV_SEED.is_file():
        raise FileNotFoundError("missing kept pov v3")
    init_pov = POV_V3 if POV_V3.is_file() else POV_SEED
    if not REV_SEED.is_file():
        raise FileNotFoundError(REV_SEED)

    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = face_tag()
    lora_pov = (
        f"<lora:{face}:0.7> <lora:Fern_id_v1:0.92> "
        "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.65> "
    )
    lora_rev = "<lora:Fern_id_v1:0.95> "

    # POV v1/v2 only — do not overwrite kept v3
    pov_jobs = [
        dict(
            name="facesit_darkness_pov_v1",
            seed=56001,
            denoise=0.5,
            prompt=(
                lora_pov
                + QUALITY
                + "perfect eyes, "
                + LOFT
                + BUST
                + "View from below looking up, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, long purple hair, "
                + EYES_FERN
                + "completely nude, large bare breasts, "
                "sitting on a face, looking down at viewer, pleasure face, "
                "bottom edge only: blonde bangs and "
                + EYES_DARK
                + "looking up, "
                "wet pussy, pussy juice, cunnilingus"
            ),
        ),
        dict(
            name="facesit_darkness_pov_v2",
            seed=56011,
            denoise=0.52,
            prompt=(
                lora_pov
                + QUALITY
                + "perfect eyes, "
                + LOFT
                + BUST
                + "from below looking up between thighs, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, "
                + EYES_FERN
                + "completely nude, big breasts, "
                "straddling a face, looking down at viewer, open mouth, "
                "blonde bangs and "
                + EYES_DARK
                + "at bottom under her pussy, "
                "wet pussy, pussy juice, cunnilingus"
            ),
        ),
    ]

    for j in pov_jobs:
        img2img(
            name=j["name"],
            init=init_pov,
            prompt=j["prompt"],
            neg=NEG_POV,
            seed=j["seed"],
            denoise=j["denoise"],
            w=1024,
            h=1152,
        )

    rev_jobs = [
        dict(
            name="facesit_reverse_ass_chin_v1",
            seed=56101,
            denoise=0.58,
            prompt=(
                lora_rev
                + QUALITY
                + LOFT
                + BUST
                + "View from behind, ass focus, "
                "solo focus, 1girl, nb_fern, Fern, long purple hair down bare back, "
                "completely nude, large breasts sideboob, bare ass, "
                "head out of frame, faceless, no looking back, "
                "kneeling on blonde face, pussy on mouth, "
                "blonde chin and lips sucking her clit, "
                "wet pussy, pussy juice, cunnilingus"
            ),
        ),
        dict(
            name="facesit_reverse_ass_chin_v2",
            seed=56111,
            denoise=0.62,
            prompt=(
                lora_rev
                + QUALITY
                + LOFT
                + BUST
                + "from behind, ass focus, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, "
                "completely nude, big breasts, bare ass, "
                "face buried in pillows, head down away from viewer, "
                "blonde chin under her pussy sucking clit, "
                "wet pussy, pussy juice, cunnilingus, "
                "dark wood panel walls"
            ),
        ),
        dict(
            name="facesit_reverse_ass_chin_v3",
            seed=56121,
            denoise=0.55,
            prompt=(
                lora_rev
                + QUALITY
                + LOFT
                + BUST
                + "close rear view, ass focus, "
                "solo focus, 1girl, nb_fern, Fern, purple hair cascading, "
                "completely nude, heavy breasts, bare hips and ass, "
                "no face in frame, head cropped out, "
                "sitting on blonde face, blonde jaw under pussy, "
                "lips sucking clit, wet pussy, pussy juice, cunnilingus"
            ),
        ),
    ]

    for j in rev_jobs:
        img2img(
            name=j["name"],
            init=REV_SEED,
            prompt=j["prompt"],
            neg=NEG_REV,
            seed=j["seed"],
            denoise=j["denoise"],
            w=1024,
            h=1024,
        )

    print("KEPT", POV_V3, flush=True)
    print("DONE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
