"""Wan 2.2 I2V-A14B MoE (HIGH + LOW) API graph — proven dual KSampler path.

Validated by BJ NSFW runs (`scripts/run_bj_wan22_loras.py`): dual UNETLoader →
per-branch LoraLoaderModelOnly stacks → ModelSamplingSD3 → WanImageToVideo →
KSamplerAdvanced (high noise) → KSamplerAdvanced (low noise) → VAEDecode → VHS.

Do not use the single-UNET Wan 2.1 native graph for identity-critical / NSFW I2V.
"""

from __future__ import annotations

from typing import Any

# ComfyBox Stability Matrix paths (as exposed by UNETLoader / VAELoader / CLIPLoader).
HIGH_UNET = "I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors"
LOW_UNET = "I2V/Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors"
VAE_NAME = "wan_2.1_vae.safetensors"
CLIP_NAME = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"

# Quality (no distill): extra steps for face/identity keepers (2026-07-31).
PRESET_QUALITY: dict[str, Any] = {
    "steps": 28,
    "switch_step": 14,
    "cfg_high": 3.5,
    "cfg_low": 3.5,
    "shift": 8.0,
    "sampler_name": "uni_pc",
    "scheduler": "simple",
    "use_lightning": False,
}

# Fast distill: LightX2V / Lightning HIGH+LOW (community motion recipe).
PRESET_FAST: dict[str, Any] = {
    "steps": 8,
    "switch_step": 4,
    "cfg_high": 3.0,
    "cfg_low": 1.0,
    "shift": 5.0,
    "sampler_name": "uni_pc",
    "scheduler": "simple",
    "use_lightning": True,
    "lightning_high_strength": 0.75,
    "lightning_low_strength": 1.0,
}

# Default = quality (no distill). Lightning is draft-only via preset "fast".
# 2026-07-20: Lightning-as-default caused identity melt on chained NSFW I2V.
PRESET_DEFAULT: dict[str, Any] = {
    "steps": 28,
    "switch_step": 14,
    "cfg_high": 3.5,
    "cfg_low": 3.5,
    "shift": 8.0,
    "sampler_name": "uni_pc",
    "scheduler": "simple",
    "use_lightning": False,
}

LIGHTNING_HIGH = "wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors"
LIGHTNING_LOW = "wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors"

PRESETS = {
    "default": PRESET_DEFAULT,
    "quality": PRESET_QUALITY,
    "fast": PRESET_FAST,
}


def stack_loras(
    api: dict[str, Any],
    model_ref: list[Any],
    loras: list[tuple[str, float]],
    start_id: int,
) -> tuple[list[Any], int]:
    """Chain LoraLoaderModelOnly after a MODEL ref. Returns (final_model_ref, next_id)."""
    nid = start_id
    prev = model_ref
    for name, strength in loras:
        if not name:
            continue
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


def build_wan22_i2v_moe_api(
    *,
    image_name: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    length: int = 49,
    seed: int = 42,
    frame_rate: float = 16.0,
    filename_prefix: str = "studio_agent_wan22_moe",
    high_loras: list[tuple[str, float]] | None = None,
    low_loras: list[tuple[str, float]] | None = None,
    preset: str = "default",
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
    """Build a ComfyUI API-format prompt for Wan 2.2 I2V-A14B MoE."""
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
    api["5"] = {"class_type": "LoadImage", "inputs": {"image": image_name}}

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
    api["40"] = {
        "class_type": "WanImageToVideo",
        "inputs": {
            "positive": ["30", 0],
            "negative": ["31", 0],
            "vae": ["4", 0],
            "start_image": ["5", 0],
            "width": int(width),
            "height": int(height),
            "length": int(length),
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


def describe_moe_graph(
    *,
    high_loras: list[tuple[str, float]] | None = None,
    low_loras: list[tuple[str, float]] | None = None,
    preset: str = "default",
    use_lightning: bool | None = None,
) -> dict[str, Any]:
    """Metadata for logs / generate_video result (no Comfy call)."""
    p = dict(PRESETS.get(preset, PRESET_DEFAULT))
    want_lightning = bool(p.get("use_lightning")) if use_lightning is None else bool(use_lightning)
    return {
        "architecture": "wan22_i2v_a14b_moe",
        "high_unet": HIGH_UNET,
        "low_unet": LOW_UNET,
        "vae": VAE_NAME,
        "clip": CLIP_NAME,
        "preset": preset,
        "use_lightning": want_lightning,
        "lightning_high": LIGHTNING_HIGH if want_lightning else None,
        "lightning_low": LIGHTNING_LOW if want_lightning else None,
        "high_loras": list(high_loras or []),
        "low_loras": list(low_loras or []),
        "sampler": {
            "steps": p["steps"],
            "switch_step": p["switch_step"],
            "cfg_high": p["cfg_high"],
            "cfg_low": p["cfg_low"],
            "shift": p["shift"],
        },
        "wiring": (
            "HIGH UNET (+ HIGH LoRAs) → KSamplerAdv 0..switch; "
            "LOW UNET (+ LOW LoRAs) → KSamplerAdv switch..end; "
            "WanImageToVideo latent bridge"
        ),
    }
