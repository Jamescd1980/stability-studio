"""Curated NSFW still-image LoRAs — Illustrious and Pony lanes (not Wan video)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from studio.civitai_download import civitai_api_key, download_civitai_lora
from studio.wan_assets import _find_file, model_dirs

# Civitai downloads + on-disk assets under Stability Matrix Data/Models/Lora/.
NSFW_IMAGE_LORAS: dict[str, dict[str, Any]] = {
    "manga_nsfw_style": {
        "id": "manga_nsfw_style",
        "filename": "Manga_Art_Style_NSFW_E43.safetensors",
        "default_weight": 0.65,
        "styles": ["ilustmix"],
        "base_model": "Illustrious",
        "purpose": "Hentai manga panel look on iLustMix dialogue/intimacy stills.",
        "trigger": "",
        "note": "Already on disk from earlier migration; no Civitai download required.",
    },
    "ntr_mix_style": {
        "id": "ntr_mix_style",
        "filename": "NTR_MIX_4.0_LORA-000007.safetensors",
        "civitai_version_id": "1074877",
        "civitai_page": "https://civitai.com/models/960071",
        "default_weight": 0.6,
        "styles": ["ilustmix", "merged_dreams", "anime"],
        "base_model": "Illustrious",
        "purpose": "NTR MIX romance/drama palette — fantasy romance explicit beats (Jan NTR MIX).",
        "trigger": "",
        "size_hint": "~218 MB",
    },
    "pov_holding_pony": {
        "id": "pov_holding_pony",
        "filename": "concept_povholding-pony-v2.safetensors",
        "default_weight": 0.7,
        "styles": ["pony", "merged_dreams"],
        "base_model": "Pony",
        "purpose": "POV holding / intimacy framing on Prefect Pony and Merged In Dreams.",
        "trigger": "",
        "note": "Already on disk.",
    },
    "hentai_manga_pony": {
        "id": "hentai_manga_pony",
        "filename": "Hentai_Manga_Style_-_for_Pony.safetensors",
        "civitai_version_id": "2072847",
        "civitai_page": "https://civitai.com/models/1831701",
        "default_weight": 0.65,
        "styles": ["pony", "merged_dreams"],
        "base_model": "Pony",
        "purpose": "Explicit hentai manga look on Pony SDXL (rating_explicit scenes).",
        "trigger": "monochrome, greyscale",
        "size_hint": "~218 MB",
    },
    "new_fantasy_core_ill": {
        "id": "new_fantasy_core_ill",
        "filename": "New_Fantasy_CoreV5_-_ILL.safetensors",
        "default_weight": 0.6,
        "styles": ["fantasy_prime", "ilustmix", "anime", "perfection_25d"],
        "base_model": "Illustrious",
        "purpose": "Dark fantasy / grimdark palette on Illustrious and 2.5D fantasy styles.",
        "trigger": "Newfantasycore",
        "note": "Also available: New Fantasy Core - PONY.safetensors, NewFantasyCore-SDXL.safetensors.",
    },
}

NSFW_IMAGE_LORA_BUNDLES: dict[str, list[str]] = {
    "illustrious_intimacy": ["manga_nsfw_style"],
    "illustrious_romance": ["ntr_mix_style"],
    "pony_explicit": ["hentai_manga_pony", "pov_holding_pony"],
    "fantasy_romance": ["ntr_mix_style", "pov_holding_pony"],
    "dark_fantasy": ["new_fantasy_core_ill"],
}


def _lora_dir(cfg: dict[str, Any]) -> Path | None:
    dirs = model_dirs(cfg)
    return dirs.get("loras")


def _resolve_ids(lora_ids: list[str] | None, bundle: str) -> list[str]:
    if lora_ids:
        return lora_ids
    if bundle:
        ids = NSFW_IMAGE_LORA_BUNDLES.get(bundle)
        if not ids:
            raise ValueError(f"Unknown bundle {bundle!r}; choose from {list(NSFW_IMAGE_LORA_BUNDLES)}")
        return ids
    return list(NSFW_IMAGE_LORAS)


def resolve_nsfw_lora_list(
    lora_ids: list[str] | None = None,
    *,
    bundle: str = "",
    style: str = "",
) -> list[dict[str, Any]]:
    """Return [{file, weight, id}, …] for generate_image(loras=…)."""
    ids = _resolve_ids(lora_ids, bundle)
    if style:
        ids = [i for i in ids if style in (NSFW_IMAGE_LORAS[i].get("styles") or [])]
    out: list[dict[str, Any]] = []
    for lid in ids:
        entry = NSFW_IMAGE_LORAS.get(lid)
        if not entry:
            raise ValueError(f"Unknown NSFW image LoRA id {lid!r}")
        out.append(
            {
                "file": entry["filename"],
                "name": entry["filename"],
                "weight": float(entry.get("default_weight", 0.65)),
                "id": lid,
                "trigger": entry.get("trigger") or "",
            }
        )
    return out


def check_nsfw_image_loras(
    cfg: dict[str, Any],
    lora_ids: list[str] | None = None,
    *,
    comfy_url: str = "",
) -> dict[str, Any]:
    lora_dir = _lora_dir(cfg)
    ids = _resolve_ids(lora_ids, "")
    comfy_loras: set[str] | None = None
    if comfy_url:
        try:
            r = requests.get(f"{comfy_url.rstrip('/')}/object_info/LoraLoader", timeout=5)
            r.raise_for_status()
            names = r.json().get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [[]])
            comfy_loras = set(names[0]) if names else set()
        except Exception:
            comfy_loras = None

    items: list[dict[str, Any]] = []
    ready = 0
    for lid in ids:
        entry = NSFW_IMAGE_LORAS[lid]
        found = _find_file(entry["filename"], model_dirs(cfg), "loras") if lora_dir else None
        on_comfy = (
            entry["filename"] in comfy_loras
            if comfy_loras is not None
            else None
        )
        is_ready = bool(found) or bool(on_comfy)
        item = {
            "id": lid,
            "filename": entry["filename"],
            "ready": is_ready,
            "path": str(found) if found else None,
            "on_comfyui": on_comfy,
            "styles": entry.get("styles", []),
            "base_model": entry.get("base_model"),
            "default_weight": entry.get("default_weight"),
            "purpose": entry.get("purpose"),
            "trigger": entry.get("trigger") or None,
            "civitai_version_id": entry.get("civitai_version_id"),
        }
        if is_ready:
            ready += 1
        items.append(item)
    return {
        "ready": ready == len(ids),
        "lora_dir": str(lora_dir) if lora_dir else None,
        "comfyui_checked": comfy_url or None,
        "items": items,
        "bundles": NSFW_IMAGE_LORA_BUNDLES,
    }


def download_nsfw_image_loras(
    cfg: dict[str, Any],
    *,
    lora_ids: list[str] | None = None,
    bundle: str = "",
    force: bool = False,
) -> list[dict[str, Any]]:
    ids = _resolve_ids(lora_ids, bundle)
    results: list[dict[str, Any]] = []
    for lid in ids:
        entry = NSFW_IMAGE_LORAS[lid]
        vid = entry.get("civitai_version_id")
        if not vid:
            found = _find_file(entry["filename"], model_dirs(cfg), "loras")
            results.append(
                {
                    "id": lid,
                    "action": "skipped_no_download_metadata",
                    "ready": found is not None,
                    "path": str(found) if found else None,
                }
            )
            continue
        path = download_civitai_lora(
            cfg,
            filename=entry["filename"],
            version_id=vid,
            force=force,
        )
        results.append({"id": lid, "action": "downloaded", "path": str(path)})
    return results


def list_nsfw_image_loras_for_style(style: str) -> list[dict[str, Any]]:
    """Catalog helper — LoRAs recommended for a style id."""
    out: list[dict[str, Any]] = []
    for lid, entry in NSFW_IMAGE_LORAS.items():
        if style in (entry.get("styles") or []):
            out.append(
                {
                    "id": lid,
                    "filename": entry["filename"],
                    "default_weight": entry.get("default_weight"),
                    "trigger": entry.get("trigger") or "",
                    "purpose": entry.get("purpose"),
                    "bundles": [b for b, ids in NSFW_IMAGE_LORA_BUNDLES.items() if lid in ids],
                }
            )
    return out
