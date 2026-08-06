#!/usr/bin/env python3
"""DaSiWa TastySin smoke on an Invoke AI still (better anatomy start)."""
from __future__ import annotations

import json
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

import requests

COMFY = "http://192.168.50.57:8188"
SRC = Path(r"D:\studio-agent\outputs\frieren\dasiwa_invoke_start.png")
OUT = Path(r"D:\studio-agent\outputs\frieren\dasiwa_invoke_smoke.mp4")

HIGH = "I2V/DasiwaWAN22I2V14BTastysinV8_q8High.gguf"
LOW = "I2V/DasiwaWAN22I2V14BTastysinV8_q8Low.gguf"
VAE = "wan_2.1_vae.safetensors"
CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"

# Start still: eyes open, cross-legged, hand covering crotch — uncover + insert.
PROMPT = (
    "nsfw, detailed anatomy, "
    "elf girl sitting cross-legged on bed, warm lamp light, "
    "she moves her hand aside and starts finger fucking her pussy, "
    "two distinct fingers thrusting in and out of her vagina, "
    "fingers fully insert into open pussy, labia parting around fingers, "
    "vaginal opening stretches as fingers go in, clear penetration not rubbing, "
    "detailed wet vulva, soft pink labia, soft breast bounce, "
    "gentle smile, looking at viewer, steady camera, no jerky body"
)
NEG = (
    "fingers fused, morphing hands, rubbing only, closed pussy, barbie doll, "
    "inflamed red pussy, bloody, ahegao, thrashing, melting face, "
    "extra fingers, deformed hands, cum, semen, watermark, text"
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
                "filename_prefix": "dasiwa_invoke",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }


def main() -> int:
    if not SRC.is_file():
        print("missing", SRC, flush=True)
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    info = requests.get(f"{COMFY}/object_info/UnetLoaderGGUF", timeout=30).json()
    if "UnetLoaderGGUF" not in info:
        print("UnetLoaderGGUF missing", flush=True)
        return 2
    remote = upload(SRC)
    print("uploaded", remote, flush=True)
    r = requests.post(
        f"{COMFY}/prompt",
        json={"prompt": build(remote), "client_id": str(uuid.uuid4())},
        timeout=60,
    )
    if r.status_code >= 400:
        print("Comfy reject", r.status_code, r.text[:1500], flush=True)
        return 2
    pid = r.json().get("prompt_id")
    print("prompt_id", pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < 1200:
        q = requests.get(f"{COMFY}/queue", timeout=20).json()
        run = any(x[1] == pid for x in (q.get("queue_running") or []))
        pend = any(x[1] == pid for x in (q.get("queue_pending") or []))
        h = requests.get(f"{COMFY}/history/{pid}", timeout=20).json()
        if pid in h:
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
                    try:
                        with urllib.request.urlopen(
                            f"{COMFY}/view?{qs}", timeout=180
                        ) as resp:
                            data = resp.read()
                        if len(data) > 1000:
                            OUT.write_bytes(data)
                            print("->", OUT, OUT.stat().st_size // 1024, "KB", flush=True)
                            return 0
                    except Exception as exc:
                        print("view fail", fn, exc, flush=True)
            # VHS often writes under Video/ while /view 404s — scp fallback
            import subprocess

            remote = (
                "/mnt/game/ComfyBox Images and Videos/Video/dasiwa_invoke_00001.mp4"
            )
            r = subprocess.run(
                [
                    "scp",
                    "-o",
                    "ConnectTimeout=30",
                    f"comfybox:{remote}",
                    str(OUT),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode == 0 and OUT.is_file() and OUT.stat().st_size > 1000:
                print("->", OUT, OUT.stat().st_size // 1024, "KB (scp)", flush=True)
                return 0
            print("scp fail", r.stderr[:500], flush=True)
            return 3
        print(f"waiting run={run} pend={pend} elapsed={int(time.time()-t0)}s", flush=True)
        time.sleep(10)
    print("timeout", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
