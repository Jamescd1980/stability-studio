"""HunyuanVideo 1.5 asset manifest, missing-file checks, and Hugging Face downloads."""

from __future__ import annotations

from typing import Any

from studio.wan_assets import (
    _find_file,
    download_asset,
    hf_download_url,
    model_dirs,
)

HF_REPO = "Comfy-Org/HunyuanVideo_1.5_repackaged"
HF_PREFIX = "split_files"

# Shared across T2V / I2V workflows.
_TEXT_ENCODERS: list[dict[str, str]] = [
    {
        "filename": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "folder": "text_encoders",
        "repo": HF_REPO,
        "path": f"{HF_PREFIX}/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "size_hint": "~8 GB",
    },
    {
        "filename": "byt5_small_glyphxl_fp16.safetensors",
        "folder": "text_encoders",
        "repo": HF_REPO,
        "path": f"{HF_PREFIX}/text_encoders/byt5_small_glyphxl_fp16.safetensors",
        "size_hint": "~400 MB",
    },
]

_VAE: dict[str, str] = {
    "filename": "hunyuanvideo15_vae_fp16.safetensors",
    "folder": "vae",
    "repo": HF_REPO,
    "path": f"{HF_PREFIX}/vae/hunyuanvideo15_vae_fp16.safetensors",
    "size_hint": "~500 MB",
}

# Catalog workflow id → files required beyond custom nodes.
WORKFLOW_ASSETS: dict[str, list[dict[str, str]]] = {
    "hunyuan_t2v": [
        *_TEXT_ENCODERS,
        _VAE,
        {
            "filename": "hunyuanvideo1.5_720p_t2v_fp16.safetensors",
            "folder": "diffusion_models",
            "repo": HF_REPO,
            "path": f"{HF_PREFIX}/diffusion_models/hunyuanvideo1.5_720p_t2v_fp16.safetensors",
            "size_hint": "~16.7 GB",
            "note": "Distilled variants on HF: hunyuanvideo1.5_720p_t2v_cfg_distilled_fp16, 480p_t2v_*",
        },
    ],
    "hunyuan_i2v": [
        *_TEXT_ENCODERS,
        _VAE,
        {
            "filename": "hunyuanvideo1.5_720p_i2v_fp16.safetensors",
            "folder": "diffusion_models",
            "repo": HF_REPO,
            "path": f"{HF_PREFIX}/diffusion_models/hunyuanvideo1.5_720p_i2v_fp16.safetensors",
            "size_hint": "~16.7 GB",
            "note": "Distilled variants on HF: hunyuanvideo1.5_720p_i2v_cfg_distilled_fp16, 480p_i2v_*",
        },
    ],
    "hunyuan_sr": [
        {
            "filename": "hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors",
            "folder": "diffusion_models",
            "repo": HF_REPO,
            "path": f"{HF_PREFIX}/diffusion_models/hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors",
            "size_hint": "~16.7 GB",
            "optional": True,
            "note": "Optional 1080p super-resolution pass — not required for base T2V/I2V",
        },
    ],
}

ROUTING_NOTE = (
    "HunyuanVideo 1.5 assets only — generate_video routing not wired yet. "
    "Use ComfyUI template workflows (Comfy-Org/workflow_templates) until engine support lands. "
    "Video weights must live on GenerationHost /mnt/game (scripts/generation-host_download_hunyuan15.sh). "
    "Prefer full FP16 I2V/T2V — not distilled FP8. Never download Hunyuan video onto the main rig."
)


def check_workflow_assets(cfg: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    """Return installed/missing files for a catalog Hunyuan workflow id."""
    entries = WORKFLOW_ASSETS.get(workflow_id, [])
    dirs = model_dirs(cfg)
    installed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    optional_missing: list[dict[str, Any]] = []

    for entry in entries:
        filename = entry["filename"]
        folder = entry.get("folder", "diffusion_models")
        found = _find_file(filename, dirs, folder)
        if found:
            installed.append({**entry, "path": str(found)})
        else:
            item = dict(entry)
            if entry.get("repo") and entry.get("path"):
                item["download_url"] = hf_download_url(entry["repo"], entry["path"])
            if entry.get("optional"):
                optional_missing.append(item)
            else:
                missing.append(item)

    return {
        "workflow_id": workflow_id,
        "installed": installed,
        "missing": missing,
        "optional_missing": optional_missing,
        "ready": len(missing) == 0,
        "routing_note": ROUTING_NOTE,
    }


def check_all_hunyuan_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    workflows = ["hunyuan_t2v", "hunyuan_i2v", "hunyuan_sr"]
    by_workflow = {wid: check_workflow_assets(cfg, wid) for wid in workflows}
    return {
        "routing_note": ROUTING_NOTE,
        "repo": HF_REPO,
        "workflows": by_workflow,
        "summary": {
            wid: {
                "ready": data["ready"],
                "missing_count": len(data["missing"]),
                "optional_missing_count": len(data.get("optional_missing", [])),
            }
            for wid, data in by_workflow.items()
        },
    }


def download_missing(
    cfg: dict[str, Any],
    workflow_id: str,
    *,
    include_large: bool = True,
    include_optional: bool = False,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Download missing assets for a Hunyuan workflow. Skips multi-GB files when include_large=False."""
    # Remote GenerationHost: MCP model_dirs often point at the main-rig SM tree — refuse
    # dumping multi-GB video weights there. Use generation-host_download_hunyuan15.sh instead.
    comfy = cfg.get("comfyui") or {}
    models_root = str((cfg.get("stability_matrix") or {}).get("models") or "")
    if comfy.get("local") is False or (
        isinstance(comfy.get("url"), str) and "127.0.0.1" not in comfy["url"] and "localhost" not in comfy["url"]
    ):
        if "StabilityMatrix-win-x64" in models_root.replace("\\", "/") and "/mnt/game" not in models_root.replace(
            "\\", "/"
        ):
            return [
                {
                    "ok": False,
                    "skipped": True,
                    "reason": (
                        "Refuse Hunyuan video download onto main-rig model path. "
                        "Run scripts/generation-host_download_hunyuan15.sh on GENERATION_HOST (/mnt/game) "
                        "for full FP16 weights."
                    ),
                    "models_path": models_root,
                    "routing_note": ROUTING_NOTE,
                }
            ]

    status = check_workflow_assets(cfg, workflow_id)
    results: list[dict[str, Any]] = []
    pending = list(status["missing"])
    if include_optional:
        pending.extend(status.get("optional_missing", []))

    for entry in pending:
        if not entry.get("repo"):
            results.append(
                {"filename": entry["filename"], "skipped": True, "reason": entry.get("note", "no URL")}
            )
            continue
        size_hint = entry.get("size_hint", "")
        if not include_large and "GB" in size_hint:
            results.append(
                {
                    "filename": entry["filename"],
                    "skipped": True,
                    "reason": "large file; pass include_large=True",
                }
            )
            continue
        try:
            path = download_asset(cfg, entry, force=force)
            results.append({"filename": entry["filename"], "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"filename": entry["filename"], "ok": False, "error": str(exc)})
    return results
