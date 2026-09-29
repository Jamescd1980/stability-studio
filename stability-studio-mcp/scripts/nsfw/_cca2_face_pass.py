"""CCA2 kiss lastframe — separate Forge face/eye inpaint per character.

1) Frieren (white hair) — full face, green eyes
2) Darkness (blonde) — eyes/upper face only so tongue-on-pussy stays locked

Forge must already be up on ComfyBox :7860.
"""
from __future__ import annotations

import base64
import json
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

FORGE = "http://192.168.50.57:7860"
CKPT = "waijfu_alpha.safetensors"
SRC = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs\Casting Couch\review\darkness_licks_v1.png"
)
OUT_DIR = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs\Casting Couch\review"
)
WORK_DIR = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Casting Couch\Work"
)
# Debug masks stay next to the still (human gate), not a nested tree.
DEBUG = OUT_DIR

NEG = (
    "picture in picture, inset, panel, camera, dslr, cum, semen, fluids, "
    "1boy, penis, melted, mushy, extra limbs, heterochromia, "
    "wrong eye color, blank eyes, extra eyes, star pupils, lens flare"
)

PROMPT_FRIEREN = (
    "masterpiece, best quality, anime++, "
    "Frieren face, white hair, silver hair, pigtails, "
    "green eyes, green irises, sharp pupils, clean eyes, "
    "pointed elf ears, pale skin, looking down"
)

PROMPT_DARKNESS = (
    "masterpiece, best quality, anime++, "
    "nbk_darkness, blonde hair, side view, "
    "dark blue eyes, dark blue irises, sharp pupils, clean eyes"
)

# Tight boxes from crops: Frieren face is upper-right; Darkness eye is
# profile lower-left. Do NOT include her mouth — tongue stays on pussy.
BOX_FRIEREN = (540, 20, 870, 360)
BOX_DARKNESS_EYES = (130, 670, 330, 840)


def b64_png(im: Image.Image) -> str:
    buf = BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def ellipse_mask(size: tuple[int, int], box: tuple[int, int, int, int], blur: int = 8) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(list(box), fill=255)
    if blur:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return mask


def forge_inpaint(
    *,
    image: Image.Image,
    mask: Image.Image,
    prompt: str,
    negative: str,
    denoise: float,
    seed: int,
) -> Image.Image:
    w, h = image.size
    payload = {
        "init_images": [b64_png(image.convert("RGB"))],
        "mask": b64_png(mask.convert("L")),
        "prompt": prompt,
        "negative_prompt": negative,
        "denoising_strength": denoise,
        "steps": 28,
        "cfg_scale": 5.5,
        "width": w,
        "height": h,
        "seed": seed,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "mask_blur": 6,
        "inpainting_fill": 1,
        "inpaint_full_res": True,
        "inpaint_full_res_padding": 48,
        "inpainting_mask_invert": 0,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": {"ADetailer": {"args": [False]}},
    }
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = r.json()["images"][0]
    if "," in raw[:40]:
        raw = raw.split(",", 1)[1]
    return Image.open(BytesIO(base64.b64decode(raw))).convert("RGB")


def overlay(im: Image.Image, boxes: list[tuple[str, tuple[int, int, int, int], tuple[int, int, int]]]) -> Image.Image:
    vis = im.copy()
    d = ImageDraw.Draw(vis)
    for name, box, color in boxes:
        d.rectangle(list(box), outline=color, width=3)
        d.text((box[0] + 4, max(0, box[1] - 14)), name, fill=color)
    return vis


def main() -> int:
    if "--scrunchy" in sys.argv:
        requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=20).raise_for_status()
        requests.post(f"{FORGE}/sdapi/v1/options", json={"sd_model_checkpoint": CKPT}, timeout=600)
        src = OUT_DIR / "darkness_licks_v3.png"
        if not src.is_file():
            src = OUT_DIR / "darkness_licks_v2.png"
        if not src.is_file():
            src = SRC
        im = Image.open(src).convert("RGB")
        w, h = im.size
        box = (4, 858, 258, 1024)
        mask = ellipse_mask((w, h), box, blur=5)
        print("PASS scrunchy red remnants -> solid black", box, src.name, flush=True)
        cur = forge_inpaint(
            image=im,
            mask=mask,
            prompt=(
                "masterpiece, best quality, anime++, "
                "nbk_darkness, blonde ponytail, "
                "solid black scrunchy, matte black hair tie, no red"
            ),
            negative=NEG + ", red scrunchy, red ribbon, red piping, red trim, red bow, crimson, scarlet",
            denoise=0.52,
            seed=541124282,
        )
        dest = OUT_DIR / "darkness_licks_v4.png"
        cur.save(dest)
        cur.save(WORK_DIR / "darkness_licks_v4.png")
        print("OK", dest, dest.stat().st_size, flush=True)
        return 0

    ping = requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=20)
    ping.raise_for_status()
    requests.post(f"{FORGE}/sdapi/v1/options", json={"sd_model_checkpoint": CKPT}, timeout=600)

    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    vis = overlay(
        im,
        [
            ("frieren", BOX_FRIEREN, (0, 220, 80)),
            ("dark_eyes", BOX_DARKNESS_EYES, (255, 200, 40)),
        ],
    )
    vis.save(DEBUG / "_face_pass_boxes.png")

    m_f = ellipse_mask((w, h), BOX_FRIEREN)
    m_d = ellipse_mask((w, h), BOX_DARKNESS_EYES)
    m_f.save(DEBUG / "_mask_frieren_face.png")
    m_d.save(DEBUG / "_mask_darkness_eyes.png")

    print("PASS 1 Frieren face / green eyes", flush=True)
    cur = forge_inpaint(
        image=im,
        mask=m_f,
        prompt=PROMPT_FRIEREN,
        negative=NEG + ", blue eyes, blonde hair, brown eyes",
        denoise=0.32,
        seed=541124279,
    )
    mid = OUT_DIR / "darkness_licks_face_frieren_v1.png"
    cur.save(mid)
    print("  saved", mid, flush=True)

    print("PASS 2 Darkness eyes / dark blue — mouth unmasked", flush=True)
    cur = forge_inpaint(
        image=cur,
        mask=m_d,
        prompt=PROMPT_DARKNESS,
        negative=NEG + ", green eyes, purple eyes, white hair, silver hair",
        denoise=0.28,
        seed=541124280,
    )
    dest = OUT_DIR / "darkness_licks_v2.png"
    cur.save(dest)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    cur.save(WORK_DIR / "darkness_licks_v2.png")
    meta = {
        "src": str(SRC),
        "frieren_box": list(BOX_FRIEREN),
        "darkness_eyes_box": list(BOX_DARKNESS_EYES),
        "denoise_frieren": 0.32,
        "denoise_darkness": 0.28,
        "out": str(dest),
    }
    (OUT_DIR / "darkness_licks_v2.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("OK", dest, dest.stat().st_size, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
