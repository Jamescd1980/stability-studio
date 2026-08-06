"""Facesit retry: lock loft BG from Fern_Facesit_v10 + enlarge Fern bust.

POV: img2img from darkness_pov_v3 (best pose) with BG + bust fix.
Reverse: img2img from Fern_Facesit_v10 (correct loft BG) — Fern on Darkness,
         ass/chin, head cropped, no lookback.
"""
from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import requests
from PIL import Image
from send2trash import send2trash

FORGE = "http://127.0.0.1:7860"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
REF_POV = OUT / "facesit_darkness_pov_v3.png"
REF_BG = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\Approved\Fern_Facesit_v10.png"
)
CKPT = "waijfu_alpha.safetensors"

# Exact loft language from Fern_Facesit_v10 / forge_soften keepers
LOFT = (
    "same loft bedroom as reference, lavender vertical wood plank walls, "
    "two small dark-framed landscape pictures on the wall, "
    "dark wood ceiling beams, dark wood nightstands, "
    "two bedside lamps with cream shades warm glow, "
    "large wooden window on the right, dark blue night sky with stars, "
    "pine tree silhouettes outside window, purple bed sheets, "
    "dim warm night lighting, "
)
QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, perfect eyes, "
)
BUST = (
    "large breasts, big breasts, full breasts, heavy breasts, "
    "ample cleavage, thick thighs, "
)
LORA_POV = (
    "<lora:Facesitting:0.7> <lora:Fern_id_v1:0.92> "
    "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.7> "
)
LORA_REV = "<lora:Fern_id_v1:0.95> "

NEG_POV = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "man, male, penis, cock, 1boy, "
    "blonde on top, blonde sitting, small breasts, flat chest, tiny breasts, petite breasts, "
    "purple hair under, black hair under, purple eyes under, two Ferns, "
    "modern apartment, white walls, city skyline, daylight, sunny window, "
    "closed eyes, eyes closed, clothes, lingerie, "
    "camera, dslr, camcorder, lens, pubic hair"
)
NEG_REV = (
    "bad quality, worst quality, blurry, bad anatomy, "
    "man, male, penis, cock, "
    "blonde on top, blonde ass, blonde back, "
    "looking back, looking over shoulder, looking at viewer, "
    "face visible, eyes of top girl, smile at viewer, portrait, "
    "small breasts, flat chest, tiny breasts, "
    "modern apartment, white walls, city skyline, daylight, "
    "purple hair under, Fern face, "
    "camera, dslr, clothes, lingerie, pubic hair"
)
AD_OFF = {"ADetailer": {"args": [False]}}


def _rgb_temp(path: Path, w: int, h: int) -> Path:
    """Forge-friendly RGB PNG at target size."""
    tmp = OUT / "_tmp_init"
    tmp.mkdir(exist_ok=True)
    dest = tmp / f"{path.stem}_{w}x{h}.png"
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.size != (w, h):
            im = im.resize((w, h), Image.Resampling.LANCZOS)
        im.save(dest, format="PNG")
    return dest


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def resolve_face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    if "Facesitting" in names:
        return "Facesitting"
    if "povFacesitting" in names:
        return "povFacesitting"
    raise RuntimeError(f"missing Facesitting LoRA: {sorted(names)}")


def img2img(
    *,
    name: str,
    init: Path,
    prompt: str,
    neg: str,
    seed: int,
    denoise: float,
    w: int = 1024,
    h: int = 1024,
) -> Path:
    out = OUT / f"{name}.png"
    init_rgb = _rgb_temp(init, w, h)
    payload = {
        "init_images": [_b64(init_rgb)],
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
    print(f"=== {name} denoise={denoise} seed={seed} init={init.name}", flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
    r.raise_for_status()
    data = r.json()
    raw = base64.b64decode(data["images"][0].split(",", 1)[-1])
    out.write_bytes(raw)
    (OUT / f"{name}.json").write_text(
        json.dumps(
            {
                "name": name,
                "seed": seed,
                "denoise": denoise,
                "init": str(init),
                "prompt": prompt,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("OK", out, len(raw), flush=True)
    return out


def main() -> int:
    if not REF_BG.is_file():
        raise FileNotFoundError(REF_BG)

    OUT.mkdir(parents=True, exist_ok=True)
    # Keep seed refs outside recycle
    seed_dir = OUT / "_seed_refs"
    seed_dir.mkdir(exist_ok=True)
    pov_seed = seed_dir / "pov_v3_seed.png"
    if REF_POV.is_file():
        shutil.copy2(REF_POV, pov_seed)
    elif not pov_seed.is_file():
        raise FileNotFoundError(f"Missing POV seed: {REF_POV} or {pov_seed}")
    shutil.copy2(REF_BG, seed_dir / "Fern_Facesit_v10_bg.png")

    for p in list(OUT.glob("facesit_*.png")) + list(OUT.glob("facesit_*.json")):
        print("recycle", p.name, flush=True)
        send2trash(str(p))

    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = resolve_face_tag()
    lora_pov = LORA_POV.replace("Facesitting", face)

    # --- Darkness POV ×3 from best pose ---
    pov_jobs = [
        dict(
            name="facesit_darkness_pov_v1",
            seed=55001,
            denoise=0.48,
            prompt=(
                lora_pov
                + QUALITY
                + LOFT
                + BUST
                + "View from below looking up, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, long purple hair, purple eyes, "
                "completely nude, large bare breasts, "
                "sitting on a face, looking down at viewer, pleasure face, "
                "bottom edge: blonde bangs and blue eyes looking up, "
                "wet pussy, cunnilingus"
            ),
        ),
        dict(
            name="facesit_darkness_pov_v2",
            seed=55011,
            denoise=0.52,
            prompt=(
                lora_pov
                + QUALITY
                + LOFT
                + BUST
                + "from below looking up between thighs, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
                "completely nude, big breasts, heavy breasts, "
                "straddling a face, looking down at viewer, open mouth, "
                "blonde bangs and blue eyes at bottom of frame under her pussy, "
                "wet pussy, cunnilingus"
            ),
        ),
        dict(
            name="facesit_darkness_pov_v3",
            seed=55021,
            denoise=0.45,
            prompt=(
                lora_pov
                + QUALITY
                + LOFT
                + BUST
                + "low angle view looking up, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
                "completely nude, large breasts, full breasts, "
                "sitting on blonde face, looking down at viewer, flushed cheeks, "
                "blonde bangs blue eyes under her pussy only, "
                "lavender wood walls, cream lamp shades, night window with pines, "
                "wet pussy juice, cunnilingus"
            ),
        ),
    ]

    for j in pov_jobs:
        img2img(
            name=j["name"],
            init=pov_seed,
            prompt=j["prompt"],
            neg=NEG_POV,
            seed=j["seed"],
            denoise=j["denoise"],
            w=1024,
            h=1152,
        )

    # --- Reverse cam ×3 from Facesit_v10 (correct BG) ---
    rev_jobs = [
        dict(
            name="facesit_reverse_ass_chin_v1",
            seed=55101,
            denoise=0.5,
            prompt=(
                LORA_REV
                + QUALITY
                + LOFT
                + BUST
                + "View from behind, ass focus, rear view, "
                "solo focus, 1girl, nb_fern, Fern, long purple hair down bare back, "
                "completely nude, large breasts sideboob, bare ass, "
                "head out of frame, faceless, no looking back, "
                "kneeling on blonde face, pussy on mouth, "
                "blonde chin and lips sucking her clit, cunnilingus, wet pussy"
            ),
        ),
        dict(
            name="facesit_reverse_ass_chin_v2",
            seed=55111,
            denoise=0.55,
            prompt=(
                LORA_REV
                + QUALITY
                + LOFT
                + BUST
                + "from behind, ass focus, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, "
                "completely nude, big breasts, bare ass, "
                "face buried in pillows, head down away from viewer, "
                "blonde chin under her pussy sucking clit, tongue on clit, "
                "cunnilingus, lavender plank walls, framed pictures, night pines"
            ),
        ),
        dict(
            name="facesit_reverse_ass_chin_v3",
            seed=55121,
            denoise=0.48,
            prompt=(
                LORA_REV
                + QUALITY
                + LOFT
                + BUST
                + "close rear view, ass focus, "
                "solo focus, 1girl, nb_fern, Fern, purple hair cascading, "
                "completely nude, heavy breasts, bare hips and ass, "
                "no face in frame, head cropped out, "
                "sitting on blonde face, blonde jaw under pussy, "
                "lips sucking clit, wet tongue, cunnilingus"
            ),
        ),
    ]

    for j in rev_jobs:
        img2img(
            name=j["name"],
            init=REF_BG,
            prompt=j["prompt"],
            neg=NEG_REV,
            seed=j["seed"],
            denoise=j["denoise"],
        )

    print("DONE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
