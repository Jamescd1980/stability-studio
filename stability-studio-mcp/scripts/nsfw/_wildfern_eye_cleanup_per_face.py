"""Wild Fern eye cleanup — one face at a time (Fern purple / Darkness blue).

Detect faces → classify by hair color → Forge inpaint each face separately.
Jobs: kiss (both), fern_licks (Fern only), facesit (Fern only). No doggy.
"""
from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

FORGE = "http://127.0.0.1:7860"
CKPT = "waijfu_alpha.safetensors"
FORGE_DIR = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften"
)
OUT = FORGE_DIR / "_eye_clean"
SEED = 62024
DENOISE = 0.32  # face-masked inpaint only

NEG = (
    "lens flare, eye flare, sparkle eyes, glowing eyes, starburst eyes, "
    "star pupils, bright catchlights, overexposed eyes, specular eyes, "
    "oily glare, wrong eye color, heterochromia, "
    "camera, dslr, blurry, bad anatomy, changed hair color"
)
AD_NEG_EXTRA_FERN = ", blue eyes, blonde"
AD_NEG_EXTRA_DARK = ", purple eyes, purple hair"

PROMPT_FERN = (
    "masterpiece, best quality, anime++, "
    "Fern face, purple hair, purple irises, purple eyes, "
    "soft diffuse catchlights, detailed iris, round pupils, "
    "clean eyes, no glare, no flare, matte skin"
)
PROMPT_DARK = (
    "masterpiece, best quality, anime++, "
    "Darkness face, blonde hair, blue irises, blue eyes, "
    "soft diffuse catchlights, detailed iris, round pupils, "
    "clean eyes, no glare, no flare, matte skin"
)

JOBS = [
    dict(
        id="01_kiss",
        src=FORGE_DIR / "Movie_WildFern_01_kiss_forge_soften.png",
        want=("fern", "darkness"),
    ),
    dict(
        id="02_fern_licks",
        src=FORGE_DIR / "Movie_WildFern_02_fern_licks_forge_soften.png",
        want=("fern",),
    ),
    dict(
        id="facesit",
        src=FORGE_DIR / "facesit_darkness_pov_city_KEEP.png",
        want=("fern",),
    ),
]


_FACE_WEIGHTS = Path(
    r"D:\sd-webui-forge\models\diffusers\models--Bingsu--adetailer"
    r"\snapshots\53cc19de382014514d9d4038601d261a7faa9b7b\face_yolov8n.pt"
)
_yolo = None


def detect_faces(rgb: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Return face boxes (x,y,w,h) via ultralytics face_yolov8n."""
    global _yolo
    from ultralytics import YOLO

    if _yolo is None:
        _yolo = YOLO(str(_FACE_WEIGHTS))
    h, w = rgb.shape[:2]
    res = _yolo.predict(rgb, conf=0.35, verbose=False)
    boxes: list[tuple[int, int, int, int]] = []
    if not res:
        return boxes
    for r in res:
        if r.boxes is None:
            continue
        for b in r.boxes.xyxy.cpu().numpy():
            x0, y0, x1, y1 = [int(v) for v in b[:4]]
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(w, x1), min(h, y1)
            bw, bh = x1 - x0, y1 - y0
            if bw > 20 and bh > 20:
                boxes.append((x0, y0, bw, bh))
    boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
    return boxes


def hair_scores(rgb: np.ndarray, box: tuple[int, int, int, int]) -> tuple[float, float]:
    """Return (purple_score, blonde_score) from upper hair band of face box."""
    x, y, bw, bh = box
    # hair band: above eyes — top 45% of face box, expand upward
    y0 = max(0, y - int(bh * 0.35))
    y1 = y + int(bh * 0.45)
    x0, x1 = x, x + bw
    band = rgb[y0:y1, x0:x1]
    if band.size == 0:
        return 0.0, 0.0
    r, g, b = band[..., 0].astype(np.float32), band[..., 1].astype(np.float32), band[..., 2].astype(np.float32)
    # purple/magenta: r and b high, g lower
    purple = ((r > 90) & (b > 90) & (r > g + 15) & (b > g + 10)).mean()
    # blonde: high r+g, lower b, not too dark
    luma = (r + g + b) / 3
    blonde = ((luma > 120) & (r > 130) & (g > 110) & (b < g + 20) & (r > b + 25)).mean()
    return float(purple), float(blonde)


def classify_faces(
    rgb: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
    want: tuple[str, ...],
) -> dict[str, tuple[int, int, int, int]]:
    """Map role -> box using hair color (purple=Fern, blonde=Darkness)."""
    scored = []
    for box in boxes:
        p, bl = hair_scores(rgb, box)
        scored.append((box, p, bl))
        print(f"    box={box} purple={p:.3f} blonde={bl:.3f}", flush=True)
    out: dict[str, tuple[int, int, int, int]] = {}
    if not scored:
        return out
    if want == ("fern",) and len(scored) == 1:
        out["fern"] = scored[0][0]
        return out
    # Fern = highest purple score
    if "fern" in want:
        out["fern"] = max(scored, key=lambda t: t[1])[0]
    if "darkness" in want:
        rest = [t for t in scored if t[0] != out.get("fern")]
        pool = rest if rest else scored
        out["darkness"] = max(pool, key=lambda t: t[2])[0]
    return out


def face_mask(size: tuple[int, int], box: tuple[int, int, int, int], pad: float = 0.15) -> Image.Image:
    w, h = size
    x, y, bw, bh = box
    px, py = int(bw * pad), int(bh * pad)
    x0, y0 = max(0, x - px), max(0, y - py)
    x1, y1 = min(w, x + bw + px), min(h, y + bh + py)
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    # ellipse covering face
    draw.ellipse([x0, y0, x1, y1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=10))
    return mask


def b64_png(im: Image.Image) -> str:
    buf = BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def forge_inpaint(
    *,
    image: Image.Image,
    mask: Image.Image,
    prompt: str,
    negative: str,
    seed: int,
) -> Image.Image:
    w, h = image.size
    payload = {
        "init_images": [b64_png(image.convert("RGB"))],
        "mask": b64_png(mask.convert("L")),
        "prompt": prompt,
        "negative_prompt": negative,
        "denoising_strength": DENOISE,
        "steps": 24,
        "cfg_scale": 5.0,
        "width": w,
        "height": h,
        "seed": seed,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "mask_blur": 8,
        "inpainting_fill": 1,  # original
        "inpaint_full_res": True,
        "inpaint_full_res_padding": 32,
        "inpainting_mask_invert": 0,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": {"ADetailer": {"args": [False]}},
    }
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    return Image.open(BytesIO(raw)).convert("RGB")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    results = []
    print("=== WF per-face eye clean (Fern purple / Darkness blue) ===", flush=True)
    for job in JOBS:
        src = job["src"]
        if not src.is_file():
            print("MISSING", src, flush=True)
            return 1
        im = Image.open(src).convert("RGB")
        rgb = np.asarray(im)
        boxes = detect_faces(rgb)
        roles = classify_faces(rgb, boxes, job["want"])
        print(f"{job['id']} faces={len(boxes)} roles={ {k:v for k,v in roles.items()} }", flush=True)
        # debug overlay
        dbg = im.copy()
        d = ImageDraw.Draw(dbg)
        for role, box in roles.items():
            x, y, bw, bh = box
            d.rectangle([x, y, x + bw, y + bh], outline=(0, 255, 0) if role == "fern" else (0, 128, 255), width=3)
            d.text((x, max(0, y - 14)), role, fill=(255, 255, 0))
        dbg.save(OUT / f"_{job['id']}_faces.png")

        cur = im
        seed = SEED
        for role in job["want"]:
            if role not in roles:
                print(f"  WARN no {role} face — skip", flush=True)
                continue
            box = roles[role]
            mask = face_mask(cur.size, box)
            mask.save(OUT / f"_{job['id']}_mask_{role}.png")
            if role == "fern":
                prompt = PROMPT_FERN
                neg = NEG + AD_NEG_EXTRA_FERN
            else:
                prompt = PROMPT_DARK
                neg = NEG + AD_NEG_EXTRA_DARK
            print(f"  inpaint {role}", flush=True)
            cur = forge_inpaint(image=cur, mask=mask, prompt=prompt, negative=neg, seed=seed)
            seed += 1

        dest = OUT / f"{job['id']}.png"
        cur.save(dest, "PNG")
        (OUT / f"{job['id']}.json").write_text(
            json.dumps(
                {
                    "id": job["id"],
                    "src": str(src),
                    "want": list(job["want"]),
                    "roles": {k: list(v) for k, v in roles.items()},
                    "denoise": DENOISE,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("  OK", dest.name, dest.stat().st_size, flush=True)
        results.append({"id": job["id"], "ok": True, "path": str(dest)})

    (OUT / "_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
