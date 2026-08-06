"""Forge full-image upscale for Wild Fern keepers (no ADetailer)."""
from __future__ import annotations

import base64
import json
import shutil
import sys
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

REVIEW = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\review"
)
GAME = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\Movie_WildFern")
FORGE = "http://192.168.50.57:7860"

# review source → game install name → forge out stem
JOBS = [
    ("fern_licks_v2.png", "Movie_WildFern_01_fern_licks.png", "fern_licks_forge_v1"),
    ("fern_facesit_v4.png", "Movie_WildFern_02_darkness_licks.png", "fern_facesit_forge_v1"),
    ("fern_revcowgirl_v1.png", "Movie_WildFern_03_fern_revcowgirl.png", "fern_revcowgirl_forge_v1"),
    ("fern_doggy_v1.png", "Movie_WildFern_04_fern_doggy.png", "fern_doggy_forge_v1"),
    ("aftercare_v0.png", "Movie_WildFern_05_aftercare.png", "fern_aftercare_forge_v1"),
]

PROMPT = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
    "bold outline, cel-shaded coloring, sharp details, clean linework, "
    "loft bedroom at night, warm bedside lamp light, purple sheets, "
    "high quality skin, detailed"
)
NEG = (
    "lowres, bad anatomy, bad hands, blurry, watermark, text, "
    "man, male, penis, daytime, clothes, lingerie"
)


def wait_forge(timeout: float = 180) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=5)
            if r.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError("Forge API not reachable")


def b64_png(path: Path) -> str:
    im = Image.open(path).convert("RGB")
    buf = BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def forge_upscale(src: Path, dest: Path, *, tw: int, th: int, seed: int) -> dict:
    im = Image.open(src)
    w, h = im.size
    # keep aspect: square keepers stay square
    if w == h:
        out_w = out_h = tw
    else:
        out_w, out_h = tw, int(th * h / w)
    payload = {
        "init_images": [b64_png(src)],
        "prompt": PROMPT,
        "negative_prompt": NEG,
        "denoising_strength": 0.30,
        "steps": 28,
        "cfg_scale": 5.5,
        "width": out_w,
        "height": out_h,
        "sampler_name": "Euler a",
        "scheduler": "Automatic",
        "seed": seed,
        "resize_mode": 0,
        "batch_size": 1,
    }
    print(f"  POST {w}x{h} -> {out_w}x{out_h} denoise 0.30", flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=2400)
    r.raise_for_status()
    img = r.json()["images"][0]
    if "," in img:
        img = img.split(",", 1)[1]
    dest.write_bytes(base64.b64decode(img))
    size = Image.open(dest).size
    return {"ok": True, "path": str(dest), "size": size, "bytes": dest.stat().st_size}


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    GAME.mkdir(parents=True, exist_ok=True)
    wait_forge()
    print("set checkpoint…", flush=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": "waijfu_alpha.safetensors"},
        timeout=600,
    )
    results = []
    # Prefer 1536; on failure retry 1280 then 1024
    targets = [1536, 1280, 1024]
    for i, (src_name, game_name, stem) in enumerate(JOBS):
        src = REVIEW / src_name
        if not src.is_file():
            # fallback game copy
            g = GAME / game_name
            if g.is_file():
                src = g
            else:
                print("MISSING", src_name, flush=True)
                results.append({"name": stem, "ok": False, "error": "missing"})
                continue
        dest = REVIEW / f"{stem}.png"
        print(f"=== {stem} from {src.name}", flush=True)
        last_err = None
        for tw in targets:
            try:
                info = forge_upscale(src, dest, tw=tw, th=tw, seed=47001 + i)
                info["name"] = stem
                info["target"] = tw
                # install
                shutil.copy2(dest, GAME / game_name)
                print(f"  OK {dest.name} {info['size']} -> game {game_name}", flush=True)
                results.append(info)
                last_err = None
                break
            except Exception as exc:
                last_err = str(exc)
                print(f"  FAIL @{tw}: {exc}", flush=True)
                time.sleep(2)
        if last_err and not any(r.get("name") == stem and r.get("ok") for r in results):
            results.append({"name": stem, "ok": False, "error": last_err})
    (REVIEW / "_forge_upscale_batch.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
