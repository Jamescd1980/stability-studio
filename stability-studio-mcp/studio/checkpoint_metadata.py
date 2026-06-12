"""Checkpoint architecture detection and Civitai cm-info sync."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def stable_diffusion_models_dir(cfg: dict[str, Any]) -> Path:
    sm = cfg.get("stability_matrix", {})
    return Path(sm.get("models", "")) / "StableDiffusion"


def find_checkpoint_path(cfg: dict[str, Any], filename: str) -> Path | None:
    if not filename:
        return None
    root = stable_diffusion_models_dir(cfg)
    direct = root / filename
    if direct.is_file():
        return direct
    if root.is_dir():
        for hit in root.rglob(filename):
            if hit.is_file():
                return hit
    packages = cfg.get("stability_matrix", {}).get("packages", {})
    comfy_ckpt = Path(packages.get("comfyui", "")) / "models" / "checkpoints" / filename
    if comfy_ckpt.is_file():
        return comfy_ckpt
    return None


def sniff_architecture_from_safetensors(path: Path) -> str | None:
    """Return sd15 | sdxl | flux2_klein | unknown from tensor key patterns."""
    try:
        from safetensors import safe_open
    except ImportError:
        return None
    if not path.is_file():
        return None
    try:
        with safe_open(str(path), framework="pt") as f:
            keys = list(f.keys())
    except Exception:
        return None
    if not keys:
        return None
    joined = " ".join(keys[:200])
    if any("model.diffusion_model.label_emb" in k for k in keys):
        return "sdxl"
    if any("conditioner" in k for k in keys) or "text_encoders" in joined:
        if any("flux" in k.lower() for k in keys[:50]):
            return "flux2_klein"
        return "sdxl"
    if any(k.startswith("cond_stage_model") for k in keys):
        return "sd15"
    if any("double_blocks" in k for k in keys):
        return "flux2_klein"
    return "unknown"


def read_civitai_cm_info(checkpoint_path: Path) -> dict[str, Any] | None:
    """Read Stability Matrix Civitai sidecar next to checkpoint."""
    stem = checkpoint_path.name
    for suffix in (".cm-info.json", ".cm_info.json"):
        sidecar = checkpoint_path.parent / f"{Path(stem).stem}{suffix}"
        if not sidecar.is_file():
            sidecar = checkpoint_path.with_suffix(suffix)
        if sidecar.is_file():
            try:
                return json.loads(sidecar.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    # Stability Matrix naming: file.safetensors -> file.cm-info.json
    sidecar = checkpoint_path.parent / f"{checkpoint_path.stem}.cm-info.json"
    if sidecar.is_file():
        try:
            return json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def architecture_from_civitai_meta(meta: dict[str, Any]) -> str | None:
    base = str(meta.get("BaseModel") or meta.get("baseModel") or "").strip().lower()
    if not base:
        ver = str(meta.get("VersionDescription") or meta.get("ModelDescription") or "").lower()
        if "sdxl" in ver or "pony" in ver:
            return "pony_sdxl" if "pony" in ver else "sdxl"
        if "sd 1.5" in ver or "sd1.5" in ver or "sd 1.5" in base:
            return "sd15"
        if "flux" in ver:
            return "flux2_klein"
    mapping = {
        "sd 1.5": "sd15",
        "sd1.5": "sd15",
        "sd 1.5 hyper": "sd15",
        "sdxl 1.0": "sdxl",
        "sdxl": "sdxl",
        "pony": "pony_sdxl",
        "flux.1 d": "flux2_klein",
        "flux": "flux2_klein",
    }
    for key, arch in mapping.items():
        if key in base:
            return arch
    return None


def resolve_checkpoint_architecture(
    cfg: dict[str, Any],
    checkpoint_filename: str,
    catalog_architecture: str | None = None,
) -> dict[str, Any]:
    """Sniff on-disk checkpoint and compare to catalog architecture."""
    path = find_checkpoint_path(cfg, checkpoint_filename)
    out: dict[str, Any] = {
        "checkpoint": checkpoint_filename,
        "path": str(path) if path else None,
        "catalog_architecture": catalog_architecture,
        "detected_architecture": None,
        "civitai_base_model": None,
        "mismatch": False,
        "warnings": [],
    }
    if not path:
        out["warnings"].append("Checkpoint file not found on disk")
        return out

    meta = read_civitai_cm_info(path)
    if meta:
        out["civitai_base_model"] = meta.get("BaseModel") or meta.get("baseModel")
        civ_arch = architecture_from_civitai_meta(meta)
        if civ_arch:
            out["detected_architecture"] = civ_arch

    if not out["detected_architecture"]:
        out["detected_architecture"] = sniff_architecture_from_safetensors(path)

    cat = (catalog_architecture or "").lower()
    det = (out["detected_architecture"] or "").lower()
    if cat and det and det != "unknown":
        cat_family = cat
        det_family = det
        if cat_family in {"sdxl_anime", "pony_sdxl"} and det_family == "sdxl":
            pass  # pony/sniff often reports sdxl
        elif cat_family == "pony_sdxl" and det_family == "sdxl":
            pass
        elif cat_family != det_family:
            out["mismatch"] = True
            out["warnings"].append(
                f"Catalog says {catalog_architecture} but checkpoint looks like {out['detected_architecture']}"
            )
    return out


def validate_style_architecture(
    cfg: dict[str, Any],
    style_id: str,
    catalog_architecture: str,
    checkpoint: str,
) -> dict[str, Any]:
    report = resolve_checkpoint_architecture(cfg, checkpoint, catalog_architecture)
    report["style"] = style_id
    return report


def sync_catalog_architecture_from_disk(
    catalog_data: dict[str, Any],
    cfg: dict[str, Any],
    *,
    dry_run: bool = True,
) -> list[dict[str, Any]]:
    """Update style architecture fields from cm-info / safetensors sniff."""
    changes: list[dict[str, Any]] = []
    styles = catalog_data.get("styles", {})
    for sid, style in styles.items():
        ckpt = style.get("checkpoint")
        if not ckpt:
            continue
        current = style.get("architecture")
        report = resolve_checkpoint_architecture(cfg, ckpt, current)
        detected = report.get("detected_architecture")
        if not detected or detected == "unknown":
            continue
        if detected != current:
            entry = {
                "style": sid,
                "from": current,
                "to": detected,
                "checkpoint": ckpt,
                "civitai_base_model": report.get("civitai_base_model"),
            }
            changes.append(entry)
            if not dry_run:
                style["architecture"] = detected
    return changes
