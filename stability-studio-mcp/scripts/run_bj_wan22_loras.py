# -*- coding: utf-8 -*-
"""Wan 2.2 I2V-A14B HIGH/LOW + oral/deepthroat/helper LoRAs — shaft-persistence BJ clips."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.engine import GenerationEngine
from studio.catalog import StyleCatalog
from studio.config import catalog_path

HIGH_UNET = "I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors"
LOW_UNET = "I2V/Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors"
VAE = "wan_2.1_vae.safetensors"
CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"

HIGH_LORAS = [
    ("wan2.2-i2v-high-oral-insertion-v1.0.safetensors", 0.75),
    ("wan22-ultimatedeepthroat-i2v-102epoc-high-k3nk.safetensors", 0.45),
    ("wan22-k3nk4llinon3-16epoc-full-high-k3nk.safetensors", 0.50),
]
LOW_LORAS = [
    ("wan2.2-i2v-low-oral-insertion-v1.0.safetensors", 0.75),
    ("wan22-ultimatedeepthroat-I2V-101epoc-low-k3nk.safetensors", 0.45),
    ("wan22-k3nk4llinon3-15epoc-full-low-k3nk.safetensors", 0.50),
]

NEG = (
    "pulling away, pulling back, withdrawing, backing off, chewing, biting, "
    "deflating penis, shrinking penis, disappearing shaft, vanishing tip, "
    "melting genitals, empty mouth, tip missing, hose, metal object, "
    "photoreal, identity change, morphing face, flicker, warped anatomy"
)

JOBS = [
    {
        "name": "close_up",
        "image": r"D:\ComfyBox Images and Videos\User Import\close_up_bj.png",
        "prompt": (
            "she is giving him a blowjob, head moves down the shaft taking him deeper, "
            "strong oral insertion, rhythmic bobbing downward then up only a little, "
            "lips stay sealed around thick erect penis with constant girth, "
            "anime style, hold purple hair and face"
        ),
        # Source is 1024x1024 — portrait 480x832 center-crops the man/depth on the right.
        "width": 720,
        "height": 720,
    },
    {
        "name": "wide_angle",
        "image": r"D:\ComfyBox Images and Videos\User Import\wide_angle_bj.png",
        "prompt": (
            "she is giving him a blowjob, head goes down the shaft taking him deeper, "
            "oral insertion, rhythmic bobbing downward not away, "
            "lips stay sealed around thick erect penis with constant girth, "
            "anime style, hold purple ponytail bodies and room"
        ),
        # Source is also 1024x1024 — landscape crops top/bottom; keep square.
        "width": 720,
        "height": 720,
    },
]


def _stack_loras(api: dict, model_ref: list, loras: list[tuple[str, float]], start_id: int) -> tuple[list, int]:
    nid = start_id
    prev = model_ref
    for name, strength in loras:
        api[str(nid)] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": prev,
                "lora_name": name,
                "strength_model": float(strength),
            },
        }
        prev = [str(nid), 0]
        nid += 1
    return prev, nid


def build_api(
    *,
    image_name: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    length: int = 49,
    steps: int = 20,
    switch_step: int = 10,
    cfg: float = 3.5,
    seed: int = 42,
) -> dict:
    api: dict = {}
    # loaders
    api["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": HIGH_UNET, "weight_dtype": "default"}}
    api["2"] = {"class_type": "UNETLoader", "inputs": {"unet_name": LOW_UNET, "weight_dtype": "default"}}
    api["3"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "wan", "device": "default"}}
    api["4"] = {"class_type": "VAELoader", "inputs": {"vae_name": VAE}}
    api["5"] = {"class_type": "LoadImage", "inputs": {"image": image_name}}

    high_model, nid = _stack_loras(api, ["1", 0], HIGH_LORAS, 10)
    low_model, nid = _stack_loras(api, ["2", 0], LOW_LORAS, nid)

    api["20"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": high_model, "shift": 8.0}}
    api["21"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": low_model, "shift": 8.0}}

    api["30"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["3", 0], "text": prompt},
    }
    api["31"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["3", 0], "text": negative},
    }
    api["40"] = {
        "class_type": "WanImageToVideo",
        "inputs": {
            "positive": ["30", 0],
            "negative": ["31", 0],
            "vae": ["4", 0],
            "start_image": ["5", 0],
            "width": width,
            "height": height,
            "length": length,
            "batch_size": 1,
        },
    }

    # High-noise phase
    api["50"] = {
        "class_type": "KSamplerAdvanced",
        "inputs": {
            "model": ["20", 0],
            "add_noise": "enable",
            "noise_seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "uni_pc",
            "scheduler": "simple",
            "positive": ["40", 0],
            "negative": ["40", 1],
            "latent_image": ["40", 2],
            "start_at_step": 0,
            "end_at_step": switch_step,
            "return_with_leftover_noise": "enable",
        },
    }
    # Low-noise phase
    api["51"] = {
        "class_type": "KSamplerAdvanced",
        "inputs": {
            "model": ["21", 0],
            "add_noise": "disable",
            "noise_seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "uni_pc",
            "scheduler": "simple",
            "positive": ["40", 0],
            "negative": ["40", 1],
            "latent_image": ["50", 0],
            "start_at_step": switch_step,
            "end_at_step": 10000,
            "return_with_leftover_noise": "disable",
        },
    }
    api["60"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["51", 0], "vae": ["4", 0]},
    }
    api["70"] = {
        "class_type": "VHS_VideoCombine",
        "inputs": {
            "images": ["60", 0],
            "frame_rate": 16,
            "loop_count": 0,
            "filename_prefix": "studio_agent_wan22",
            "format": "video/h264-mp4",
            "pingpong": False,
            "save_output": True,
            "pix_fmt": "yuv420p",
            "crf": 17,
            "save_metadata": True,
            "trim_to_audio": False,
            "no_preview": False,
        },
    }
    return api


def main() -> None:
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)

    results = []
    for job in JOBS:
        print("=" * 60, flush=True)
        print(f"START {job['name']} wan22+loras", flush=True)
        src = Path(job["image"])
        uploaded = eng.comfy.upload_image(src)
        api = build_api(
            image_name=uploaded,
            prompt=job["prompt"],
            negative=NEG,
            width=job["width"],
            height=job["height"],
        )
        try:
            prompt_id = eng.comfy.queue_prompt(api)
            history = eng.comfy.wait_for_completion(prompt_id)
            outputs = eng.comfy.collect_outputs(history)
            saved = eng._save_comfy_outputs(outputs, extensions=(".mp4", ".webm", ".gif", ".png"))
            result = {
                "ok": True,
                "name": job["name"],
                "prompt_id": prompt_id,
                "saved_files": saved,
                "uploaded_image": uploaded,
                "workflow": "wan22_a14b_dual_loras",
            }
            print(f"OK {job['name']} saved={saved}", flush=True)
        except Exception as exc:
            result = {"ok": False, "name": job["name"], "error": str(exc)}
            print(f"FAIL {job['name']}: {exc}", flush=True)
        results.append(result)
        (ROOT / "outputs" / f"bj_wan22_{job['name']}.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )

    summary = ROOT / "outputs" / "bj_wan22_loras_summary.json"
    summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("SUMMARY", summary, flush=True)
    sys.exit(0 if all(r.get("ok") and r.get("saved_files") for r in results) else 1)


if __name__ == "__main__":
    main()
