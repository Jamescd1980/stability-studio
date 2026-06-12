"""Wan video asset manifest, missing-file checks, and Hugging Face downloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

HF_BASE = "https://huggingface.co"

# Catalog workflow id → files required beyond custom nodes (already installed).
WORKFLOW_ASSETS: dict[str, list[dict[str, str]]] = {
    "v2v_5b": [
        {
            "filename": "wan2.2_ti2v_5B_fp16.safetensors",
            "folder": "diffusion_models",
            "repo": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
            "path": "split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors",
            "size_hint": "~10 GB",
        },
        {
            "filename": "wan2.2_vae.safetensors",
            "folder": "vae",
            "repo": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
            "path": "split_files/vae/wan2.2_vae.safetensors",
            "size_hint": "~1.4 GB",
            "alt_local": "wan_2.1_vae.safetensors",
        },
        {
            "filename": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "folder": "text_encoders",
            "repo": "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
            "path": "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "size_hint": "~6 GB",
        },
    ],
    "i2v_5b": [
        {
            "filename": "wan2.2_ti2v_5B_fp16.safetensors",
            "folder": "diffusion_models",
            "repo": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
            "path": "split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors",
            "size_hint": "~10 GB",
        },
        {
            "filename": "wan2.2_vae.safetensors",
            "folder": "vae",
            "repo": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
            "path": "split_files/vae/wan2.2_vae.safetensors",
            "size_hint": "~1.4 GB",
            "alt_local": "wan_2.1_vae.safetensors",
        },
        {
            "filename": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "folder": "text_encoders",
            "repo": "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
            "path": "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "size_hint": "~6 GB",
        },
    ],
    "i2v": [
        {
            "filename": "Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
            "folder": "loras",
            "repo": "lightx2v/Wan2.1-I2V-14B-480P-StepDistill-CfgDistill-Lightx2v",
            "path": "loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
            "size_hint": "~739 MB",
        },
        {
            "filename": "Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors",
            "folder": "diffusion_models",
            "repo": "Kijai/WanVideo_comfy_fp8_scaled",
            "path": "I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors",
            "size_hint": "~14 GB",
        },
        {
            "filename": "Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors",
            "folder": "diffusion_models",
            "repo": "Kijai/WanVideo_comfy_fp8_scaled",
            "path": "I2V/Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors",
            "size_hint": "~14 GB",
        },
        {
            "filename": "Wan2_1_VAE_bf16.safetensors",
            "folder": "vae",
            "repo": "Kijai/WanVideo_comfy",
            "path": "Wan2_1_VAE_bf16.safetensors",
            "size_hint": "~254 MB",
            "alt_local": "wan_2.1_vae.safetensors",
        },
    ],
    "i2v_wan21": [
        {
            "filename": "Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors",
            "folder": "loras",
            "repo": "Kijai/WanVideo_comfy",
            "path": "Wan21_T2V_14B_lightx2v_cfg_step_distill_lora_rank32.safetensors",
            "size_hint": "~317 MB",
        },
        {
            "filename": "Wan2.1-T2V-1.3B-Self-Forcing-DMD-VACE-FP16.safetensors",
            "folder": "diffusion_models",
            "size_hint": "manual",
            "note": "Not on Hugging Face under this exact name. Install Self-Forcing VACE from the workflow author or use i2v_gpu instead.",
        },
    ],
    "i2v_gpu": [
        {
            "filename": "wan2.1_i2v_480p_14B_bf16.safetensors",
            "folder": "diffusion_models",
            "note": "MCP default GPU I2V path (built from t2v workflow). No extra LoRAs.",
        },
    ],
    "t2v": [
        {
            "filename": "wan2.1_t2v_1.3B_bf16.safetensors",
            "folder": "diffusion_models",
        },
        {
            "filename": "umt5-xxl-enc-bf16.safetensors",
            "folder": "text_encoders",
        },
        {
            "filename": "wan_2.1_vae.safetensors",
            "folder": "vae",
        },
    ],
}

V2V_NOTE = (
    "V2V extend: generate_video(mode='v2v', video_path='clip.mp4', prompt='...'). "
    "Default workflow v2v_5b_painter — extracts last frame, runs Wan 2.2 TI2V-5B + PainterI2V, "
    "then concat source+continuation when concat_source=true (default). "
    "Same assets as i2v_5b. Optional LoRAs via lora_ids / lora_bundle. Catalog ids: v2v_5b, v2v_5b_painter."
)

FOLDER_MAP = {
    "loras": "Lora",
    "diffusion_models": "DiffusionModels",
    "vae": "VAE",
    "text_encoders": "TextEncoders",
}


def model_dirs(cfg: dict[str, Any]) -> dict[str, Path]:
    sm = cfg.get("stability_matrix", {})
    models = Path(sm.get("models", ""))
    return {key: models / sub for key, sub in FOLDER_MAP.items()}


def hf_download_url(repo: str, path: str) -> str:
    return f"{HF_BASE}/{repo}/resolve/main/{quote(path, safe='/')}"


def _find_file(name: str, dirs: dict[str, Path], folder_key: str) -> Path | None:
    root = dirs.get(folder_key)
    if not root or not root.is_dir():
        return None
    direct = root / name
    if direct.is_file():
        return direct
    for hit in root.rglob(name):
        if hit.is_file():
            return hit
    return None


def check_workflow_assets(cfg: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    """Return installed/missing files for a catalog workflow id."""
    entries = WORKFLOW_ASSETS.get(workflow_id, [])
    dirs = model_dirs(cfg)
    installed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for entry in entries:
        filename = entry["filename"]
        folder = entry.get("folder", "diffusion_models")
        found = _find_file(filename, dirs, folder)
        if not found and entry.get("alt_local"):
            alt = _find_file(entry["alt_local"], dirs, folder)
            if alt:
                installed.append({**entry, "path": str(alt), "via_alt": entry["alt_local"]})
                continue
        if found:
            installed.append({**entry, "path": str(found)})
        else:
            item = dict(entry)
            if entry.get("repo") and entry.get("path"):
                item["download_url"] = hf_download_url(entry["repo"], entry["path"])
            missing.append(item)

    return {
        "workflow_id": workflow_id,
        "installed": installed,
        "missing": missing,
        "ready": len(missing) == 0,
    }


def check_all_video_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    workflows = ["t2v", "i2v_5b", "v2v_5b", "i2v_gpu", "i2v", "i2v_wan21"]
    by_workflow = {wid: check_workflow_assets(cfg, wid) for wid in workflows}
    return {
        "v2v_note": V2V_NOTE,
        "workflows": by_workflow,
        "summary": {
            wid: {"ready": data["ready"], "missing_count": len(data["missing"])}
            for wid, data in by_workflow.items()
        },
    }


def download_asset(
    cfg: dict[str, Any],
    entry: dict[str, str],
    *,
    force: bool = False,
) -> Path:
    """Download one manifest entry to the Stability Matrix models folder."""
    if not entry.get("repo") or not entry.get("path"):
        raise ValueError(f"No download URL for {entry.get('filename')}")

    dirs = model_dirs(cfg)
    folder = entry.get("folder", "diffusion_models")
    dest_dir = dirs.get(folder)
    if dest_dir is None:
        raise ValueError(f"Unknown folder key: {folder}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / entry["filename"]
    if dest.is_file() and not force:
        return dest

    # Prefer huggingface_hub for large LFS / Xet files.
    try:
        from huggingface_hub import hf_hub_download

        fetched = Path(
            hf_hub_download(
                entry["repo"],
                entry["path"],
                local_dir=str(dest_dir),
                local_dir_use_symlinks=False,
                force_download=force,
            )
        )
        if fetched.resolve() != dest.resolve() and fetched.is_file():
            fetched.replace(dest)
        return dest if dest.is_file() else fetched
    except ImportError:
        pass

    url = hf_download_url(entry["repo"], entry["path"])
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    tmp.replace(dest)
    return dest


def download_missing(
    cfg: dict[str, Any],
    workflow_id: str,
    *,
    include_large: bool = True,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Download missing assets for a workflow. Skips multi-GB files when include_large=False."""
    status = check_workflow_assets(cfg, workflow_id)
    results: list[dict[str, Any]] = []
    for entry in status["missing"]:
        if not entry.get("repo"):
            results.append({"filename": entry["filename"], "skipped": True, "reason": entry.get("note", "no URL")})
            continue
        size_hint = entry.get("size_hint", "")
        if not include_large and "GB" in size_hint:
            results.append({"filename": entry["filename"], "skipped": True, "reason": "large file; pass include_large=True"})
            continue
        try:
            path = download_asset(cfg, entry, force=force)
            results.append({"filename": entry["filename"], "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"filename": entry["filename"], "ok": False, "error": str(exc)})
    return results
