"""Das Booty DB-08..DB-10 — same v3 face pass as 01–07, then pad into game."""
from __future__ import annotations

import base64
import json
import shutil
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageFilter
from send2trash import send2trash

FORGE = "http://127.0.0.1:7860"
SRC_DIR = Path(r"D:\ComfyBox Images and Videos\User Import\Photo Shoots\Das Booty")
OUT_DIR = SRC_DIR / "_face_pass"
GAME_DIR = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\das_booty")
CHECKPOINT = "waijfu_alpha.safetensors"
W, H = 1920, 1080

JOBS = [
    ("DB-08", "DB-08.png"),
    ("DB-09", "DB-09.png"),
    ("DB-10", "DB-10.png"),
]

CHAR = (
    "nb_frieren, frieren, elf girl, long silver white hair, twin tails, "
    "pointed ears, red teardrop earrings, matte green eyes, pale skin, "
    "closed mouth, disdainful sneer, lips pressed together, looking at viewer, "
    "masterpiece, best quality, highly detailed, sharp focus, crisp lines, "
    "anime illustration, <lora:Frieren:0.75>"
)
FACE_AD = (
    "nb_frieren, frieren, detailed face, "
    "matte green eyes, dark pupils, soft muted green iris, no glow, "
    "ordinary anime eyes, subtle white catchlight only, "
    "closed mouth, lips fully closed, no teeth visible, no fang, "
    "disdainful sneer with closed lips, crisp anime face, "
    "<lora:Frieren:0.7>"
)
NEG = (
    "lowres, blurry, soft focus, oversmoothed, plastic skin, bad anatomy, "
    "watermark, text, worst quality, "
    "glowing eyes, luminous eyes, neon eyes, bright glowing green eyes, "
    "emissive eyes, light emitting eyes, oversaturated eyes, "
    "snaggletooth, fang, fangs, uneven teeth, buck teeth, shark teeth, "
    "open mouth, tongue out, "
    "smile, happy, soft smile, open mouth smile, friendly expression, "
    "dull eyes, empty eyes, deformed eyes, crossed eyes, "
    "wrong face, different character"
)
SCENE = (
    ", pirate theme, black bandana, skull bandana, wet skin, "
    "looking down at viewer, low angle, ship deck, outdoor daylight"
)
AD_NEG = (
    "blurry face, soft face, dull eyes, deformed eyes, "
    "glowing eyes, luminous eyes, neon eyes, emissive eyes, "
    "snaggletooth, fang, fangs, uneven teeth, open mouth, "
    "smile, happy smile, friendly, soft expression"
)


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _set_checkpoint() -> None:
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CHECKPOINT},
        timeout=180,
    )
    time.sleep(2)


def _refine(src: Path, dest: Path) -> dict:
    with Image.open(src) as im:
        w, h = im.size
    payload = {
        "init_images": [_b64(src)],
        "prompt": CHAR + SCENE,
        "negative_prompt": NEG,
        "denoising_strength": 0.06,
        "steps": 28,
        "cfg_scale": 5.0,
        "width": w,
        "height": h,
        "sampler_name": "Euler a",
        "seed": -1,
        "resize_mode": 0,
        "batch_size": 1,
        "alwayson_scripts": {
            "adetailer": {
                "args": [
                    True,
                    False,
                    {
                        "ad_model": "face_yolov8n.pt",
                        "ad_tab_enable": True,
                        "ad_prompt": FACE_AD,
                        "ad_negative_prompt": AD_NEG,
                        "ad_confidence": 0.25,
                        "ad_dilate_erode": 4,
                        "ad_mask_blur": 4,
                        "ad_denoising_strength": 0.48,
                        "ad_inpaint_only_masked": True,
                        "ad_inpaint_only_masked_padding": 32,
                    },
                ]
            }
        },
    }
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=900)
    r.raise_for_status()
    images = (r.json().get("images") or [])
    if not images:
        return {"ok": False, "error": "no images"}
    raw = images[0]
    if "," in raw[:64]:
        raw = raw.split(",", 1)[1]
    dest.write_bytes(base64.b64decode(raw))
    return {"ok": True, "output": str(dest)}


def pad_blur(src: Path, dst: Path) -> None:
    im = Image.open(src).convert("RGB")
    bg = im.copy()
    bg.thumbnail((W * 2, H * 2), Image.Resampling.LANCZOS)
    scale = max(W / bg.width, H / bg.height)
    bw, bh = int(bg.width * scale) + 2, int(bg.height * scale) + 2
    bg = bg.resize((bw, bh), Image.Resampling.LANCZOS)
    left = (bw - W) // 2
    top = (bh - H) // 2
    bg = bg.crop((left, top, left + W, top + H))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=28))
    arr = (np.asarray(bg).astype(np.float32) * 0.55).clip(0, 255).astype(np.uint8)
    canvas = Image.fromarray(arr, "RGB")
    fg = im.copy()
    fg.thumbnail((W, H), Image.Resampling.LANCZOS)
    canvas.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    if dst.is_file():
        send2trash(str(dst))
    canvas.save(dst, "PNG")
    print(f"PAD {dst.name} plate={fg.size}", flush=True)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GAME_DIR.mkdir(parents=True, exist_ok=True)
    try:
        requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=5).raise_for_status()
    except Exception as exc:
        print(f"Forge not reachable: {exc}", flush=True)
        return 1
    print("Setting checkpoint", CHECKPOINT, flush=True)
    _set_checkpoint()

    results = []
    for stem, fname in JOBS:
        src = SRC_DIR / fname
        if not src.is_file():
            print("MISSING", fname, flush=True)
            results.append({"ok": False, "stem": stem, "error": "missing"})
            continue
        face = OUT_DIR / f"{stem}_face.png"
        print(f"=== FACE {src.name} -> {face.name} ===", flush=True)
        try:
            r = _refine(src, face)
        except Exception as exc:
            print("FAIL", stem, exc, flush=True)
            results.append({"ok": False, "stem": stem, "error": str(exc)})
            continue
        if not r.get("ok"):
            print("FAIL", stem, r, flush=True)
            results.append({"ok": False, "stem": stem, "result": r})
            continue
        game = GAME_DIR / f"das_booty_{stem.split('-')[1]}.png"
        pad_blur(face, game)
        print("OK", face, "->", game, flush=True)
        results.append({"ok": True, "stem": stem, "face": str(face), "game": str(game)})

    note = OUT_DIR / "_das_booty_face_pass_08_10_note.json"
    summary = {"ok": all(x.get("ok") for x in results), "results": results}
    note.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("DONE", note, "ok=", summary["ok"], flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
