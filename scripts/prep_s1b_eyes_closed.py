#!/usr/bin/env python3
"""Mild img2img: s1a_play lastframe → eyes closed, keep face/body/crotch."""
from __future__ import annotations

import json
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

import requests

COMFY = "http://192.168.50.57:8188"
SRC = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\s1a_play_lastframe.png")
OUT = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\s1b_finger_start.png")

CKPT = "waijfu_alpha.safetensors"
FRIEREN = "Frieren/Frieren.safetensors"
PROMPT = (
    "masterpiece, best quality, same face as source, same body as source, "
    "nb_frieren, Frieren, 1girl, solo, elf, naked, sitting on bed legs spread, "
    "eyes closed, eyelids shut, peaceful expression, same mouth, "
    "left hand fingering her pussy, fingers in pussy, detailed labia, "
    "right hand on breast, keep pose, keep hands, keep pussy detail"
)
NEG = (
    "eyes open, looking at viewer, ahegao, melted face, blob mouth, "
    "barbie doll, smooth crotch, different pose, censored, bad hands"
)


def upload(path: Path) -> str:
    data = path.read_bytes()
    b = f"----E{uuid.uuid4().hex}"
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


def main() -> int:
    if not SRC.is_file():
        print("missing", SRC)
        return 2
    remote = upload(SRC)
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "10": {"class_type": "LoadImage", "inputs": {"image": remote}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}},
        "20": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": FRIEREN,
                "strength_model": 0.85,
                "strength_clip": 0.85,
                "model": ["4", 0],
                "clip": ["4", 1],
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": PROMPT, "clip": ["20", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEG, "clip": ["20", 1]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": uuid.uuid4().int % (2**32),
                "steps": 28,
                "cfg": 5.5,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 0.28,
                "model": ["20", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["11", 0],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "s1b_eyes", "images": ["8", 0]},
        },
    }
    r = requests.post(
        f"{COMFY}/prompt",
        json={"prompt": wf, "client_id": str(uuid.uuid4())},
        timeout=30,
    )
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    t0 = time.time()
    name = None
    while time.time() - t0 < 300:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=15).json()
        if pid in h:
            for node in (h[pid].get("outputs") or {}).values():
                for im in node.get("images") or []:
                    if im.get("filename"):
                        name = im["filename"]
                        break
            if name or (h[pid].get("status") or {}).get("status_str") == "error":
                break
        time.sleep(1.2)
    if not name:
        print("FAIL")
        return 2
    qs = urllib.parse.urlencode({"filename": name, "subfolder": "", "type": "output"})
    with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=120) as resp:
        OUT.write_bytes(resp.read())
    print("->", OUT, OUT.stat().st_size // 1024, "KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
