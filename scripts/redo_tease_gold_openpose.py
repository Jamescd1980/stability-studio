#!/usr/bin/env python3
"""Redo 01_tease stills â†’ OpenPose + Frieren LoRA + studio_agent_00009 gold bar.

Writes clean PNGs into scene_packs/01_tease_gold (no JSON beside them).
"""
from __future__ import annotations

import json
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

import requests

COMFY = "http://192.168.50.57:8188"
TEASE = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\_refined\scene_packs\01_tease"
)
OUT = TEASE.parent / "01_tease_gold_v2"
ORLA = "http://127.0.0.1:11436"

CKPT = "waijfu_alpha.safetensors"
CN = "OpenPoseXL2.safetensors"
CN_STRENGTH = 0.95
WIDTH, HEIGHT = 832, 1472
STEPS, CFG = 36, 6.5
POSE_RES = 768

FRIEREN_LORA = "Frieren/Frieren.safetensors"
FRIEREN_WEIGHT = 0.90
GOLD_LORAS = [
    ("Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", 0.75),
    ("LensFlare_LightLeak_IL.safetensors", 0.40),  # milder — bedroom scenes
    ("ILDetailerV2.safetensors", 0.65),
]

IDENTITY = (
    "nb_frieren, Frieren, 1girl, solo, elf, pointy ears, "
    "long white hair, twintails, green eyes, pale skin, small breasts, "
    "serene expression, looking at viewer"
)
NEG = (
    "lowres, bad anatomy, bad hands, worst quality, watermark, signature, text, "
    "blonde hair, yellow eyes, brown hair, black hair, photorealistic, 3d render, "
    "plastic skin, muddy shading, extra fingers, deformed hands, "
    "cum, semen, excessive bodily fluids"
)


def upload(path: Path) -> str:
    boundary = f"----Tease{uuid.uuid4().hex[:8]}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode()
        + path.read_bytes()
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
    with urllib.request.urlopen(req, timeout=120) as r:
        up = json.loads(r.read().decode())
    return str(up.get("name") or path.name)


def vlm_scene_tags(path: Path) -> str:
    try:
        payload = {
            "action": "describe_image",
            "path": str(path),
            "mode": "tags",
            "prompt": (
                "Danbooru tags only for pose, hands, camera, setting, lighting, "
                "nudity/clothing. Do NOT invent hair color, eye color, or character "
                "name. No commentary."
            ),
        }
        req = urllib.request.Request(
            f"{ORLA}/action",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
        if data.get("ok"):
            tags = str(data.get("description") or "")
            # Strip identity conflicts the VLM may still emit
            for bad in (
                "blonde hair",
                "yellow eyes",
                "brown hair",
                "black hair",
                "park heejin",
                "nb_park",
            ):
                tags = tags.replace(bad, "")
            return tags.strip(" ,")
    except Exception as exc:
        print("  vlm skip:", exc)
    return (
        "sitting on bed, spread legs, bedroom, window light, nude, "
        "hand on breast, hand between legs"
    )


def build_wf(remote: str, prompt: str) -> dict:
    wf: dict = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CKPT},
        },
        "10": {"class_type": "LoadImage", "inputs": {"image": remote}},
        "12": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["10", 0],
                "upscale_method": "lanczos",
                "width": WIDTH,
                "height": HEIGHT,
                "crop": "disabled",
            },
        },
        "31": {
            "class_type": "OpenposePreprocessor",
            "inputs": {
                "image": ["12", 0],
                "detect_hand": "enable",
                "detect_body": "enable",
                "detect_face": "enable",
                "resolution": POSE_RES,
            },
        },
        "30": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": CN},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEG, "clip": ["4", 1]},
        },
        "32": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "control_net": ["30", 0],
                "image": ["31", 0],
                "strength": CN_STRENGTH,
                "start_percent": 0.0,
                "end_percent": 1.0,
            },
        },
        # Seed from source pixels so composition/hands survive the gold pass
        "11": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["12", 0], "vae": ["4", 2]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": uuid.uuid4().int % (2**32),
                "steps": STEPS,
                "cfg": CFG,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                # OpenPose + img2img = pose + scene layout stick
                "denoise": 0.58,
                "model": ["4", 0],
                "positive": ["32", 0],
                "negative": ["32", 1],
                "latent_image": ["11", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "tease_gold",
                "images": ["8", 0],
            },
        },
    }
    # LoRA chain: Frieren first, then gold finish
    model_ref: list = ["4", 0]
    clip_ref: list = ["4", 1]
    nid = 20
    stack = [(FRIEREN_LORA, FRIEREN_WEIGHT)] + GOLD_LORAS
    for name, weight in stack:
        sid = str(nid)
        wf[sid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": name,
                "strength_model": weight,
                "strength_clip": weight,
                "model": model_ref,
                "clip": clip_ref,
            },
        }
        model_ref = [sid, 0]
        clip_ref = [sid, 1]
        nid += 1
    wf["3"]["inputs"]["model"] = model_ref
    wf["6"]["inputs"]["clip"] = clip_ref
    wf["7"]["inputs"]["clip"] = clip_ref
    return wf


def queue_and_wait(wf: dict, timeout_s: float = 360) -> str | None:
    r = requests.post(
        f"{COMFY}/prompt",
        json={"prompt": wf, "client_id": str(uuid.uuid4())},
        timeout=30,
    )
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=15).json()
        if pid not in h:
            time.sleep(1.5)
            continue
        outs = h[pid].get("outputs") or {}
        for node in outs.values():
            for im in node.get("images") or []:
                if im.get("filename"):
                    return str(im["filename"])
        status = (h[pid].get("status") or {}).get("status_str")
        if status == "error":
            print("  comfy error", (h[pid].get("status") or {}).get("messages"))
            return None
        time.sleep(1.5)
    return None


def download(filename: str, dest: Path) -> None:
    qs = urllib.parse.urlencode(
        {"filename": filename, "subfolder": "", "type": "output"}
    )
    url = f"{COMFY}/view?{qs}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = sorted(
        p
        for p in TEASE.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".webp"} and p.is_file()
    )
    if not sources:
        print("No sources in", TEASE)
        return 1
    print(f"Redo {len(sources)} stills â†’ {OUT}")
    results = []
    for src in sources:
        print(f"\n=== {src.name} ===")
        remote = upload(src)
        scene = vlm_scene_tags(src)
        prompt = (
            f"{IDENTITY}, highly detailed, sharp focus, absurdres, highres, "
            f"perfect eyes, eye_focus, detailed skin, micro hair detail, {scene}"
        )
        print("  prompt:", prompt[:160], "...")
        wf = build_wf(remote, prompt)
        out_name = queue_and_wait(wf)
        if not out_name:
            print("  FAILED")
            results.append((src.name, None))
            continue
        dest = OUT / f"{src.stem}_gold_v2.png"
        download(out_name, dest)
        # Keep a tiny run log away from the PNGs
        log_path = OUT / "_batch_log.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "src": src.name,
                        "comfy": out_name,
                        "dest": dest.name,
                        "prompt": prompt,
                    }
                )
                + "\n"
            )
        print("  â†’", dest.name, f"({dest.stat().st_size // 1024} KB)")
        results.append((src.name, dest.name))

    ok = sum(1 for _, d in results if d)
    print(f"\nDone: {ok}/{len(results)} â†’ {OUT}")
    for s, d in results:
        print(f"  {s} â†’ {d or 'FAIL'}")
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())

