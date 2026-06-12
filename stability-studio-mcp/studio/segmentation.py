"""Text-prompt segmentation via GroundingDINO + SAM (comfyui_controlnet_aux)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from studio.comfy_deps import check_node_types, install_node_packages

SEGMENTATION_NODES = frozenset(
    {
        "GroundingDinoModelLoader",
        "SAMLoader",
        "GroundingDinoSAMSegment",
    }
)

# Fallback when segmentation nodes unavailable
REGION_KEYWORDS: dict[str, str] = {
    "right wall": "right_building",
    "right church": "right_building",
    "church wall": "right_building",
    "right building": "right_building",
    "tower": "church_tower",
    "steeple": "church_tower",
    "sky": "church_tower",
    "top": "church_tower",
    "upper": "church_tower",
    "full": "full",
}


def install_segmentation_dependencies(cfg: dict[str, Any], comfy_url: str) -> dict[str, Any]:
    report = check_node_types(cfg=cfg, comfy_url=comfy_url, required=set(SEGMENTATION_NODES))
    installs = install_node_packages(cfg, report.get("installable_packages") or {})
    return {
        **report,
        "install_results": installs,
        "note": "Uses comfyui_controlnet_aux (same pack as DepthAnythingPreprocessor).",
    }


def infer_mask_region(segment_prompt: str, fallback: str = "right_building") -> str:
    text = segment_prompt.lower()
    for phrase, region in REGION_KEYWORDS.items():
        if phrase in text:
            return region
    return fallback


def build_grounding_sam_workflow(
    *,
    image_filename: str,
    prompt: str,
    threshold: float = 0.3,
) -> dict[str, Any]:
    """ComfyUI workflow: image + text prompt → mask image."""
    return {
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename},
        },
        "20": {
            "class_type": "GroundingDinoModelLoader",
            "inputs": {"model_name": "GroundingDINO_SwinT_OGC (694MB)"},
        },
        "21": {
            "class_type": "SAMLoader",
            "inputs": {"model_name": "sam_vit_b_01ec64.pth"},
        },
        "22": {
            "class_type": "GroundingDinoSAMSegment",
            "inputs": {
                "sam_model": ["21", 0],
                "grounding_dino_model": ["20", 0],
                "image": ["10", 0],
                "prompt": prompt,
                "threshold": float(threshold),
            },
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "studio_mask", "images": ["22", 0]},
        },
    }


def segment_image_to_mask(
    comfy_client: Any,
    output_dir: Path,
    *,
    image_path: Path,
    segment_prompt: str,
    threshold: float = 0.3,
) -> tuple[Path | None, str]:
    """
    Run GroundingDINO+SAM; return (local_mask_path, fallback_region).
    On failure returns (None, inferred_region).
    """
    fallback = infer_mask_region(segment_prompt)
    try:
        uploaded = comfy_client.upload_image(image_path)
        workflow = build_grounding_sam_workflow(
            image_filename=uploaded,
            prompt=segment_prompt,
            threshold=threshold,
        )
        prompt_id = comfy_client.queue_prompt(workflow)
        history = comfy_client.wait_for_completion(prompt_id)
        outputs = comfy_client.collect_outputs(history)
        for file_info in outputs:
            if file_info.get("filename", "").lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                path = comfy_client.download_file(file_info, output_dir)
                return path, fallback
    except Exception:
        pass
    return None, fallback
