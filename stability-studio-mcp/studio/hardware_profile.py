"""GPU-aware generation limits for Stability Studio MCP."""

from __future__ import annotations

from typing import Any

from studio.comfy_client import ComfyUIClient

ANATOMY_NEGATIVE_HINT = (
    "deformed face, bad anatomy, bad hands, extra fingers, missing fingers, "
    "mutated hands, distorted limbs, blurry, low quality"
)

ANATOMY_POSITIVE_HINT = (
    "natural hands, anatomically correct, detailed face, symmetrical eyes"
)


def _hardware_config(cfg: dict[str, Any]) -> dict[str, Any]:
    return dict(cfg.get("hardware") or {})


def fetch_gpu_stats(comfy: ComfyUIClient | None) -> dict[str, Any] | None:
    """Read GPU info from ComfyUI /system_stats. Returns None if ComfyUI is down."""
    if comfy is None:
        return None
    stats = comfy.get_system_stats()
    if not stats:
        return None

    devices = stats.get("devices") or []
    if not devices:
        return None

    primary = devices[0]
    vram_total = primary.get("vram_total") or 0
    vram_free = primary.get("vram_free") or 0
    return {
        "gpu": primary.get("name", "unknown"),
        "vram_total_bytes": int(vram_total),
        "vram_free_bytes": int(vram_free),
        "vram_gb": round(vram_total / (1024**3), 1),
        "vram_free_gb": round(vram_free / (1024**3), 1),
        "device_type": primary.get("type", "cuda"),
    }


def resolve_vram_gb(cfg: dict[str, Any], gpu_stats: dict[str, Any] | None) -> float:
    """Prefer config override, then live ComfyUI stats, else a safe default."""
    hw = _hardware_config(cfg)
    override = hw.get("vram_gb")
    if override and float(override) > 0:
        return float(override)
    if gpu_stats and gpu_stats.get("vram_gb"):
        return float(gpu_stats["vram_gb"])
    return 8.0


def build_generation_limits(vram_gb: float, cfg: dict[str, Any]) -> dict[str, Any]:
    """Return recommended caps for images and video on this GPU."""
    hw = _hardware_config(cfg)
    gpu_only = bool(hw.get("gpu_only", True))
    prefer_prompt_quality = bool(hw.get("prefer_prompt_quality", True))

    if vram_gb <= 8:
        image = {"max_width": 768, "max_height": 1024, "max_steps": 28}
        video_t2v = {
            "workflow_id": "t2v",
            "model_hint": "wan2.1_t2v_1.3B",
            "max_frames": 49,
            "frame_rate": 16,
        }
        video_i2v = {
            "workflow_id": "i2v_5b",
            "model_hint": "wan2.2_ti2v_5B_fp16 + wan2.2_vae",
            "max_width": 416,
            "max_height": 576,
            "max_frames": 49,
            "frame_rate": 16,
        }
        tier = "8gb"
    elif vram_gb <= 12:
        image = {"max_width": 896, "max_height": 1152, "max_steps": 30}
        video_t2v = {
            "workflow_id": "t2v",
            "model_hint": "wan2.1_t2v_1.3B",
            "max_frames": 65,
            "frame_rate": 16,
        }
        video_i2v = {
            "workflow_id": "i2v_5b",
            "model_hint": "wan2.2_ti2v_5B_fp16 + wan2.2_vae",
            "max_width": 480,
            "max_height": 640,
            "max_frames": 49,
            "frame_rate": 16,
        }
        tier = "12gb"
    elif vram_gb <= 16:
        image = {"max_width": 1024, "max_height": 1216, "max_steps": 35}
        video_t2v = {
            "workflow_id": "t2v",
            "model_hint": "wan2.1_t2v_1.3B",
            "max_frames": 81,
            "frame_rate": 16,
        }
        video_i2v = {
            "workflow_id": "i2v_5b",
            "model_hint": "wan2.2_ti2v_5B_fp16 + wan2.2_vae",
            "max_width": 704,
            "max_height": 1056,
            "max_frames": 65,
            "frame_rate": 16,
        }
        tier = "16gb"
    elif vram_gb <= 24:
        image = {"max_width": 1024, "max_height": 1536, "max_steps": 40}
        video_t2v = {
            "workflow_id": "t2v",
            "model_hint": "wan2.1_t2v_1.3B",
            "max_frames": 81,
            "frame_rate": 24,
        }
        video_i2v = {
            "workflow_id": "i2v_5b",
            "model_hint": "wan2.2_ti2v_5B_fp16 + wan2.2_vae",
            "max_width": 832,
            "max_height": 480,
            "max_frames": 81,
            "frame_rate": 16,
        }
        tier = "24gb"
    else:
        image = {"max_width": 1216, "max_height": 1664, "max_steps": 45}
        video_t2v = {
            "workflow_id": "t2v",
            "model_hint": "wan2.1_t2v_1.3B",
            "max_frames": 81,
            "frame_rate": 24,
        }
        video_i2v = {
            "max_width": 832,
            "max_height": 1216,
            "max_frames": 81,
            "frame_rate": 16,
            "quantization": "bf16",
            "load_device": "main_device",
            "force_offload": False,
        }
        tier = "32gb+"

    notes = [
        "Do not exceed these caps unless the user explicitly asks.",
        "Prefer prompt quality (face, hands, anatomy) over higher resolution.",
    ]
    if gpu_only:
        notes.append(
            "gpu_only=true: keep diffusion on GPU (fp8); T5 may use offload_device on ≤16GB I2V."
        )
    if prefer_prompt_quality:
        notes.append(
            f"Include anatomy cues in prompts, e.g. {ANATOMY_POSITIVE_HINT!r}; "
            f"negatives like {ANATOMY_NEGATIVE_HINT!r}."
        )

    return {
        "tier": tier,
        "vram_gb_used": vram_gb,
        "gpu_only": gpu_only,
        "prefer_prompt_quality": prefer_prompt_quality,
        "image": image,
        "video_t2v": video_t2v,
        "video_i2v": video_i2v,
        "notes": notes,
    }


def build_hardware_profile(cfg: dict[str, Any], comfy: ComfyUIClient | None) -> dict[str, Any]:
    """Combine live GPU stats, config overrides, and generation limits."""
    hw = _hardware_config(cfg)
    gpu_stats = fetch_gpu_stats(comfy)
    vram_gb = resolve_vram_gb(cfg, gpu_stats)
    limits = build_generation_limits(vram_gb, cfg)

    profile: dict[str, Any] = {
        "vram_gb": vram_gb,
        "vram_gb_source": "config" if hw.get("vram_gb") else ("comfyui" if gpu_stats else "default"),
        "gpu_only": bool(hw.get("gpu_only", True)),
        "prefer_prompt_quality": bool(hw.get("prefer_prompt_quality", True)),
    }
    if gpu_stats:
        profile.update(
            {
                "gpu": gpu_stats["gpu"],
                "vram_free_gb": gpu_stats["vram_free_gb"],
                "device_type": gpu_stats["device_type"],
            }
        )
    else:
        profile["gpu"] = None
        profile["note"] = "ComfyUI offline — limits use config override or conservative defaults."

    return {
        "hardware_profile": profile,
        "generation_limits": limits,
    }


def _round_dim(value: int, multiple: int = 8, minimum: int = 16) -> int:
    if value <= 0:
        return minimum
    rounded = max(multiple, (value // multiple) * multiple)
    return max(minimum, rounded)


# Common portrait sizes agents mention (width → height).
_PORTRAIT_HEIGHT_BY_WIDTH: dict[int, int] = {
    512: 768,
    768: 1152,
    832: 1216,
    896: 1152,
    1024: 1536,
}


def sanitize_image_dims(
    width: int | None,
    height: int | None,
    defaults: dict[str, Any],
    limits: dict[str, Any],
) -> tuple[int, int, dict[str, Any]]:
    """
    Normalize agent-supplied width/height before clamping.

    Fixes missing/zero dims and absurd values (e.g. 8320000000000000 from "8k" glued to 832).
    """
    caps = limits.get("image", {})
    max_w = int(caps.get("max_width", 2048))
    max_h = int(caps.get("max_height", 2048))
    def_w = int(defaults.get("width", 1024))
    def_h = int(defaults.get("height", 1024))
    hard_max = max(max_w, max_h, 2048)

    applied: dict[str, Any] = {}

    def _coerce_dim(raw: int | None, default: int, label: str) -> int:
        if raw is None or raw <= 0:
            if raw == 0:
                applied[label] = {"received": 0, "used": default, "reason": "zero_means_default"}
            return default
        if raw > hard_max:
            # Agent bug: "832" + "8k resolution" → 8320000000000000
            s = str(raw)
            for candidate in sorted(_PORTRAIT_HEIGHT_BY_WIDTH.keys(), reverse=True):
                if s.startswith(str(candidate)):
                    applied[label] = {
                        "received": raw,
                        "used": candidate,
                        "reason": "recovered_width_prefix",
                    }
                    return candidate
            applied[label] = {"received": raw, "used": default, "reason": "out_of_range"}
            return default
        return raw

    w = _coerce_dim(width, def_w, "width")
    h = _coerce_dim(height, def_h, "height")

    if height is None or height <= 0:
        preset_h = _PORTRAIT_HEIGHT_BY_WIDTH.get(w)
        if preset_h:
            h = preset_h
            applied["height"] = {"inferred": h, "reason": "portrait_preset", "width": w}
        elif width and width > 0:
            h = _round_dim(int(w * 1.5))
            applied["height"] = {"inferred": h, "reason": "aspect_ratio_2_3", "width": w}

    w = _round_dim(w)
    h = _round_dim(h)
    return w, h, applied


def clamp_image_params(
    width: int,
    height: int,
    steps: int,
    limits: dict[str, Any],
) -> tuple[int, int, int, dict[str, Any]]:
    """Clamp image size/steps to generation_limits.image."""
    caps = limits.get("image", {})
    max_w = int(caps.get("max_width", width))
    max_h = int(caps.get("max_height", height))
    max_steps = int(caps.get("max_steps", steps))

    orig = {"width": width, "height": height, "steps": steps}
    w, h = width, height
    if w > max_w or h > max_h:
        scale = min(max_w / w, max_h / h, 1.0)
        w = _round_dim(int(w * scale))
        h = _round_dim(int(h * scale))
    st = min(steps, max_steps)

    w = _round_dim(w)
    h = _round_dim(h)

    applied = {}
    if (w, h, st) != (width, height, steps):
        applied = {"original": orig, "clamped": {"width": w, "height": h, "steps": st}}

    return w, h, st, applied


def fit_i2v_dimensions(
    src_width: int,
    src_height: int,
    max_width: int,
    max_height: int,
) -> tuple[int, int]:
    """Fit source image into VRAM caps, preserve aspect ratio, round to multiples of 16."""
    if src_width <= 0 or src_height <= 0:
        w = max(16, (max_width // 16) * 16)
        h = max(16, (max_height // 16) * 16)
        return w, h
    scale = min(max_width / src_width, max_height / src_height, 1.0)
    width = max(16, int(round((src_width * scale) / 16)) * 16)
    height = max(16, int(round((src_height * scale) / 16)) * 16)
    return width, height


def clamp_video_params(
    *,
    mode: str,
    num_frames: int | None,
    frame_rate: float | None,
    limits: dict[str, Any],
) -> tuple[int, float, dict[str, Any]]:
    """Apply defaults then clamp video frame count and fps to generation_limits."""
    key = "video_i2v" if mode in {"i2v", "v2v"} else "video_t2v"
    caps = limits.get(key, {})
    applied: dict[str, Any] = {}

    nf = num_frames if num_frames is not None else int(caps.get("max_frames", 65))
    fr = frame_rate if frame_rate is not None else float(caps.get("frame_rate", 16))

    if caps.get("max_frames"):
        max_f = int(caps["max_frames"])
        if nf > max_f:
            applied["num_frames"] = {"original": nf, "clamped": max_f}
            nf = max_f
    if caps.get("frame_rate"):
        max_fr = float(caps["frame_rate"])
        if fr > max_fr:
            applied["frame_rate"] = {"original": fr, "clamped": max_fr}
            fr = max_fr

    return nf, fr, applied


def apply_video_safety_caps(
    *,
    vram_gb: float,
    vram_free_gb: float | None,
    smooth_motion: bool,
    lora_bundle: str,
    lora_ids: list[str] | None,
    use_painter_i2v: bool,
    workflow_id: str | None,
    num_frames: int,
    frame_rate: float,
    motion_amplitude: float,
) -> tuple[bool, str, list[str] | None, float, int, float, dict[str, Any]]:
    """
    Downgrade risky video params on ≤16 GB GPUs.
    Returns (smooth_motion, lora_bundle, lora_ids, motion_amplitude, num_frames, frame_rate, applied).
    """
    applied: dict[str, Any] = {}
    low_vram = vram_gb <= 16
    painter = use_painter_i2v or (workflow_id or "") in {"i2v_5b_painter", "v2v_5b_painter"}
    has_loras = bool(lora_bundle) or bool(lora_ids)

    if low_vram and smooth_motion:
        smooth_motion = False
        applied["smooth_motion"] = {
            "original": True,
            "clamped": False,
            "reason": "16GB: smooth_motion often freezes clips; use motion_amplitude 1.1–1.2 instead",
        }

    if low_vram and has_loras and painter:
        if lora_bundle:
            applied["lora_bundle"] = {"original": lora_bundle, "clamped": ""}
            lora_bundle = ""
        if lora_ids:
            applied["lora_ids"] = {"original": lora_ids, "clamped": None}
            lora_ids = None

    if low_vram and motion_amplitude > 1.25:
        applied["motion_amplitude"] = {"original": motion_amplitude, "clamped": 1.25}
        motion_amplitude = 1.25

    if vram_free_gb is not None and vram_free_gb < 2.0 and num_frames > 33:
        applied["num_frames"] = {
            "original": num_frames,
            "clamped": 33,
            "reason": f"Low free VRAM ({vram_free_gb} GB) — another GPU job may be active",
        }
        num_frames = 33

    if low_vram and num_frames > 65:
        applied["num_frames"] = {"original": num_frames, "clamped": 65}
        num_frames = 65

    return smooth_motion, lora_bundle, lora_ids, motion_amplitude, num_frames, frame_rate, applied
