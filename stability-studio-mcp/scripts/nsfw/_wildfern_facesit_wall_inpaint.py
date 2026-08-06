"""Wall/window inpaint on facesit v3s to match kiss forge_soften BG.

Masks protect bodies/hair/contact; Forge inpaint walls only. ADetailer OFF.
Does not overwrite v3 — writes *_bgmatch_v1.png.
"""
from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageFilter

FORGE = "http://127.0.0.1:7860"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
REF = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften"
    r"\Movie_WildFern_01_kiss_forge_soften.png"
)
CKPT = "waijfu_alpha.safetensors"
MASK_DIR = OUT / "_masks_bgmatch"
AD_OFF = {"ADetailer": {"args": [False]}}

PROMPT = (
    "masterpiece, best quality, anime++, "
    "loft bedroom at night, warm dark brown vertical wood panel walls, "
    "wood grain planks, cream conical lampshade warm yellow glow, "
    "dark wood nightstand, dark night window, warm lamp light, "
    "cozy night loft, clean background"
)
NEG = (
    "purple walls, lavender walls, pink walls, magenta walls, "
    "pine trees, trees, forest, evergreen, city neon, "
    "cum, semen, white stains, white splatters, fluids, fluid, "
    "person, face, body, breasts, ass, hair, "
    "man, male, penis, camera, dslr, daytime, blurry, bad anatomy"
)

JOBS = [
    dict(name="facesit_darkness_pov_v3", protect_bottom=0.32),
    dict(name="facesit_reverse_ass_chin_v3", protect_bottom=0.30),
]


def _b64_png(im: Image.Image) -> str:
    buf = BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def build_wall_mask(src: Path, protect_bottom: float) -> tuple[Image.Image, Image.Image]:
    """White = inpaint (walls).

    Important: purple *walls* must NOT be treated as purple hair.
    Force geometry wall bands + low-sat purple wall pixels into the mask.
    """
    im = Image.open(src).convert("RGB")
    arr = np.asarray(im).astype(np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = (mx - mn) / (mx + 1e-6)
    h, w = arr.shape[:2]

    # Skin (warm pale) — protect
    skin = (
        (r > 145)
        & (g > 95)
        & (b > 75)
        & (r > g - 5)
        & (r > b)
        & (r - b > 18)
        & (sat < 0.5)
    )
    # Blonde hair — protect
    blonde = (r > 150) & (g > 115) & (b < g + 15) & (r > b + 20) & (sat > 0.1)
    # Purple HAIR only: higher sat + darker, near skin (not flat wall fill)
    purple_hairish = (
        (b > g + 10)
        & (r > g)
        & (sat > 0.22)
        & (mx < 190)
        & (mx > 35)
    )
    # Dilate skin a lot → hair near body counts as protect; flat wall purple does not
    skin_u8 = (skin.astype(np.uint8) * 255)
    skin_im = Image.fromarray(skin_u8, mode="L")
    for _ in range(8):
        skin_im = skin_im.filter(ImageFilter.MaxFilter(9))
    near_body = np.asarray(skin_im) > 40
    purple_hair = purple_hairish & near_body

    protect = skin | blonde | purple_hair
    # Center-bottom contact / sheets
    y0 = int(h * (1.0 - protect_bottom))
    x0, x1 = int(w * 0.15), int(w * 0.85)
    protect[y0:, x0:x1] = True

    prot_u8 = (protect.astype(np.uint8) * 255)
    prot_im = Image.fromarray(prot_u8, mode="L")
    for _ in range(2):
        prot_im = prot_im.filter(ImageFilter.MaxFilter(5))
    prot_im = prot_im.filter(ImageFilter.GaussianBlur(1.5))
    protect = np.asarray(prot_im) > 40

    # FORCE wall inpaint regions (geometry) — top band + side strips
    force = np.zeros((h, w), dtype=bool)
    force[: int(h * 0.28), :] = True
    force[:, : int(w * 0.20)] = True
    force[:, int(w * 0.80) :] = True
    # Purple / lavender WALL paint (was wrongly protected as hair before)
    purple_wall = (
        (b > g + 3)
        & (r > g - 15)
        & (sat < 0.45)
        & (mx > 50)
        & (mx < 210)
        & (~skin)
        & (~blonde)
    )
    force |= purple_wall

    # Never force-inpaint on protected body
    force &= ~protect

    wall = force.astype(np.uint8) * 255
    wall_im = Image.fromarray(wall, mode="L")
    wall_im = wall_im.filter(ImageFilter.GaussianBlur(2.0))
    # Preview: red overlay on walls
    overlay = arr.copy()
    m = np.asarray(wall_im) > 80
    overlay[m] = overlay[m] * 0.45 + np.array([220, 40, 40], dtype=np.float32) * 0.55
    preview = Image.fromarray(overlay.astype(np.uint8))
    return wall_im, preview


def inpaint(src: Path, mask: Image.Image, dest: Path, seed: int) -> Path:
    with Image.open(src) as im:
        w, h = im.size
        init = im.convert("RGB")
    payload = {
        "init_images": [_b64_png(init)],
        "mask": _b64_png(mask.convert("L")),
        "prompt": PROMPT,
        "negative_prompt": NEG,
        "denoising_strength": 0.78,
        "steps": 34,
        "cfg_scale": 6.5,
        "width": w,
        "height": h,
        "seed": seed,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "resize_mode": 0,
        "mask_blur": 8,
        "inpainting_fill": 0,  # fill noise — purple paint must not dominate
        "inpaint_full_res": True,
        "inpaint_full_res_padding": 64,
        "inpainting_mask_invert": 0,  # white = inpaint
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_OFF,
    }
    print(f"=== inpaint {src.name} -> {dest.name} seed={seed}", flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
    r.raise_for_status()
    data = r.json()
    raw = base64.b64decode(data["images"][0].split(",", 1)[-1])
    dest.write_bytes(raw)
    meta = dest.with_suffix(".json")
    meta.write_text(
        json.dumps(
            {
                "source": str(src),
                "ref_bg": str(REF),
                "seed": seed,
                "denoise": 0.78,
                "prompt": PROMPT,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("OK", dest, len(raw), flush=True)
    return dest


def main() -> int:
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    if not REF.is_file():
        raise FileNotFoundError(REF)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )

    seeds = {"facesit_darkness_pov_v3": 60001, "facesit_reverse_ass_chin_v3": 60011}
    for job in JOBS:
        src = OUT / f"{job['name']}.png"
        if not src.is_file():
            raise FileNotFoundError(src)
        mask, preview = build_wall_mask(src, job["protect_bottom"])
        mask_path = MASK_DIR / f"{job['name']}_wallmask.png"
        prev_path = MASK_DIR / f"{job['name']}_wallmask_preview.png"
        mask.save(mask_path)
        preview.save(prev_path)
        print("mask", mask_path, "white_pct", round(100 * (np.asarray(mask) > 127).mean(), 1), flush=True)
        dest = OUT / f"{job['name']}_bgmatch_v1.png"
        inpaint(src, mask, dest, seeds[job["name"]])

    print("DONE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
