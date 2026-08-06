"""FLF2V: HQ still first=last, clone flf_00002 prompt/seed/length/LoRA."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.comfy_client import ComfyUIClient  # noqa: E402
from studio.config import load_config  # noqa: E402
from studio.gpu_backend import acquire_gpu_lock, assert_backend_available, release_gpu_lock  # noqa: E402
from studio.hardware_profile import fit_i2v_dimensions  # noqa: E402
from studio.wan22_flf2v_moe import build_wan22_flf2v_moe_api  # noqa: E402

STILL = Path(r"D:\ComfyBox Images and Videos\User Import\Movie_WildFern_04_darkness_strap.png")
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\User Import\FLF_WildFern")
W, H = 960, 544
# clone studio_agent_wan22_flf_00002.mp4
LENGTH = 21
SEED = 1100911941
PROMPT = (
    "they are having doggy style sex, one slow hip thrust forward then settle, "
    "strap stays inside, hips only, no multi pump, natural hands, anatomically correct"
)
NEGATIVE = (
    "talking, mouth moving, lip sync, facial animation, head turn, "
    "glowing eyes, blank eyes, deformed eyes, camera pan, zoom, morphing, "
    "melting, full withdrawal, penis exit, deflating cock, blurry, low quality"
)


def content_fit(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    arr = np.asarray(im.convert("RGB"))
    mask = arr.mean(axis=2) > 12
    ys, xs = np.where(mask)
    if len(ys):
        im = im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return im.convert("RGB").resize(size, Image.Resampling.LANCZOS)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    still = content_fit(Image.open(STILL), (W, H))
    first = OUT_DIR / "WF04_flf_clone00002_first.png"
    last = OUT_DIR / "WF04_flf_clone00002_last.png"
    still.save(first)
    shutil.copy2(first, last)
    print(f"first=last={first} (HQ still, clone 00002)", flush=True)

    cfg = load_config()
    comfy_url = str((cfg.get("comfyui") or {}).get("url") or "http://192.168.50.57:8188")
    comfy = ComfyUIClient(comfy_url, timeout=3600)
    if not comfy.is_running():
        print(f"ComfyUI not running at {comfy_url}", flush=True)
        return 2

    assert_backend_available(cfg, "comfyui", comfyui_running=True, operation="generate_video")
    acquire_gpu_lock(cfg, "comfyui", detail="generate_video flf2v clone00002")
    try:
        start_name = comfy.upload_image(first)
        end_name = comfy.upload_image(last)
        w, h = fit_i2v_dimensions(W, H, 960, 960)
        api = build_wan22_flf2v_moe_api(
            start_image_name=start_name,
            end_image_name=end_name,
            prompt=PROMPT,
            negative=NEGATIVE,
            width=w,
            height=h,
            length=LENGTH,
            seed=SEED,
            frame_rate=16.0,
            filename_prefix="studio_agent_wan22_flf_clone00002",
            high_loras=[("wan2.2-i2v-high-doggy-style-sex-14b.safetensors", 0.55)],
            low_loras=[("wan2.2-i2v-low-doggy-style-sex-14b.safetensors", 0.55)],
            preset="quality",
            use_lightning=False,
        )
        print(f"submit clone00002 FLF {w}x{h} len={LENGTH} seed={SEED}", flush=True)
        prompt_id = comfy.queue_prompt(api)
        print(f"prompt_id={prompt_id}", flush=True)
        hist = comfy.wait_for_completion(prompt_id)
        dest_dir = Path(r"D:\ComfyBox Images and Videos\Video")
        saved = []
        for info in comfy.collect_outputs(hist):
            out = comfy.download_file(info, dest_dir, cfg=cfg)
            saved.append(str(out))
            print(f"saved {out}", flush=True)
        print(json.dumps({"ok": bool(saved), "prompt_id": prompt_id, "saved_files": saved, "seed": SEED}, indent=2))
        return 0 if saved else 1
    finally:
        release_gpu_lock(cfg, "comfyui")


if __name__ == "__main__":
    raise SystemExit(main())
