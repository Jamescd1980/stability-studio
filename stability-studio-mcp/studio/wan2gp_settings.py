"""Build Wan2GP settings dicts for hero I2V (Enhanced Lightning v2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_MODEL = "i2v_2_2_Enhanced_Lightning_v2"


def build_hero_i2v_settings(
    *,
    prompt: str,
    image_path: str | Path,
    negative_prompt: str = "",
    video_length: int = 49,
    resolution: str = "832x480",
    seed: int = -1,
    motion_amplitude: float = 1.05,
    num_inference_steps: int = 4,
    model_type: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    img = Path(image_path).resolve()
    if not img.is_file():
        raise FileNotFoundError(f"image_start not found: {img}")
    return {
        "settings_version": 2.56,
        "model_type": model_type,
        "base_model_type": "i2v_2_2",
        "prompt": prompt.strip(),
        "negative_prompt": negative_prompt.strip(),
        "resolution": resolution,
        "video_length": int(video_length),
        "batch_size": 1,
        "seed": int(seed),
        "num_inference_steps": int(num_inference_steps),
        "guidance_scale": 1,
        "guidance2_scale": 1,
        "guidance_phases": 2,
        "switch_threshold": 900,
        "flow_shift": 5,
        "sample_solver": "unipc",
        "image_prompt_type": "S",
        "motion_amplitude": float(motion_amplitude),
        "multi_prompts_gen_type": "FG",
        "image_start": str(img),
    }


def plan_wan2gp_job(
    *,
    prompt: str,
    image_path: str,
    negative_prompt: str = "",
    video_length: int = 49,
    resolution: str = "832x480",
    model_type: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    settings = build_hero_i2v_settings(
        prompt=prompt,
        image_path=image_path,
        negative_prompt=negative_prompt,
        video_length=video_length,
        resolution=resolution,
        model_type=model_type,
    )
    return {
        "backend": "wan2gp",
        "model_type": model_type,
        "settings": settings,
        "note": "Call generate_video_hero to run. Requires check_gpu_backend allowed wan2gp.",
    }
