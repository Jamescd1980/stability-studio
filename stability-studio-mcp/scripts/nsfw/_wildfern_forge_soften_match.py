"""Wild Fern Forge soften — match Saloon hero_forge look (local Forge)."""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import refine_image_forge  # noqa: E402
import studio.forge_backend as fb  # noqa: E402
import studio.gpu_backend as gb  # noqa: E402

GAME = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\Movie_WildFern")
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften"
)
FORGE = "http://127.0.0.1:7860"

# game filename -> mode
JOBS = [
    ("Movie_WildFern_01_kiss.png", "body"),
    ("Movie_WildFern_02_fern_licks.png", "body"),
    ("Movie_WildFern_03_darkness_licks.png", "body"),
    ("Movie_WildFern_04_fern_revcowgirl.png", "body"),
    ("Movie_WildFern_05_fern_doggy.png", "body"),
    ("Movie_WildFern_06_aftercare.png", "body"),
]

PROMPT = (
    "masterpiece, best quality, anime++, soft diffused lighting, "
    "gentle rim light, matte skin, reduced specular, natural eyes, "
    "clean iris, round pupils, consistent faces, warm bedroom light"
)
NEG = (
    "overexposed, harsh specular, oily skin glare, blown highlights, "
    "lens flare, eye flare, sparkle eyes, glowing eyes, starburst eyes, "
    "plastic skin, blurry, bad anatomy, extra fingers, "
    "camera, dslr, camcorder, watermark, text"
)
AD_FACE = (
    "anime face, soft diffuse catchlights, detailed iris, round pupils, "
    "clean eyes, soft lighting, natural skin"
)
AD_NEG = (
    "lens flare, eye flare, bright catchlights, sparkle eyes, glowing eyes, "
    "starburst, star pupils, overexposed eyes, specular eyes, oily glare"
)


def wait_forge(timeout_s: int = 600) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=5).ok:
                print(f"Forge up after {time.time()-t0:.0f}s", flush=True)
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise RuntimeError("Local Forge not up")


def rgb_temp(src: Path, tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / src.name
    with Image.open(src) as im:
        im.convert("RGB").save(dest, format="PNG")
    return dest


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_rgb_tmp"
    wait_forge()
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": "waijfu_alpha.safetensors"},
        timeout=600,
    )
    cfg = load_config()
    cfg.setdefault("forge", {})
    cfg["forge"]["url"] = FORGE
    cfg["forge"]["generate_timeout_seconds"] = 1800
    gb.comfyui_is_reachable = lambda _cfg=None: False  # type: ignore
    fb.comfyui_is_reachable = lambda _cfg=None: False  # type: ignore

    results = []
    for i, (name, _mode) in enumerate(JOBS, 1):
        src = GAME / name
        dest = OUT / f"{Path(name).stem}_forge_soften.png"
        if not src.is_file():
            print("MISSING", name, flush=True)
            results.append({"name": name, "ok": False, "error": "missing"})
            continue
        if dest.is_file() and dest.stat().st_size > 50_000:
            print(f"[{i}/{len(JOBS)}] SKIP {dest.name}", flush=True)
            results.append({"name": name, "ok": True, "path": str(dest), "skipped": True})
            continue
        print(f"[{i}/{len(JOBS)}] {name}", flush=True)
        try:
            rgb = rgb_temp(src, tmp)
            r = refine_image_forge(
                cfg,
                image_path=str(rgb),
                prompt=PROMPT,
                negative_prompt=NEG,
                checkpoint="waijfu_alpha.safetensors",
                denoising_strength=0.22,
                steps=28,
                cfg_scale=5.0,
                seed=62024,
                adetailer=True,
                ad_model="face_yolov8n.pt",
                ad_prompt=AD_FACE,
                ad_negative=AD_NEG,
                ad_denoising_strength=0.30,
                ad_dilate_erode=4,
                ad_mask_padding=32,
            )
            if not r.get("ok") or not r.get("saved_files"):
                raise RuntimeError(r.get("error") or "no saved_files")
            shutil.copy2(r["saved_files"][0], dest)
            print("  OK", dest.name, flush=True)
            results.append({"name": name, "ok": True, "path": str(dest)})
        except Exception as e:
            print("  FAIL", e, flush=True)
            results.append({"name": name, "ok": False, "error": str(e)})

    summary = OUT / "_forge_soften_summary.json"
    summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok_n = sum(1 for x in results if x.get("ok"))
    print(f"DONE {ok_n}/{len(results)} -> {OUT}", flush=True)
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
