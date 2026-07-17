"""Probe ComfyUI (often a remote generation host) for installed model filenames.

Windows may see NTFS model files as zeroed while Linux ComfyUI reads them fine.
For readiness / Jan agents, trust the live ComfyUI object_info list when reachable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import requests


def file_has_payload(path: Path) -> bool:
    """True if path exists and is not an empty/zeroed shell."""
    try:
        if not path.is_file() or path.stat().st_size <= 0:
            return False
        with path.open("rb") as f:
            head = f.read(64)
        return bool(head) and not all(x == 0 for x in head)
    except OSError:
        return False


def _comfy_url(cfg: dict[str, Any]) -> str:
    return str((cfg.get("comfyui") or {}).get("url") or "").rstrip("/")


@lru_cache(maxsize=8)
def _object_info_cached(comfy_url: str, node: str) -> dict[str, Any] | None:
    if not comfy_url:
        return None
    try:
        r = requests.get(f"{comfy_url}/object_info/{node}", timeout=12)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def clear_comfy_model_cache() -> None:
    _object_info_cached.cache_clear()


def _list_from_node(comfy_url: str, node: str, field_hints: tuple[str, ...]) -> list[str]:
    data = _object_info_cached(comfy_url, node)
    if not data or node not in data:
        return []
    req = (data[node].get("input") or {}).get("required") or {}
    for key in field_hints:
        spec = req.get(key)
        if isinstance(spec, list) and spec and isinstance(spec[0], list):
            return [str(x) for x in spec[0]]
    for _key, spec in req.items():
        if isinstance(spec, list) and spec and isinstance(spec[0], list):
            return [str(x) for x in spec[0]]
    return []


def list_comfy_checkpoints(cfg: dict[str, Any]) -> list[str]:
    return _list_from_node(_comfy_url(cfg), "CheckpointLoaderSimple", ("ckpt_name",))


def list_comfy_loras(cfg: dict[str, Any]) -> list[str]:
    return _list_from_node(_comfy_url(cfg), "LoraLoader", ("lora_name",))


def list_comfy_vaes(cfg: dict[str, Any]) -> list[str]:
    return _list_from_node(_comfy_url(cfg), "VAELoader", ("vae_name",))


def list_comfy_unets(cfg: dict[str, Any]) -> list[str]:
    return _list_from_node(_comfy_url(cfg), "UNETLoader", ("unet_name",))


def list_comfy_clips(cfg: dict[str, Any]) -> list[str]:
    return _list_from_node(_comfy_url(cfg), "CLIPLoader", ("clip_name",))


def remote_model_inventory(cfg: dict[str, Any]) -> dict[str, Any]:
    url = _comfy_url(cfg)
    if not url:
        return {"comfyui_url": None, "reachable": False}
    ckpts = list_comfy_checkpoints(cfg)
    return {
        "comfyui_url": url,
        "reachable": bool(ckpts),
        "checkpoints": ckpts,
        "loras": list_comfy_loras(cfg),
        "vaes": list_comfy_vaes(cfg),
        "unets": list_comfy_unets(cfg),
        "clips": list_comfy_clips(cfg),
        "note": (
            "Filenames reported by live ComfyUI. Prefer this over local Windows disk "
            "when models live on a shared NTFS volume mounted by the generation host."
        ),
    }


def checkpoint_available(cfg: dict[str, Any], filename: str) -> tuple[bool, str]:
    """Return (ok, source) where source is local|comfyui|missing."""
    root = Path((cfg.get("stability_matrix") or {}).get("models", ""))
    local = root / "StableDiffusion" / filename
    if file_has_payload(local):
        return True, "local"
    if local.is_file() and not file_has_payload(local):
        # Zeroed Windows view — still may be OK on the generation host
        pass
    else:
        # rglob local non-zero
        ckpt_dir = root / "StableDiffusion"
        if ckpt_dir.is_dir():
            for hit in ckpt_dir.rglob(filename):
                if file_has_payload(hit):
                    return True, "local"
    remote = list_comfy_checkpoints(cfg)
    # ComfyUI may show subfolder paths; match basename
    basenames = {Path(n).name for n in remote}
    if filename in remote or filename in basenames:
        return True, "comfyui"
    return False, "missing"


def unet_available(cfg: dict[str, Any], filename: str) -> tuple[bool, str]:
    if filename in list_comfy_unets(cfg) or Path(filename).name in {
        Path(n).name for n in list_comfy_unets(cfg)
    }:
        return True, "comfyui"
    root = Path((cfg.get("stability_matrix") or {}).get("models", ""))
    for folder in ("DiffusionModels", "StableDiffusion"):
        p = root / folder / filename
        if file_has_payload(p):
            return True, "local"
    return False, "missing"


def companion_available(cfg: dict[str, Any], filename: str, *, role: str) -> tuple[bool, str]:
    if role == "vae":
        names = list_comfy_vaes(cfg)
    else:
        names = list_comfy_clips(cfg)
    basenames = {Path(n).name for n in names}
    if filename in names or filename in basenames:
        return True, "comfyui"
    dirs = {
        "vae": root_vae(cfg),
        "clip": root_text_encoders(cfg),
    }
    folder = dirs.get(role)
    if folder and file_has_payload(folder / filename):
        return True, "local"
    return False, "missing"


def root_vae(cfg: dict[str, Any]) -> Path:
    return Path((cfg.get("stability_matrix") or {}).get("models", "")) / "VAE"


def root_text_encoders(cfg: dict[str, Any]) -> Path:
    return Path((cfg.get("stability_matrix") or {}).get("models", "")) / "TextEncoders"
