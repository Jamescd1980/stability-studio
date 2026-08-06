"""FLF2V: HQ still as BOTH first and last (identity lock). Stroke mid, return to still."""
from __future__ import annotations

import json
import secrets
import shutil
import sys
from pathlib import Path

from PIL import Image
import numpy as np

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
# ~2s — two micro strokes returning to same still (4n+1)
LENGTH = 33


def content_fit(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    arr = np.asarray(im.convert("RGB"))
    mask = arr.mean(axis=2) > 12
    ys, xs = np.where(mask)
    if len(ys):
        im = im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return im.convert("RGB").resize(size, Image.Resampling.LANCZOS)


def prep_same_still() -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    still = content_fit(Image.open(STILL), (W, H))
    first = OUT_DIR / "WF04_flf_same_first.png"
    last = OUT_DIR / "WF04_flf_same_last.png"
    still.save(first)
    shutil.copy2(first, last)
    print(f"first=last={first} (identical HQ still)", flush=True)
    return first, last


def main() -> int:
    first, last = prep_same_still()
    cfg = load_config()
    comfy_url = str((cfg.get("comfyui") or {}).get("url") or "http://192.168.50.57:8188")
    comfy = ComfyUIClient(comfy_url, timeout=3600)
    if not comfy.is_running():
        print(f"ComfyUI not running at {comfy_url}", flush=True)
        return 2

    assert_backend_available(cfg, "comfyui", comfyui_running=True, operation="generate_video")
    acquire_gpu_lock(cfg, "comfyui", detail="generate_video mode=flf2v same_still")
    try:
        start_name = comfy.upload_image(first)
        end_name = comfy.upload_image(last)
        print(f"uploaded start={start_name} end={end_name}", flush=True)

        w, h = fit_i2v_dimensions(W, H, 960, 960)
        seed = secrets.randbelow(2**31 - 1)
        prompt = (
            "doggy style sex, two short hip thrusts in and out then settle back to start pose, "
            "strap stays inside, hips only, return to same pose"
        )
        negative = (
            "talking, mouth moving, lip sync, facial animation, head turn, "
            "glowing eyes, blank eyes, deformed eyes, camera pan, zoom, morphing, "
            "melting, full withdrawal, penis exit, deflating cock, blurry, low quality"
        )
        api = build_wan22_flf2v_moe_api(
            start_image_name=start_name,
            end_image_name=end_name,
            prompt=prompt + ", natural hands, anatomically correct",
            negative=negative,
            width=w,
            height=h,
            length=LENGTH,
            seed=seed,
            frame_rate=16.0,
            filename_prefix="studio_agent_wan22_flf_same",
            high_loras=[("wan2.2-i2v-high-doggy-style-sex-14b.safetensors", 0.55)],
            low_loras=[("wan2.2-i2v-low-doggy-style-sex-14b.safetensors", 0.55)],
            preset="quality",
            use_lightning=False,
        )
        print(f"submit FLF2V same-still {w}x{h} len={LENGTH} seed={seed}", flush=True)
        prompt_id = comfy.queue_prompt(api)
        print(f"prompt_id={prompt_id}", flush=True)
        hist = comfy.wait_for_completion(prompt_id)
        dest_dir = Path(r"D:\ComfyBox Images and Videos\Video")
        saved = []
        for info in comfy.collect_outputs(hist):
            out = comfy.download_file(info, dest_dir, cfg=cfg)
            saved.append(str(out))
            print(f"saved {out}", flush=True)
        print(json.dumps({"ok": bool(saved), "prompt_id": prompt_id, "saved_files": saved, "seed": seed}, indent=2))
        return 0 if saved else 1
    finally:
        release_gpu_lock(cfg, "comfyui")


if __name__ == "__main__":
    raise SystemExit(main())
