# -*- coding: utf-8 -*-
"""CUDA RealESRGAN / AnimeSharp upscale for Wan delivery clips (main-rig .venv-post)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from spandrel import ModelLoader
from torchvision.transforms.functional import to_pil_image, to_tensor


def _probe_fps(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    if "/" in out:
        num, den = out.split("/", 1)
        if float(den):
            return float(num) / float(den)
    return float(out or 16)


def _load_model(model_path: Path, device: torch.device):
    model = ModelLoader().load_from_file(str(model_path))
    model = model.eval().to(device)
    use_half = False
    if device.type == "cuda":
        try:
            model = model.half()
            use_half = True
        except Exception:
            # RCAN AnimeSharp etc. often fp32-only in spandrel
            model = model.float()
            use_half = False
    return model, use_half


@torch.inference_mode()
def _upscale_bgr(model, bgr: np.ndarray, device: torch.device, use_half: bool) -> np.ndarray:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    t = to_tensor(Image.fromarray(rgb)).unsqueeze(0).to(device)
    if use_half:
        t = t.half()
    out = model(t)
    if isinstance(out, (tuple, list)):
        out = out[0]
    out = out.float().clamp(0, 1).squeeze(0).cpu()
    pil = to_pil_image(out)
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


def upscale_video(
    src: Path,
    dest: Path,
    model_path: Path,
    *,
    crf: int = 17,
    max_frames: int = 0,
) -> dict:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available — run with .venv-post on the 5060 Ti rig")
    device = torch.device("cuda")
    model, use_half = _load_model(model_path, device)
    fps = _probe_fps(src)

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {src}")

    tmp = Path(tempfile.mkdtemp(prefix="wan_upscale_"))
    frames_dir = tmp / "frames"
    frames_dir.mkdir()
    n = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            up = _upscale_bgr(model, frame, device, use_half)
            cv2.imwrite(str(frames_dir / f"f_{n:06d}.png"), up)
            n += 1
            if max_frames and n >= max_frames:
                break
            if n % 25 == 0:
                print(f"upscaled {n} frames...", flush=True)
        cap.release()
        if n == 0:
            raise RuntimeError("No frames decoded")

        dest.parent.mkdir(parents=True, exist_ok=True)
        pattern = str(frames_dir / "f_%06d.png")
        cmd = [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {
        "ok": True,
        "source": str(src),
        "dest": str(dest),
        "frames": n,
        "fps": fps,
        "model": model_path.name,
        "device": torch.cuda.get_device_name(0),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()
    result = upscale_video(
        Path(args.input),
        Path(args.output),
        Path(args.model),
        crf=args.crf,
        max_frames=args.max_frames,
    )
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
