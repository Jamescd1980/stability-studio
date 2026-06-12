"""Image-editing assets: SD1.5 ControlNet, references, edit LoRAs, unified setup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from studio.comfy_deps import check_node_types, install_node_packages
from studio.ip_adapter_assets import (
    IP_ADAPTER_ASSETS,
    REFERENCE_ASSETS,
    _hf_stream_to_file,
    check_ip_adapter_assets,
    check_reference_assets,
    download_ip_adapter_assets,
    install_controlnet_dependencies,
    install_ip_adapter_dependencies,
    model_dirs,
)
from studio.segmentation import SEGMENTATION_NODES, install_segmentation_dependencies

# SD 1.5 ControlNet (photorealistic / cyberrealistic_final)
SD15_CONTROLNET_ASSETS: list[dict[str, Any]] = [
    {
        "filename": "control_v11p_sd15_canny.safetensors",
        "folder": "controlnet",
        "repo": "lllyasviel/control_v11p_sd15_canny",
        "path": "diffusion_pytorch_model.safetensors",
        "size_hint": "~1.4 GB",
    },
    {
        "filename": "control_v11f1p_sd15_depth.safetensors",
        "folder": "controlnet",
        "repo": "lllyasviel/control_v11f1p_sd15_depth",
        "path": "diffusion_pytorch_model.safetensors",
        "size_hint": "~1.4 GB",
    },
]

# Optional SDXL inpaint-tuned checkpoint (regional edits)
INPAINT_CHECKPOINT_ASSETS: list[dict[str, Any]] = [
    {
        "filename": "sd_xl_refiner_1.0_0.9.safetensors",
        "folder": "checkpoints",
        "repo": "stabilityai/stable-diffusion-xl-refiner-1.0",
        "path": "sd_xl_refiner_1.0_0.9.safetensors",
        "size_hint": "~6 GB",
        "optional": True,
        "note": "Optional refiner for polish passes; not required for inpaint_advanced.",
    },
]

# Edit-time LoRAs (concepts hard to prompt)
EDIT_LORA_MANIFEST: list[dict[str, Any]] = [
    {
        "id": "irish_flag_insignia",
        "filename": "irish_flag_insignia.safetensors",
        "note": "Placeholder — add Civitai LoRA when available; use flag_reference=ireland until then.",
        "optional": True,
        "trigger": "irish flag",
        "food_groups": ["photoreal", "fantasy"],
    },
    {
        "id": "anime_eyes_ilustmix",
        "filename": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
        "note": "Bundled with ilustmix style in catalog.",
        "food_groups": ["anime"],
        "trigger": "perfect eyes",
    },
]

EXTENDED_REFERENCE_ASSETS: dict[str, dict[str, str]] = {
    **REFERENCE_ASSETS,
    "usa_flag": {
        "filename": "usa.png",
        "subdir": "flags",
        "url": "https://flagcdn.com/w640/us.png",
        "note": "US flag reference for IP-Adapter edits.",
    },
    "uk_flag": {
        "filename": "uk.png",
        "subdir": "flags",
        "url": "https://flagcdn.com/w640/gb.png",
        "note": "UK flag reference for IP-Adapter edits.",
    },
}

CONTROLNET_FILE_SETS: dict[str, dict[str, str]] = {
    "sdxl": {
        "depth": "controlnet-depth-sdxl-1.0.safetensors",
        "canny": "controlnet-canny-sdxl-1.0.safetensors",
    },
    "sd15": {
        "depth": "control_v11f1p_sd15_depth.safetensors",
        "canny": "control_v11p_sd15_canny.safetensors",
    },
    "sdxl_anime": {
        "depth": "controlnet-depth-sdxl-1.0.safetensors",
        "canny": "controlnet-canny-sdxl-1.0.safetensors",
    },
    "pony_sdxl": {
        "depth": "controlnet-depth-sdxl-1.0.safetensors",
        "canny": "controlnet-canny-sdxl-1.0.safetensors",
    },
}


def controlnet_files_for_architecture(architecture: str) -> dict[str, str]:
    arch = architecture.lower()
    if arch == "sd15":
        return dict(CONTROLNET_FILE_SETS["sd15"])
    return dict(CONTROLNET_FILE_SETS["sdxl"])


def is_sdxl_family(architecture: str) -> bool:
    return architecture.lower() in {"sdxl", "sdxl_anime", "pony_sdxl"}


def is_ipadapter_supported(architecture: str) -> bool:
    return is_sdxl_family(architecture)


def check_sd15_controlnet_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    dirs = model_dirs(cfg)
    installed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for entry in SD15_CONTROLNET_ASSETS:
        folder = dirs[entry["folder"]]
        found = folder / entry["filename"]
        if found.is_file():
            installed.append({**entry, "path": str(found)})
        else:
            missing.append(dict(entry))
    return {"installed": installed, "missing": missing, "ready": not missing}


def download_sd15_controlnet_assets(cfg: dict[str, Any], *, force: bool = False) -> list[dict[str, Any]]:
    dirs = model_dirs(cfg)
    results: list[dict[str, Any]] = []
    for entry in SD15_CONTROLNET_ASSETS:
        dest = dirs[entry["folder"]] / entry["filename"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and not force:
            results.append({"filename": entry["filename"], "path": str(dest), "ok": True, "skipped": True})
            continue
        try:
            path = _hf_stream_to_file(entry["repo"], entry["path"], dest, force=force)
            results.append({"filename": entry["filename"], "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"filename": entry["filename"], "ok": False, "error": str(exc)})
    return results


def ensure_extended_reference(cfg: dict[str, Any], key: str) -> Path:
    from studio.ip_adapter_assets import ensure_reference_asset

    if key in REFERENCE_ASSETS:
        return ensure_reference_asset(cfg, key)
    meta = EXTENDED_REFERENCE_ASSETS.get(key)
    if not meta:
        raise ValueError(f"Unknown reference asset: {key}")
    root = Path(cfg.get("_root", Path(__file__).resolve().parent.parent)) / "assets"
    dest = root / meta["subdir"] / meta["filename"]
    if dest.is_file():
        return dest
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "StabilityStudioMCP/1.0"}
    with requests.get(meta["url"], stream=True, timeout=120, headers=headers) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    return dest


def reference_key_for_instruction(instruction: str) -> str | None:
    text = instruction.lower()
    if "irish" in text or "ireland" in text or "tricolor" in text:
        return "ireland_flag"
    if "american" in text or "usa flag" in text or "us flag" in text:
        return "usa_flag"
    if "british" in text or "uk flag" in text or "union jack" in text:
        return "uk_flag"
    return None


def check_image_editing_readiness(cfg: dict[str, Any], comfy_url: str) -> dict[str, Any]:
    ip = check_ip_adapter_assets(cfg, include_optional=True)
    from studio.ip_adapter_assets import check_controlnet_assets

    cn = check_controlnet_assets(cfg)
    sd15 = check_sd15_controlnet_assets(cfg)
    seg = check_node_types(cfg=cfg, comfy_url=comfy_url, required=set(SEGMENTATION_NODES))
    refs = check_reference_assets(cfg)
    return {
        "ip_adapter": ip,
        "controlnet_sdxl": cn,
        "controlnet_sd15": sd15,
        "segmentation": seg,
        "reference_assets": refs,
        "edit_lora_manifest": EDIT_LORA_MANIFEST,
        "ready_for_sdxl_editing": ip.get("ready") and cn.get("ready"),
        "ready_for_sd15_controlnet": sd15.get("ready"),
    }


def setup_image_editing(
    cfg: dict[str, Any],
    comfy_url: str,
    *,
    include_sd15_controlnet: bool = True,
    include_segmentation: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """One-shot: IP-Adapter + SDXL ControlNet + SD1.5 ControlNet + segmentation nodes."""
    from studio.ip_adapter_assets import download_controlnet_assets

    ip_deps = install_ip_adapter_dependencies(cfg, comfy_url, include_depth=True)
    cn_deps = install_controlnet_dependencies(cfg, comfy_url)
    seg_deps = install_segmentation_dependencies(cfg, comfy_url) if include_segmentation else None
    ip_dl = download_ip_adapter_assets(cfg, include_optional=True, force=force)
    cn_dl = download_controlnet_assets(cfg, force=force)
    sd15_dl = download_sd15_controlnet_assets(cfg, force=force) if include_sd15_controlnet else []
    ref_results: list[dict[str, Any]] = []
    for key in ("ireland_flag", "usa_flag", "uk_flag"):
        try:
            p = ensure_extended_reference(cfg, key)
            ref_results.append({"key": key, "path": str(p), "ok": True})
        except Exception as exc:
            ref_results.append({"key": key, "ok": False, "error": str(exc)})

    readiness = check_image_editing_readiness(cfg, comfy_url)
    restart = any(
        [
            ip_deps.get("install_results"),
            cn_deps.get("install_results"),
            seg_deps.get("install_results") if seg_deps else False,
        ]
    )
    return {
        "ip_adapter_dependencies": ip_deps,
        "controlnet_dependencies": cn_deps,
        "segmentation_dependencies": seg_deps,
        "downloads": {
            "ip_adapter": ip_dl,
            "controlnet_sdxl": cn_dl,
            "controlnet_sd15": sd15_dl,
            "references": ref_results,
        },
        "readiness": readiness,
        "restart_comfyui_required": bool(restart),
        "next_steps": [
            "Restart ComfyUI from Stability Matrix if any custom nodes were installed.",
            "Restart stability-studio MCP if tool list changed.",
            "Use edit_image(image_path, instruction, food_group=...) for guided edits.",
            "Food groups: anime (ilustmix), fantasy (merged_dreams), cyberpunk (n4mik4), photoreal (juggernaut).",
        ],
    }
