"""Invoke-style region focus on Forge: inpaint_full_res on a bbox/ellipse mask.

Concentrates diffusion on a small frame (face/head/feet) at higher effective
resolution, then composites back — no separate crop-paste workflow.

Usage examples:
  # Auto face frame from YOLO @2x
  python _region_inpaint_forge.py --image path.png --auto-face --prompt \"...\"

  # Manual frame (pixels)
  python _region_inpaint_forge.py --image path.png --box 540,100,700,290 --prompt \"...\"

Forge must be running (switch_stills_backend forge / gpu_backend.sh forge).
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import forge_url  # noqa: E402


def _b64_file(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


def _auto_face_box(im: Image.Image) -> tuple[int, int, int, int]:
    from ultralytics import YOLO

    w, h = im.size
    scale = 2
    yolo_path = Path(
        r"D:\sd-webui-forge\models\diffusers\models--Bingsu--adetailer"
        r"\snapshots\53cc19de382014514d9d4038601d261a7faa9b7b\face_yolov8s.pt"
    )
    yolo = YOLO(str(yolo_path))
    big = np.array(im.resize((w * scale, h * scale), Image.Resampling.BICUBIC))
    det = yolo.predict(big, conf=0.08, verbose=False)[0]
    if det.boxes is None or len(det.boxes) == 0:
        raise SystemExit("no face detected — pass --box x1,y1,x2,y2")
    box = det.boxes.xyxy.cpu().numpy()[0] / scale
    x1, y1, x2, y2 = map(int, box)
    bw, bh = x2 - x1, y2 - y1
    # Tight face-only frame (Invoke-style zoom on face, not full head/neck).
    pad_x, pad_y = int(bw * 0.06), int(bh * 0.08)
    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(w, x2 + pad_x),
        min(h, y2 + pad_y),
    )


def _ellipse_mask(size: tuple[int, int], box: tuple[int, int, int, int], blur: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(list(box), fill=255)
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return mask


def region_inpaint(
    *,
    image: Path,
    box: tuple[int, int, int, int],
    prompt: str,
    negative: str,
    denoise: float,
    seed: int,
    padding: int,
    out: Path,
) -> Path:
    cfg = load_config()
    url = forge_url(cfg)
    im = Image.open(image).convert("RGB")
    w, h = im.size
    mask = _ellipse_mask((w, h), box, blur=5)
    mask_path = out.with_name(out.stem + "_mask.png")
    mask.save(mask_path)
    # draw frame preview
    prev = im.copy()
    ImageDraw.Draw(prev).rectangle(list(box), outline=(255, 60, 60), width=3)
    prev.save(out.with_name(out.stem + "_frame.png"))

    payload = {
        "init_images": [_b64_file(image)],
        "mask": _b64_file(mask_path),
        "prompt": prompt,
        "negative_prompt": negative,
        "denoising_strength": denoise,
        "steps": 28,
        "cfg_scale": 5.5,
        "width": w,
        "height": h,
        "sampler_name": "Euler a",
        "seed": seed,
        "mask_blur": 4,
        "inpainting_fill": 1,
        "inpaint_full_res": True,
        "inpaint_full_res_padding": padding,
    }
    r = requests.post(f"{url}/sdapi/v1/img2img", json=payload, timeout=600)
    r.raise_for_status()
    raw = r.json()["images"][0]
    if "," in raw[:40]:
        raw = raw.split(",", 1)[1]
    out.write_bytes(base64.b64decode(raw))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", required=True)
    ap.add_argument("--box", default="", help="x1,y1,x2,y2")
    ap.add_argument("--auto-face", action="store_true")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative", default="blurry, lowres, deformed")
    ap.add_argument("--denoise", type=float, default=0.42)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--padding", type=int, default=72)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    image = Path(args.image)
    im = Image.open(image)
    if args.auto_face:
        box = _auto_face_box(im)
    else:
        if not args.box:
            raise SystemExit("pass --auto-face or --box x1,y1,x2,y2")
        box = tuple(int(x) for x in args.box.split(","))  # type: ignore
        if len(box) != 4:
            raise SystemExit("box must be x1,y1,x2,y2")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    region_inpaint(
        image=image,
        box=box,  # type: ignore
        prompt=args.prompt,
        negative=args.negative,
        denoise=args.denoise,
        seed=args.seed,
        padding=args.padding,
        out=out,
    )
    print("saved", out)
    print("frame", out.with_name(out.stem + "_frame.png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
