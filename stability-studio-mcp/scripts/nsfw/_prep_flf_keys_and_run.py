"""Prep FLF first/last keys for Wild Fern strap + submit Wan MoE FLF2V on ComfyBox.

NOTE (2026-07-31): Owner intent for FLF is HQ still as BOTH first and last.
Prefer scripts/nsfw/_run_flf_same_still.py. This script's face-composite last
from Wan guide mid is DEPRECATED for keepers (caused soft tail).
"""
from __future__ import annotations

import json
import secrets
import sys
import time
import urllib.request
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

STILL = Path(r"D:\ComfyBox Images and Videos\User Import\Movie_WildFern_04_darkness_strap.png")
GUIDE = Path(r"D:\ComfyBox Images and Videos\Video\studio_agent_wan22_moe_00153.mp4")
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\User Import\FLF_WildFern")
WORK = Path(r"D:\ComfyBox Images and Videos\temp\flf_fern_strap")
W, H = 960, 544
# ~1.3s @ 16fps — one micro thrust only (49f multi-thrust melts eyes)
LENGTH = 21  # Wan FLF wants 4n+1; builder snaps


def _content_fit(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    arr = np.asarray(im.convert("RGB"))
    mask = arr.mean(axis=2) > 12
    ys, xs = np.where(mask)
    if len(ys):
        im = im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return im.convert("RGB").resize(size, Image.Resampling.LANCZOS)


def _extract_frame(video: Path, t: float, dest: Path) -> None:
    import subprocess

    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", str(dest)],
        check=True,
        capture_output=True,
    )


def _face_composite(still: Image.Image, pose: Image.Image) -> Image.Image:
    """Keep pose body; blend upper faces from still (quality eyes at end key)."""
    s = np.asarray(still, dtype=np.float32)
    p = np.asarray(pose.resize(still.size, Image.Resampling.LANCZOS), dtype=np.float32)
    h, w = s.shape[:2]
    # Soft mask: top ~48% of frame (both faces in this CG), feathered
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    face_w = np.clip((0.52 - yy) / 0.12, 0, 1)  # 1 at top → 0 by ~52%
    face_w = np.repeat(face_w, w, axis=1)[:, :, None]
    # Slight horizontal center weight for faces
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    cx = np.exp(-((xx - 0.45) ** 2) / (2 * 0.22**2))
    cx = np.repeat(cx, h, axis=0)[:, :, None]
    m = np.clip(face_w * (0.55 + 0.45 * cx), 0, 1)
    out = p * (1 - m) + s * m
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def prep_keys() -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    still = _content_fit(Image.open(STILL), (W, H))
    first = OUT_DIR / "WF04_flf_first.png"
    still.save(first)

    mid_raw = WORK / "guide_mid.png"
    if GUIDE.is_file():
        _extract_frame(GUIDE, 1.5, mid_raw)
        pose = Image.open(mid_raw).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    else:
        # Fallback: tiny vertical hip nudge via affine
        pose = still.transform(
            (W, H),
            Image.Transform.AFFINE,
            (1, 0, 0, 0.02, 1, -4),
            resample=Image.Resampling.BICUBIC,
        )
    last_img = _face_composite(still, pose)
    last_img = last_img.filter(ImageFilter.SMOOTH_MORE)
    last = OUT_DIR / "WF04_flf_last.png"
    last_img.save(last)
    print(f"first={first}\nlast={last}", flush=True)
    return first, last


def upload(comfy: ComfyUIClient, path: Path) -> str:
    return comfy.upload_image(path)


def main() -> int:
    first, last = prep_keys()
    cfg = load_config()
    comfy_url = str((cfg.get("comfyui") or {}).get("url") or "http://192.168.50.57:8188")
    comfy = ComfyUIClient(comfy_url, timeout=3600)
    if not comfy.is_running():
        print(f"ComfyUI not running at {comfy_url}", flush=True)
        return 2

    assert_backend_available(cfg, "comfyui", comfyui_running=True, operation="generate_video")
    acquire_gpu_lock(cfg, "comfyui", detail="generate_video mode=flf2v")
    try:
        start_name = upload(comfy, first)
        end_name = upload(comfy, last)
        print(f"uploaded start={start_name} end={end_name}", flush=True)

        w, h = fit_i2v_dimensions(W, H, 960, 960)
        seed = secrets.randbelow(2**31 - 1)
        prompt = (
            "they are having doggy style sex, one slow hip thrust forward then settle, "
            "strap stays inside, hips only, no multi pump"
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
            filename_prefix="studio_agent_wan22_flf",
            high_loras=[("wan2.2-i2v-high-doggy-style-sex-14b.safetensors", 0.55)],
            low_loras=[("wan2.2-i2v-low-doggy-style-sex-14b.safetensors", 0.55)],
            preset="quality",
            use_lightning=False,
        )
        print(f"submit FLF2V {w}x{h} seed={seed}", flush=True)
        prompt_id = comfy.queue_prompt(api)
        print(f"prompt_id={prompt_id}", flush=True)
        hist = comfy.wait_for_completion(prompt_id)
        dest_dir = Path(r"D:\ComfyBox Images and Videos\Video")
        saved = []
        for info in comfy.collect_outputs(hist):
            out = comfy.download_file(info, dest_dir, cfg=cfg)
            saved.append(str(out))
            print(f"saved {out}", flush=True)
        result = {"ok": bool(saved), "prompt_id": prompt_id, "saved_files": saved, "seed": seed}
        print(json.dumps(result, indent=2), flush=True)
        return 0 if saved else 1
    finally:
        release_gpu_lock(cfg, "comfyui")


if __name__ == "__main__":
    raise SystemExit(main())
