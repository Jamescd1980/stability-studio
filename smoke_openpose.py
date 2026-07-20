#!/usr/bin/env python3
"""Smoke OpenPose ControlNet cast-swap path against ComfyUI."""
from __future__ import annotations

import json
import time
import uuid
import urllib.request
from pathlib import Path

import requests

COMFY = "http://192.168.50.57:8188"
SRC = Path(r"D:\ComfyBox Images and Videos\Images\studio_agent_00009_.png")


def main() -> int:
    print("stats", requests.get(f"{COMFY}/system_stats", timeout=10).status_code)
    if not SRC.is_file():
        print("missing", SRC)
        return 1

    boundary = f"----Smoke{uuid.uuid4().hex[:8]}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{SRC.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode()
        + SRC.read_bytes()
        + b"\r\n"
        + (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
            f"true\r\n"
        ).encode()
        + f"--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        f"{COMFY}/upload/image",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        up = json.loads(r.read().decode())
    remote = up.get("name") or SRC.name
    print("uploaded", remote)

    prompt = (
        "masterpiece, best quality, amazing quality, anime illustration, "
        "nb_frieren, 1girl, solo, long white hair, green eyes, elf, pointy ears, "
        "sun hat, dappled sunlight, outdoors, looking at viewer, "
        "highly detailed, perfect eyes, eye_focus"
    )
    neg = "lowres, bad anatomy, worst quality, watermark"
    wf = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "waijfu_alpha.safetensors"},
        },
        "10": {"class_type": "LoadImage", "inputs": {"image": remote}},
        "31": {
            "class_type": "OpenposePreprocessor",
            "inputs": {
                "image": ["10", 0],
                "detect_hand": "enable",
                "detect_body": "enable",
                "detect_face": "enable",
                "resolution": 512,
            },
        },
        "30": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "OpenPoseXL2.safetensors"},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": neg, "clip": ["4", 1]},
        },
        "32": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "control_net": ["30", 0],
                "image": ["31", 0],
                "strength": 0.85,
                "start_percent": 0.0,
                "end_percent": 1.0,
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 832, "height": 1472, "batch_size": 1},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42,
                "steps": 28,
                "cfg": 6.5,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["32", 0],
                "negative": ["32", 1],
                "latent_image": ["5", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
        },
        "20": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
                "strength_model": 0.75,
                "strength_clip": 0.75,
                "model": ["4", 0],
                "clip": ["4", 1],
            },
        },
        "21": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "LensFlare_LightLeak_IL.safetensors",
                "strength_model": 0.55,
                "strength_clip": 0.55,
                "model": ["20", 0],
                "clip": ["20", 1],
            },
        },
        "22": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "ILDetailerV2.safetensors",
                "strength_model": 0.65,
                "strength_clip": 0.65,
                "model": ["21", 0],
                "clip": ["21", 1],
            },
        },
    }
    wf["3"]["inputs"]["model"] = ["22", 0]
    wf["6"]["inputs"]["clip"] = ["22", 1]
    wf["7"]["inputs"]["clip"] = ["22", 1]

    r = requests.post(
        f"{COMFY}/prompt",
        json={"prompt": wf, "client_id": str(uuid.uuid4())},
        timeout=30,
    )
    print("queue", r.status_code, r.text[:400])
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < 360:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=15).json()
        if pid in h:
            status = (h[pid].get("status") or {}).get("status_str")
            msgs = (h[pid].get("status") or {}).get("messages") or []
            outs = h[pid].get("outputs") or {}
            imgs = []
            for n in outs.values():
                for im in n.get("images") or []:
                    if im.get("filename"):
                        imgs.append(im["filename"])
            print("DONE status=", status, "imgs=", imgs, "elapsed=", round(time.time() - t0, 1))
            if not imgs:
                print("messages", msgs[-3:] if msgs else msgs)
            return 0 if imgs else 2
        time.sleep(2)
    print("TIMEOUT")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
