"""Wan 2.2 I2V-A14B MoE First-Last-Frame (FLF2V) API graph.

Same HIGH+LOW dual KSampler stack as wan22_i2v_moe, but bridges with
WanFirstLastFrameToVideo instead of WanImageToVideo.
"""

from __future__ import annotations

from typing import Any

from studio.wan22_i2v_moe import (
    CLIP_NAME,
    HIGH_UNET,
    LIGHTNING_HIGH,
    LIGHTNING_LOW,
    LOW_UNET,
    PRESET_DEFAULT,
    PRESETS,
    VAE_NAME,
    stack_loras,
)


def build_wan22_flf2v_moe_api(
    *,
    start_image_name: str,
    end_image_name: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    length: int = 21,
    seed: int = 42,
    frame_rate: float = 16.0,
    filename_prefix: str = "studio_agent_wan22_flf",
    high_loras: list[tuple[str, float]] | None = None,
    low_loras: list[tuple[str, float]] | None = None,
    preset: str = "quality",
    steps: int | None = None,
    switch_step: int | None = None,
    cfg_high: float | None = None,
    cfg_low: float | None = None,
    shift: float | None = None,
    use_lightning: bool | None = None,
    lightning_high: str = LIGHTNING_HIGH,
    lightning_low: str = LIGHTNING_LOW,
    crf: int = 14,
) -> dict[str, Any]:
    """Build ComfyUI API prompt for Wan 2.2 MoE FLF2V (no Lightning by default)."""
    p = dict(PRESETS.get(preset, PRESET_DEFAULT))
    steps_v = int(steps if steps is not None else p["steps"])
    switch_v = int(switch_step if switch_step is not None else p["switch_step"])
    switch_v = max(1, min(switch_v, steps_v - 1))
    cfg_h = float(cfg_high if cfg_high is not None else p["cfg_high"])
    cfg_l = float(cfg_low if cfg_low is not None else p["cfg_low"])
    shift_v = float(shift if shift is not None else p["shift"])
    want_lightning = bool(p.get("use_lightning")) if use_lightning is None else bool(use_lightning)

    high_stack: list[tuple[str, float]] = []
    low_stack: list[tuple[str, float]] = []
    if want_lightning:
        high_stack.append((lightning_high, float(p.get("lightning_high_strength", 0.7))))
        low_stack.append((lightning_low, float(p.get("lightning_low_strength", 1.0))))
    high_stack.extend(high_loras or [])
    low_stack.extend(low_loras or [])

    api: dict[str, Any] = {}
    api["1"] = {
        "class_type": "UNETLoader",
        "inputs": {"unet_name": HIGH_UNET, "weight_dtype": "default"},
    }
    api["2"] = {
        "class_type": "UNETLoader",
        "inputs": {"unet_name": LOW_UNET, "weight_dtype": "default"},
    }
    api["3"] = {
        "class_type": "CLIPLoader",
        "inputs": {"clip_name": CLIP_NAME, "type": "wan", "device": "default"},
    }
    api["4"] = {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}}
    api["5"] = {"class_type": "LoadImage", "inputs": {"image": start_image_name}}
    api["6"] = {"class_type": "LoadImage", "inputs": {"image": end_image_name}}

    high_model, nid = stack_loras(api, ["1", 0], high_stack, 10)
    low_model, nid = stack_loras(api, ["2", 0], low_stack, nid)

    api["20"] = {
        "class_type": "ModelSamplingSD3",
        "inputs": {"model": high_model, "shift": shift_v},
    }
    api["21"] = {
        "class_type": "ModelSamplingSD3",
        "inputs": {"model": low_model, "shift": shift_v},
    }
    api["30"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["3", 0], "text": prompt},
    }
    api["31"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["3", 0], "text": negative},
    }
    # length step 4 for WanFirstLastFrameToVideo
    length_v = max(5, int(length))
    length_v = length_v - ((length_v - 1) % 4)
    api["40"] = {
        "class_type": "WanFirstLastFrameToVideo",
        "inputs": {
            "positive": ["30", 0],
            "negative": ["31", 0],
            "vae": ["4", 0],
            "start_image": ["5", 0],
            "end_image": ["6", 0],
            "width": int(width),
            "height": int(height),
            "length": length_v,
            "batch_size": 1,
        },
    }
    sampler = str(p.get("sampler_name", "uni_pc"))
    scheduler = str(p.get("scheduler", "simple"))
    api["50"] = {
        "class_type": "KSamplerAdvanced",
        "inputs": {
            "model": ["20", 0],
            "add_noise": "enable",
            "noise_seed": int(seed),
            "steps": steps_v,
            "cfg": cfg_h,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "positive": ["40", 0],
            "negative": ["40", 1],
            "latent_image": ["40", 2],
            "start_at_step": 0,
            "end_at_step": switch_v,
            "return_with_leftover_noise": "enable",
        },
    }
    api["51"] = {
        "class_type": "KSamplerAdvanced",
        "inputs": {
            "model": ["21", 0],
            "add_noise": "disable",
            "noise_seed": int(seed),
            "steps": steps_v,
            "cfg": cfg_l,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "positive": ["40", 0],
            "negative": ["40", 1],
            "latent_image": ["50", 0],
            "start_at_step": switch_v,
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
            "frame_rate": float(frame_rate),
            "loop_count": 0,
            "filename_prefix": filename_prefix,
            "format": "video/h264-mp4",
            "pingpong": False,
            "save_output": True,
            "pix_fmt": "yuv420p",
            "crf": int(crf),
            "save_metadata": True,
            "trim_to_audio": False,
            "no_preview": False,
        },
    }
    return api
