#!/usr/bin/env python3
"""Smoke DaSiWa TastySin GGUF HIGH+LOW on Frieren s1b finger start still."""
from __future__ import annotations

import json
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

import requests

COMFY = "http://192.168.50.57:8188"
# Prefer local delivery copy; fall back to already-uploaded Comfy input name.
SRC_CANDIDATES = [
    Path(r"D:\studio-agent\outputs\frieren\s1b_finger_start.png"),
    Path(r"D:\ComfyBox Images and Videos\Video\Frieren\s1b_finger_start.png"),
]
REMOTE_FALLBACK = "s1b_finger_start.png"
OUT = Path(r"D:\studio-agent\outputs\frieren\s1b_dasiwa_smoke.mp4")

HIGH = "I2V/DasiwaWAN22I2V14BTastysinV8_q8High.gguf"
LOW = "I2V/DasiwaWAN22I2V14BTastysinV8_q8Low.gguf"
VAE = "wan_2.1_vae.safetensors"
CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"

PROMPT = (
    "nsfw, detailed anatomy, "
    "eyes closed, face still, minimal expression change, "
    "left hand finger fucking her pussy, two fingers thrusting in and out of her vagina, "
    "fingers fully insert into open pussy, labia parting around fingers, "
    "detailed wet vulva, pale pink labia, soft breast bounce only, "
    "no jerky body, steady camera, natural daylight"
)
NEG = (
    "fingers fused, morphing hands, rubbing only, closed pussy, barbie doll, "
    "inflamed red pussy, bloody, eyes open, ahegao, thrashing, melting face, "
    "cum, semen, watermark, text"
)


def upload(path: Path) -> str:
    data = path.read_bytes()
    b = f"----D{uuid.uuid4().hex}"
    body = (
        f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; "
        f"filename=\"{path.name}\"\r\nContent-Type: image/png\r\n\r\n"
    ).encode() + data + b"\r\n" + (
        f"--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n"
    ).encode() + f"--{b}--\r\n".encode()
    req = urllib.request.Request(
        f"{COMFY}/upload/image",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={b}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return str(json.loads(r.read().decode()).get("name") or path.name)


def has_gguf_loader() -> bool:
    try:
        info = requests.get(f"{COMFY}/object_info/UnetLoaderGGUF", timeout=30).json()
        return "UnetLoaderGGUF" in info
    except Exception:
        return False


def resolve_remote() -> str:
    for src in SRC_CANDIDATES:
        try:
            if src.is_file():
                name = upload(src)
                print("uploaded", src, "->", name, flush=True)
                return name
        except OSError as exc:
            print("skip local", src, exc, flush=True)
    print("using remote fallback", REMOTE_FALLBACK, flush=True)
    return REMOTE_FALLBACK


def build(remote: str) -> dict:
    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": HIGH}},
        "2": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": LOW}},
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": CLIP, "type": "wan", "device": "default"},
        },
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "5": {"class_type": "LoadImage", "inputs": {"image": remote}},
        "20": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "21": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": 8.0}},
        "30": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": PROMPT}},
        "31": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": NEG}},
        "40": {
            "class_type": "WanImageToVideo",
            "inputs": {
                "positive": ["30", 0],
                "negative": ["31", 0],
                "vae": ["4", 0],
                "start_image": ["5", 0],
                "width": 720,
                "height": 720,
                "length": 49,
                "batch_size": 1,
            },
        },
        "50": {
            "class_type": "KSamplerAdvanced",
            "inputs": {
                "model": ["20", 0],
                "add_noise": "enable",
                "noise_seed": uuid.uuid4().int % (2**32),
                "steps": 12,
                "cfg": 3.0,
                "sampler_name": "uni_pc",
                "scheduler": "simple",
                "positive": ["40", 0],
                "negative": ["40", 1],
                "latent_image": ["40", 2],
                "start_at_step": 0,
                "end_at_step": 6,
                "return_with_leftover_noise": "enable",
            },
        },
        "51": {
            "class_type": "KSamplerAdvanced",
            "inputs": {
                "model": ["21", 0],
                "add_noise": "disable",
                "noise_seed": 0,
                "steps": 12,
                "cfg": 1.5,
                "sampler_name": "uni_pc",
                "scheduler": "simple",
                "positive": ["40", 0],
                "negative": ["40", 1],
                "latent_image": ["50", 0],
                "start_at_step": 6,
                "end_at_step": 10000,
                "return_with_leftover_noise": "disable",
            },
        },
        "60": {"class_type": "VAEDecode", "inputs": {"samples": ["51", 0], "vae": ["4", 0]}},
        "70": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["60", 0],
                "frame_rate": 16,
                "loop_count": 0,
                "filename_prefix": "dasiwa_s1b",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not has_gguf_loader():
        print("UnetLoaderGGUF missing — install ComfyUI-GGUF + gguf in ~/ComfyUI and restart")
        return 2
    print("UnetLoaderGGUF available: True", flush=True)
    remote = resolve_remote()
    wf = build(remote)
    r = requests.post(
        f"{COMFY}/prompt",
        json={"prompt": wf, "client_id": str(uuid.uuid4())},
        timeout=60,
    )
    if r.status_code >= 400:
        print("Comfy reject", r.status_code, r.text[:1500], flush=True)
        return 2
    pid = r.json().get("prompt_id")
    print("prompt_id", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 1200:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=20).json()
        if pid not in h:
            time.sleep(5)
            continue
        st = h[pid].get("status") or {}
        if st.get("status_str") == "error":
            print("ERROR", st.get("messages"), flush=True)
            return 2
        for node in (h[pid].get("outputs") or {}).values():
            for im in node.get("gifs") or node.get("images") or []:
                fn = im.get("filename")
                if not fn:
                    continue
                qs = urllib.parse.urlencode(
                    {
                        "filename": fn,
                        "subfolder": im.get("subfolder") or "",
                        "type": im.get("type") or "output",
                    }
                )
                with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=180) as resp:
                    OUT.write_bytes(resp.read())
                print("->", OUT, OUT.stat().st_size // 1024, "KB", flush=True)
                return 0
        time.sleep(5)
    print("timeout", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
