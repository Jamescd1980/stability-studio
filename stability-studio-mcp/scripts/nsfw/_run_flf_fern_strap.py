"""FLF2V for Movie_WildFern_05 fern_strap (next parallel link)."""
from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.comfy_client import ComfyUIClient  # noqa: E402
from studio.config import load_config  # noqa: E402
from studio.gpu_backend import acquire_gpu_lock, assert_backend_available, release_gpu_lock  # noqa: E402
from studio.hardware_profile import fit_i2v_dimensions  # noqa: E402
from studio.wan22_flf2v_moe import build_wan22_flf2v_moe_api  # noqa: E402

STILL = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\Movie_WildFern\Movie_WildFern_05_fern_strap.png")
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\User Import\FLF_WildFern")
W, H = 960, 544


def content_fit(im: Image.Image) -> Image.Image:
    arr = np.asarray(im.convert("RGB"))
    mask = arr.mean(2) > 12
    ys, xs = np.where(mask)
    if len(ys):
        im = im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return im.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    still = content_fit(Image.open(STILL))
    first = OUT_DIR / "WF05_flf_first.png"
    still.save(first)
    # Micro end: slight affine hip nudge + smooth
    last_im = still.transform(
        (W, H),
        Image.Transform.AFFINE,
        (1, 0, 0, 0.015, 1, -3),
        resample=Image.Resampling.BICUBIC,
    ).filter(ImageFilter.SMOOTH)
    last = OUT_DIR / "WF05_flf_last.png"
    last_im.save(last)

    cfg = load_config()
    url = str((cfg.get("comfyui") or {}).get("url") or "http://192.168.50.57:8188")
    comfy = ComfyUIClient(url, timeout=3600)
    assert_backend_available(cfg, "comfyui", comfyui_running=True, operation="generate_video")
    acquire_gpu_lock(cfg, "comfyui", detail="generate_video mode=flf2v fern_strap")
    try:
        start = comfy.upload_image(first)
        end = comfy.upload_image(last)
        w, h = fit_i2v_dimensions(W, H, 960, 960)
        seed = secrets.randbelow(2**31 - 1)
        api = build_wan22_flf2v_moe_api(
            start_image_name=start,
            end_image_name=end,
            prompt=(
                "they are having doggy style sex, purple hair woman behind blonde, "
                "one slow hip thrust forward then settle, strap stays inside, hips only, "
                "natural hands, anatomically correct"
            ),
            negative=(
                "talking, mouth moving, facial animation, glowing eyes, blank eyes, "
                "camera pan, zoom, morphing, melting, full withdrawal, penis exit"
            ),
            width=w,
            height=h,
            length=21,
            seed=seed,
            filename_prefix="studio_agent_wan22_flf_fernstrap",
            high_loras=[("wan2.2-i2v-high-doggy-style-sex-14b.safetensors", 0.55)],
            low_loras=[("wan2.2-i2v-low-doggy-style-sex-14b.safetensors", 0.55)],
            preset="quality",
            use_lightning=False,
        )
        print(f"submit fern_strap FLF {w}x{h} seed={seed}", flush=True)
        pid = comfy.queue_prompt(api)
        print(f"prompt_id={pid}", flush=True)
        hist = comfy.wait_for_completion(pid)
        dest = Path(r"D:\ComfyBox Images and Videos\Video")
        saved = [str(comfy.download_file(i, dest, cfg=cfg)) for i in comfy.collect_outputs(hist)]
        print(json.dumps({"ok": bool(saved), "saved_files": saved, "seed": seed}, indent=2), flush=True)
        return 0 if saved else 1
    finally:
        release_gpu_lock(cfg, "comfyui")


if __name__ == "__main__":
    raise SystemExit(main())
