"""IP-Adapter / ControlNet asset checks, downloads, and bundled reference images."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Any
import requests

from studio.comfy_deps import check_node_types, install_node_packages
from studio.wan_assets import hf_download_url

IP_ADAPTER_REQUIRED_NODES = frozenset(
    {
        "IPAdapterModelLoader",
        "IPAdapterAdvanced",
        "CLIPVisionLoader",
    }
)
IP_ADAPTER_DEPTH_NODES = frozenset({"DepthAnythingPreprocessor"})

HF_BASE = "https://huggingface.co"

# Models for SDXL IP-Adapter Plus + optional depth ControlNet.
IP_ADAPTER_ASSETS: list[dict[str, Any]] = [
    {
        "filename": "ip-adapter-plus_sdxl_vit-h.safetensors",
        "folder": "ipadapter",
        "repo": "h94/IP-Adapter",
        "path": "sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors",
        "size_hint": "~800 MB",
    },
    {
        "filename": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
        "folder": "clip_vision",
        "repo": "h94/IP-Adapter",
        "path": "models/image_encoder/model.safetensors",
        "size_hint": "~2.5 GB",
    },
    {
        "filename": "controlnet-depth-sdxl-1.0.safetensors",
        "folder": "controlnet",
        "repo": "diffusers/controlnet-depth-sdxl-1.0",
        "path": "diffusion_pytorch_model.safetensors",
        "size_hint": "~2.5 GB",
        "optional": True,
        "note": "Depth ControlNet for inpaint_advanced and controlnet_txt2img.",
    },
    {
        "filename": "controlnet-canny-sdxl-1.0.safetensors",
        "folder": "controlnet",
        "repo": "diffusers/controlnet-canny-sdxl-1.0",
        "path": "diffusion_pytorch_model.safetensors",
        "size_hint": "~2.5 GB",
        "optional": True,
        "note": "Canny ControlNet for controlnet_txt2img from a guide image.",
    },
]

CONTROLNET_TXT2IMG_NODES = frozenset(
    {
        "DepthAnythingPreprocessor",
        "ControlNetLoader",
        "ControlNetApplyAdvanced",
        "Canny",
    }
)

# Bundled / downloadable reference images (flags, etc.).
REFERENCE_ASSETS: dict[str, dict[str, str]] = {
    "ireland_flag": {
        "filename": "ireland.png",
        "subdir": "flags",
        "url": "https://flagcdn.com/w640/ie.png",
        "note": "Irish tricolor reference for IP-Adapter flag edits.",
    },
    "gothic_church_interior": {
        "filename": "gothic_church_interior_plate.png",
        "subdir": "references/churches",
        "url": "",
        "note": "Bundled nave plate (pews, vaults, stained glass). Use with generate_image_controlnet guide_image_path.",
    },
}

FOLDER_MAP = {
    "ipadapter": "ipadapter",
    "clip_vision": "clip_vision",
    "controlnet": "controlnet",
}


def comfy_models_dir(cfg: dict[str, Any]) -> Path:
    sm = cfg.get("stability_matrix", {})
    packages = sm.get("packages", {})
    return Path(packages.get("comfyui", "")) / "models"


def model_dirs(cfg: dict[str, Any]) -> dict[str, Path]:
    root = comfy_models_dir(cfg)
    return {key: root / sub for key, sub in FOLDER_MAP.items()}


def assets_root(cfg: dict[str, Any]) -> Path:
    return Path(cfg.get("_root", Path(__file__).resolve().parent.parent)) / "assets"


def _find_file(name: str, folder: Path) -> Path | None:
    if not folder.is_dir():
        return None
    direct = folder / name
    if direct.is_file():
        return direct
    for hit in folder.rglob(name):
        if hit.is_file():
            return hit
    return None


def check_ip_adapter_assets(
    cfg: dict[str, Any],
    *,
    include_optional: bool = False,
) -> dict[str, Any]:
    dirs = model_dirs(cfg)
    installed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for entry in IP_ADAPTER_ASSETS:
        if entry.get("optional") and not include_optional:
            continue
        folder_key = entry["folder"]
        found = _find_file(entry["filename"], dirs[folder_key])
        if found:
            installed.append({**entry, "path": str(found)})
        else:
            item = dict(entry)
            if entry.get("repo") and entry.get("path"):
                item["download_url"] = hf_download_url(entry["repo"], entry["path"])
            missing.append(item)

    refs = check_reference_assets(cfg)
    ready = len(missing) == 0
    return {
        "installed": installed,
        "missing": missing,
        "ready": ready,
        "reference_assets": refs,
        "model_dirs": {k: str(v) for k, v in dirs.items()},
    }


def check_reference_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    root = assets_root(cfg)
    out: dict[str, Any] = {}
    for key, meta in REFERENCE_ASSETS.items():
        path = root / meta["subdir"] / meta["filename"]
        out[key] = {
            **meta,
            "path": str(path),
            "installed": path.is_file(),
        }
    return out


def ensure_reference_asset(cfg: dict[str, Any], key: str = "ireland_flag") -> Path:
    meta = REFERENCE_ASSETS.get(key)
    if not meta:
        raise ValueError(f"Unknown reference asset: {key}")
    dest = assets_root(cfg) / meta["subdir"] / meta["filename"]
    if dest.is_file():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = (meta.get("url") or "").strip()
    if not url:
        raise FileNotFoundError(f"Bundled reference not on disk: {dest}")
    headers = {"User-Agent": "StabilityStudioMCP/1.0 (local image generation setup)"}
    with requests.get(url, stream=True, timeout=120, headers=headers) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    return dest


def default_flag_reference_path(cfg: dict[str, Any]) -> str:
    """Return path to bundled Irish flag, downloading if needed."""
    return str(ensure_reference_asset(cfg, "ireland_flag"))


def download_ip_adapter_assets(
    cfg: dict[str, Any],
    *,
    include_optional: bool = True,
    force: bool = False,
) -> list[dict[str, Any]]:
    status = check_ip_adapter_assets(cfg, include_optional=include_optional)
    results: list[dict[str, Any]] = []
    dirs = model_dirs(cfg)

    for entry in status["missing"]:
        folder = entry["folder"]
        dest_dir = dirs[folder]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / entry["filename"]
        if dest.is_file() and not force:
            results.append({"filename": entry["filename"], "path": str(dest), "ok": True, "skipped": True})
            continue
        try:
            path = _hf_stream_to_file(
                entry["repo"],
                entry["path"],
                dest,
                force=force,
            )
            results.append({"filename": entry["filename"], "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"filename": entry["filename"], "ok": False, "error": str(exc)})

    ref = ensure_reference_asset(cfg, "ireland_flag")
    results.append({"filename": "ireland.png", "path": str(ref), "ok": True, "kind": "reference"})
    return results


def _hf_stream_to_file(repo: str, path: str, dest: Path, *, force: bool = False) -> Path:
    if dest.is_file() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import hf_hub_download

        fetched = Path(hf_hub_download(repo, path, force_download=force))
        if fetched.resolve() != dest.resolve():
            if dest.is_file():
                dest.unlink()
            dest.write_bytes(fetched.read_bytes())
        return dest
    except ImportError:
        pass

    url = hf_download_url(repo, path)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    tmp.replace(dest)
    return dest


def check_ip_adapter_dependencies(
    cfg: dict[str, Any],
    comfy_url: str,
    *,
    include_depth: bool = False,
) -> dict[str, Any]:
    required = set(IP_ADAPTER_REQUIRED_NODES)
    if include_depth:
        required |= IP_ADAPTER_DEPTH_NODES
    return check_node_types(cfg=cfg, comfy_url=comfy_url, required=required)


def check_controlnet_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    """Depth + canny SDXL ControlNet files required for guided txt2img."""
    return check_ip_adapter_assets(cfg, include_optional=True)


def download_controlnet_assets(
    cfg: dict[str, Any],
    *,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Download depth and canny SDXL ControlNet weights."""
    names = {
        "controlnet-depth-sdxl-1.0.safetensors",
        "controlnet-canny-sdxl-1.0.safetensors",
    }
    dirs = model_dirs(cfg)
    results: list[dict[str, Any]] = []
    for entry in IP_ADAPTER_ASSETS:
        if entry["filename"] not in names:
            continue
        dest_dir = dirs[entry["folder"]]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / entry["filename"]
        if dest.is_file() and not force:
            results.append({"filename": entry["filename"], "path": str(dest), "ok": True, "skipped": True})
            continue
        try:
            path = _hf_stream_to_file(entry["repo"], entry["path"], dest, force=force)
            results.append({"filename": entry["filename"], "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"filename": entry["filename"], "ok": False, "error": str(exc)})
    return results


def check_controlnet_dependencies(cfg: dict[str, Any], comfy_url: str) -> dict[str, Any]:
    return check_node_types(
        cfg=cfg,
        comfy_url=comfy_url,
        required=set(CONTROLNET_TXT2IMG_NODES),
    )


def install_controlnet_dependencies(cfg: dict[str, Any], comfy_url: str) -> dict[str, Any]:
    report = check_controlnet_dependencies(cfg, comfy_url)
    installs = install_node_packages(cfg, report.get("installable_packages") or {})
    return {
        **report,
        "install_results": installs,
        "next_steps": [
            "Restart ComfyUI from Stability Matrix (required for DepthAnythingPreprocessor).",
            "Call check_controlnet_dependencies again to verify.",
            "Call download_controlnet_assets if models are still missing.",
            "Then use generate_image_controlnet with guide_image_path.",
        ],
    }


def install_ip_adapter_dependencies(
    cfg: dict[str, Any],
    comfy_url: str,
    *,
    include_depth: bool = True,
) -> dict[str, Any]:
    required = set(IP_ADAPTER_REQUIRED_NODES)
    if include_depth:
        required |= IP_ADAPTER_DEPTH_NODES
    report = check_node_types(cfg=cfg, comfy_url=comfy_url, required=required)
    installs = install_node_packages(cfg, report.get("installable_packages") or {})
    return {
        **report,
        "install_results": installs,
        "next_steps": [
            "Restart ComfyUI from Stability Matrix (required for new nodes to load).",
            "Call check_ip_adapter_dependencies again to verify.",
            "Call download_ip_adapter_assets if models are still missing.",
            "Then use inpaint_advanced with reference_image_path or flag_reference='ireland'.",
        ],
    }


def image_dimensions(path: Path) -> tuple[int, int]:
    """Read width/height from PNG or JPEG without Pillow."""
    data = path.read_bytes()[:32]
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return int(w), int(h)
    if data.startswith(b"\xff\xd8"):
        # Minimal JPEG SOF scan
        with path.open("rb") as f:
            f.read(2)
            while True:
                marker = f.read(2)
                if len(marker) < 2:
                    break
                if marker[0] != 0xFF:
                    break
                if marker[1] in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                    f.read(3)
                    h, w = struct.unpack(">HH", f.read(4))
                    return int(w), int(h)
                length = struct.unpack(">H", f.read(2))[0]
                f.read(length - 2)
    raise ValueError(f"Could not read image dimensions: {path}")


def write_region_mask_png(
    path: Path,
    width: int,
    height: int,
    region: str = "top",
) -> Path:
    """Write grayscale PNG mask (white=inpaint region) without Pillow."""
    path.parent.mkdir(parents=True, exist_ok=True)

    def row_bytes(y: int) -> bytes:
        row = bytearray([0])
        for x in range(width):
            if region == "full":
                val = 255
            elif region in ("top", "upper_half"):
                val = 255 if y < height // 2 else 0
            elif region == "top_third":
                val = 255 if y < height // 3 else 0
            elif region == "top_two_thirds":
                val = 255 if y < (height * 2) // 3 else 0
            elif region in ("sky", "church"):
                val = 255 if y < int(height * 0.22) else 0
            elif region == "church_tower":
                # Steeple / sky strip + upper corners; protect center column (knight)
                top_strip = y < int(height * 0.16)
                upper = y < int(height * 0.34)
                center_col = int(width * 0.30) <= x <= int(width * 0.70)
                knight_zone = center_col and y < int(height * 0.55)
                if top_strip:
                    val = 255
                elif upper and not knight_zone:
                    val = 255
                else:
                    val = 0
            elif region == "right_building":
                # Small patch on right ruin wall — flag mount, not steeple/cross/knight
                knight = int(width * 0.20) <= x <= int(width * 0.68) and y >= int(height * 0.15)
                steeple = int(width * 0.36) <= x <= int(width * 0.64) and y < int(height * 0.24)
                right_patch = (
                    int(width * 0.54) <= x <= int(width * 0.86)
                    and int(height * 0.18) <= y <= int(height * 0.42)
                )
                val = 255 if right_patch and not knight and not steeple else 0
            else:
                val = 255 if y < height // 2 else 0
            row.append(val)
        return bytes(row)

    raw = b"".join(row_bytes(y) for y in range(height))
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    path.write_bytes(png)
    return path
