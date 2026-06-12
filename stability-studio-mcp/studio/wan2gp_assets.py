"""Wan2GP install paths and I2V asset readiness (separate from ComfyUI Wan workflows)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

WAN2GP_I2V_FILES = [
    {
        "filename": "wan2.2_image2video_14B_high_quanto_mbf16_int8.safetensors",
        "note": "Wan 2.2 I2V 14B high-noise (base)",
    },
    {
        "filename": "wan2.2_image2video_14B_low_quanto_mbf16_int8.safetensors",
        "note": "Wan 2.2 I2V 14B low-noise (base)",
    },
    {
        "filename": "wan22EnhancedLightning_v2I2VFP8HIGH.safetensors",
        "note": "Wan 2.2 I2V Lightning v2 high-noise (Enhanced preset)",
    },
    {
        "filename": "wan22EnhancedLightning_v2I2VFP8LOW.safetensors",
        "note": "Wan 2.2 I2V Lightning v2 low-noise (Enhanced preset)",
    },
]


def wan2gp_root(cfg: dict[str, Any]) -> Path:
    pkg = cfg.get("wan2gp", {}).get("root")
    if pkg:
        return Path(pkg)
    data = Path(cfg["stability_matrix"]["data"])
    return data / "Packages" / "Wan2GP"


def check_wan2gp_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    from studio.output_paths import delivery_dir, sync_wan2gp_save_paths

    root = wan2gp_root(cfg)
    ckpts = root / "ckpts"
    delivery = delivery_dir(cfg)
    save_sync = sync_wan2gp_save_paths(cfg)
    files: list[dict[str, Any]] = []
    for entry in WAN2GP_I2V_FILES:
        path = ckpts / entry["filename"]
        files.append(
            {
                **entry,
                "path": str(path),
                "ready": path.is_file(),
                "size_mb": round(path.stat().st_size / (1024 * 1024), 1) if path.is_file() else None,
            }
        )
    base_ready = all(f["ready"] for f in files[:2])
    lightning_ready = all(f["ready"] for f in files[2:])
    return {
        "root": str(root),
        "ckpts": str(ckpts),
        "outputs": str(delivery or (root / "outputs")),
        "save_path_sync": save_sync,
        "preset_enhanced_lightning": "defaults/i2v_2_2_Enhanced_Lightning_v2.json",
        "files": files,
        "summary": {
            "base_i2v_14b": base_ready,
            "lightning_v2_i2v": lightning_ready,
            "any_i2v": base_ready or lightning_ready,
        },
        "usage": "Launch Wan2GP from Stability Matrix; pick Wan 2.2 Image2video 14B or Enhanced Lightning v2 for hero I2V clips.",
        "mcp_note": "generate_video uses ComfyUI; Wan2GP is manual or future wan2gp backend — see get_generation_context.media_paths.",
    }


def download_wan2gp_lightning(cfg: dict[str, Any], *, force: bool = False) -> list[dict[str, Any]]:
    from huggingface_hub import hf_hub_download

    ckpts = wan2gp_root(cfg) / "ckpts"
    ckpts.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for entry in WAN2GP_I2V_FILES[2:]:
        dest = ckpts / entry["filename"]
        item = dict(entry, dest=str(dest))
        if dest.is_file() and not force:
            item["status"] = "skipped"
            results.append(item)
            continue
        try:
            path = hf_hub_download(
                repo_id="DeepBeepMeep/Wan2.2",
                filename=entry["filename"],
                local_dir=str(ckpts),
                local_dir_use_symlinks=False,
                force_download=force,
            )
            item["status"] = "ok"
            item["path"] = path
        except Exception as exc:
            item["status"] = "error"
            item["error"] = str(exc)
        results.append(item)
    return results
