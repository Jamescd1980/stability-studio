"""OpenPose / line-art preprocessors and pose-guided SDXL i2i."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from studio.comfy_deps import check_node_types, install_node_packages
from studio.ip_adapter_assets import _hf_stream_to_file, check_ip_adapter_assets, model_dirs

# --- External editors (export PNG at target width × height) ---
OPENPOSE_EDITORS = [
    {
        "name": "OpenPose Editor (Vercel)",
        "url": "https://openpose-editor.vercel.app/",
        "notes": "Drag joints and fingers; set canvas size; export pose PNG.",
    },
    {
        "name": "Open Pose Editor (Zhuyu)",
        "url": "https://zhuyu1997.github.io/open-pose-editor/",
        "notes": "Resolution control; hand keypoints; download pose image.",
    },
]

PREPROCESSORS: dict[str, dict[str, Any]] = {
    "openpose": {
        "node": "OpenposePreprocessor",
        "label": "OpenPose skeleton (body + face + hands)",
        "inputs": {
            "detect_hand": "enable",
            "detect_body": "enable",
            "detect_face": "enable",
            "scale_stick_for_xinsr_cn": "disable",
        },
    },
    "dwpose": {
        "node": "DWPreprocessor",
        "label": "DWPose (often sharper hands)",
        "inputs": {
            "detect_hand": "enable",
            "detect_body": "enable",
            "detect_face": "enable",
            "bbox_detector": "yolox_l.onnx",
            "pose_estimator": "dw-ll_ucoco_384_bs5.torchscript.pt",
        },
    },
    "canny": {
        "node": "Canny",
        "label": "Hard edge map (Canny — matches hardline look)",
        "inputs": {"low_threshold": 0.25, "high_threshold": 0.6},
        "builtin": True,
    },
    "canny_edge": {
        "node": "CannyEdgePreprocessor",
        "label": "Canny edge (controlnet_aux)",
        "inputs": {},
    },
    "anime_lineart": {
        "node": "AnimeLineArtPreprocessor",
        "label": "Anime lineart (clean hard lines)",
        "inputs": {},
    },
    "lineart": {
        "node": "LineArtPreprocessor",
        "label": "Realistic lineart",
        "inputs": {},
    },
    "hed": {
        "node": "HEDPreprocessor",
        "label": "Soft HED edges",
        "inputs": {},
    },
}

POSE_CONTROL_NODES = frozenset(
    {
        "OpenposePreprocessor",
        "DWPreprocessor",
        "Canny",
        "CannyEdgePreprocessor",
        "AnimeLineArtPreprocessor",
        "LineArtPreprocessor",
        "HEDPreprocessor",
        "ControlNetLoader",
        "ControlNetApplyAdvanced",
        "MeshGraphormer-DepthMapPreprocessor",
    }
)

OPENPOSE_CONTROLNET_ASSET: dict[str, Any] = {
    "filename": "OpenPoseXL2.safetensors",
    "folder": "controlnet",
    "repo": "thibaud/controlnet-openpose-sdxl-1.0",
    "path": "OpenPoseXL2.safetensors",
    "size_hint": "~2.5 GB",
    "note": "SDXL OpenPose ControlNet for pose-guided i2i (Pony / SDXL anime).",
}


def openpose_controlnet_path(cfg: dict[str, Any]) -> Path:
    return model_dirs(cfg)["controlnet"] / OPENPOSE_CONTROLNET_ASSET["filename"]


def check_openpose_controlnet_asset(cfg: dict[str, Any]) -> dict[str, Any]:
    path = openpose_controlnet_path(cfg)
    return {
        "filename": OPENPOSE_CONTROLNET_ASSET["filename"],
        "path": str(path),
        "ready": path.is_file() and path.stat().st_size > 10_000_000,
        "size_hint": OPENPOSE_CONTROLNET_ASSET["size_hint"],
        "repo": OPENPOSE_CONTROLNET_ASSET["repo"],
    }


def download_openpose_controlnet(cfg: dict[str, Any], *, force: bool = False) -> Path:
    path = openpose_controlnet_path(cfg)
    if path.is_file() and not force:
        return path
    _hf_stream_to_file(
        OPENPOSE_CONTROLNET_ASSET["repo"],
        OPENPOSE_CONTROLNET_ASSET["path"],
        path,
        force=force,
    )
    return path


def check_pose_control_readiness(cfg: dict[str, Any], comfy_url: str) -> dict[str, Any]:
    nodes = check_node_types(cfg=cfg, comfy_url=comfy_url, required=set(POSE_CONTROL_NODES))
    ip = check_ip_adapter_assets(cfg, include_optional=True)
    openpose_cn = check_openpose_controlnet_asset(cfg)
    depth_canny = [
        a for a in ip.get("assets", []) if a.get("filename", "").startswith("controlnet-")
    ]
    return {
        "preprocessors": {k: v["label"] for k, v in PREPROCESSORS.items()},
        "openpose_editors": OPENPOSE_EDITORS,
        "nodes": nodes,
        "openpose_controlnet": openpose_cn,
        "depth_canny_controlnets": depth_canny,
        "ip_adapter": ip.get("summary", {}),
        "ready_for_extract": nodes.get("ready", False),
        "ready_for_pose_i2i": nodes.get("ready", False) and openpose_cn.get("ready"),
        "workflow_hint": (
            "1) Pose on openpose-editor.vercel.app at target size → export PNG. "
            "2) extract_control_maps on hero still (canny + openpose). "
            "3) generate_image_pose_guided(identity + pose PNG + holding_kunai prompt)."
        ),
    }


def install_pose_control_dependencies(cfg: dict[str, Any], comfy_url: str) -> dict[str, Any]:
    report = check_node_types(cfg=cfg, comfy_url=comfy_url, required=set(POSE_CONTROL_NODES))
    installs = install_node_packages(cfg, report.get("installable_packages") or {})
    return {**report, "install_results": installs}


def setup_pose_control(
    cfg: dict[str, Any],
    comfy_url: str,
    *,
    download_openpose: bool = True,
    force_download: bool = False,
) -> dict[str, Any]:
    deps = install_pose_control_dependencies(cfg, comfy_url)
    dl = None
    if download_openpose:
        try:
            path = download_openpose_controlnet(cfg, force=force_download)
            dl = {"status": "ok", "path": str(path)}
        except Exception as exc:
            dl = {"status": "failed", "error": str(exc)}
    after = check_pose_control_readiness(cfg, comfy_url)
    return {
        "dependencies": deps,
        "openpose_download": dl,
        "readiness": after,
        "restart_comfyui_required": bool(deps.get("install_results")),
        "note": "Restart ComfyUI after new custom nodes. OpenPose XL2 ~2.5 GB.",
    }


def build_preprocess_workflow(
    *,
    image_filename: str,
    preprocessor: str,
    resolution: int = 832,
) -> dict[str, Any]:
    meta = PREPROCESSORS.get(preprocessor)
    if not meta:
        raise ValueError(f"Unknown preprocessor: {preprocessor}. Choose from {list(PREPROCESSORS)}")

    workflow: dict[str, Any] = {
        "10": {"class_type": "LoadImage", "inputs": {"image": image_filename}},
    }
    inputs = dict(meta.get("inputs") or {})
    if meta["node"] not in ("Canny",):
        inputs.setdefault("resolution", int(resolution))
    inputs["image"] = ["10", 0]

    workflow["20"] = {"class_type": meta["node"], "inputs": inputs}
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": f"studio_{preprocessor}", "images": ["20", 0]},
    }
    return workflow


def build_openpose_i2i_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    source_image_filename: str,
    pose_image_filename: str,
    width: int,
    height: int,
    openpose_controlnet_file: str = "OpenPoseXL2.safetensors",
    openpose_strength: float = 0.82,
    preprocess_pose: bool = False,
    pose_resolution: int = 832,
    seed: int | None = None,
    steps: int = 28,
    cfg: float = 5.5,
    sampler: str = "euler_ancestral",
    scheduler: str = "normal",
    denoising_strength: float = 0.38,
    loras: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    import random

    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    loras = loras or []
    last_model = "4"
    last_clip = "4"

    workflow: dict[str, Any] = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "10": {"class_type": "LoadImage", "inputs": {"image": source_image_filename}},
        "21": {"class_type": "LoadImage", "inputs": {"image": pose_image_filename}},
        "12": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["10", 0],
                "upscale_method": "lanczos",
                "width": width,
                "height": height,
                "crop": "center",
            },
        },
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["12", 0], "vae": ["4", 2]}},
        "62": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": openpose_controlnet_file}},
    }

    pose_src: list[str | int] = ["21", 0]
    if preprocess_pose:
        workflow["22"] = {
            "class_type": "OpenposePreprocessor",
            "inputs": {
                "image": ["21", 0],
                "detect_hand": "enable",
                "detect_body": "enable",
                "detect_face": "enable",
                "resolution": int(pose_resolution),
                "scale_stick_for_xinsr_cn": "disable",
            },
        }
        pose_src = ["22", 0]

    for i, lora in enumerate(loras):
        nid = str(30 + i)
        workflow[nid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora.get("name") or lora.get("file"),
                "strength_model": float(lora.get("weight", 0.75)),
                "strength_clip": float(lora.get("weight", 0.75)),
                "model": [last_model, 0],
                "clip": [last_clip, 1],
            },
        }
        last_model = nid
        last_clip = nid

    workflow["6"] = {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": [last_clip, 1]}}
    workflow["7"] = {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": [last_clip, 1]}}
    workflow["73"] = {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "positive": ["6", 0],
            "negative": ["7", 0],
            "control_net": ["62", 0],
            "image": pose_src,
            "strength": float(openpose_strength),
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
    }
    workflow["3"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": float(denoising_strength),
            "model": [last_model, 0],
            "positive": ["73", 0],
            "negative": ["73", 1],
            "latent_image": ["11", 0],
        },
    }
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    }
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "studio_pose_i2i", "images": ["8", 0]},
    }
    return workflow
