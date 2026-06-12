"""FaceDetailer (ADetailer-style) assets and ComfyUI Impact Pack / Subpack setup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from studio.comfy_deps import (
    check_node_types,
    comfy_custom_nodes_dir,
    install_git_package,
    install_node_packages,
)
from studio.ip_adapter_assets import comfy_models_dir

FACE_DETAIL_REQUIRED_NODES = frozenset(
    {
        "FaceDetailer",
        "SAMLoader",
        "UltralyticsDetectorProvider",
    }
)

IMPACT_PACK = {
    "package": "ComfyUI-Impact-Pack",
    "git_url": "https://github.com/ltdrdata/ComfyUI-Impact-Pack.git",
    "node_types": ["FaceDetailer", "SAMLoader"],
}

IMPACT_SUBPACK = {
    "package": "ComfyUI-Impact-Subpack",
    "git_url": "https://github.com/ltdrdata/ComfyUI-Impact-Subpack.git",
    "node_types": ["UltralyticsDetectorProvider"],
}

FACE_DETAIL_ASSETS: list[dict[str, Any]] = [
    {
        "filename": "face_yolov8m.pt",
        "folder": "ultralytics_bbox",
        "subdir": "ultralytics/bbox",
        "url": "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt",
        "size_hint": "~50 MB",
        "detector_name": "bbox/face_yolov8m.pt",
    },
    {
        "filename": "sam_vit_b_01ec64.pth",
        "folder": "sams",
        "subdir": "sams",
        "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
        "size_hint": "~375 MB",
    },
]


def face_detail_model_dirs(cfg: dict[str, Any]) -> dict[str, Path]:
    root = comfy_models_dir(cfg)
    return {
        "ultralytics_bbox": root / "ultralytics" / "bbox",
        "sams": root / "sams",
    }


def _find_asset(name: str, folder: Path) -> Path | None:
    if not folder.is_dir():
        return None
    direct = folder / name
    if direct.is_file():
        return direct
    for hit in folder.rglob(name):
        if hit.is_file():
            return hit
    return None


def check_face_detail_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    dirs = face_detail_model_dirs(cfg)
    installed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for entry in FACE_DETAIL_ASSETS:
        folder_key = entry["folder"]
        found = _find_asset(entry["filename"], dirs[folder_key])
        if found:
            installed.append({**entry, "path": str(found)})
        else:
            missing.append(dict(entry))

    return {
        "installed": installed,
        "missing": missing,
        "ready": not missing,
        "model_dirs": {k: str(v) for k, v in dirs.items()},
    }


def _download_url(url: str, dest: Path, *, force: bool = False) -> Path:
    if dest.is_file() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    headers = {"User-Agent": "StabilityStudioMCP/1.0 (face detail setup)"}
    with requests.get(url, stream=True, timeout=300, headers=headers) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    tmp.replace(dest)
    return dest


def download_face_detail_assets(cfg: dict[str, Any], *, force: bool = False) -> list[dict[str, Any]]:
    status = check_face_detail_assets(cfg)
    dirs = face_detail_model_dirs(cfg)
    results: list[dict[str, Any]] = []

    for entry in status["missing"]:
        dest = dirs[entry["folder"]] / entry["filename"]
        if dest.is_file() and not force:
            results.append({"filename": entry["filename"], "path": str(dest), "ok": True, "skipped": True})
            continue
        try:
            if url := entry.get("url"):
                path = _download_url(url, dest, force=force)
            else:
                raise ValueError("No download URL configured")
            results.append({"filename": entry["filename"], "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"filename": entry["filename"], "ok": False, "error": str(exc)})

    return results


def _packages_for_face_detail(missing: set[str]) -> dict[str, dict[str, str]]:
    needed: dict[str, dict[str, str]] = {}
    for meta in (IMPACT_PACK, IMPACT_SUBPACK):
        hits = [n for n in meta["node_types"] if n in missing]
        if not hits:
            continue
        pkg = meta["package"]
        needed[pkg] = {
            "git_url": meta["git_url"],
            "node_types": hits,
            "note": "Impact Pack FaceDetailer + Subpack UltralyticsDetectorProvider.",
        }
    return needed


def _install_missing_packages_from_disk(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Clone Impact Pack / Subpack when custom_nodes folders are absent (ComfyUI may be down)."""
    custom_nodes = comfy_custom_nodes_dir(cfg)
    installs: list[dict[str, Any]] = []
    for meta in (IMPACT_PACK, IMPACT_SUBPACK):
        target = custom_nodes / meta["package"]
        if not target.exists():
            installs.append(
                install_git_package(custom_nodes, meta["package"], meta["git_url"])
            )
    return installs


def check_face_detail_dependencies(cfg: dict[str, Any], comfy_url: str) -> dict[str, Any]:
    report = check_node_types(
        cfg=cfg,
        comfy_url=comfy_url,
        required=set(FACE_DETAIL_REQUIRED_NODES),
    )
    missing = set(report.get("missing_node_types") or [])
    packages = _packages_for_face_detail(missing)
    assets = check_face_detail_assets(cfg)
    ready = report.get("ready", False) and assets["ready"]
    return {
        **report,
        "installable_packages": packages,
        "assets": assets,
        "ready": ready,
        "restart_required_after_install": bool(packages),
        "note": (
            "Install nodes (Impact Pack + Impact Subpack), restart ComfyUI, then "
            "download_face_detail_assets. Use face_detail=true on generate_image / generate_image_i2i."
        ),
    }


def install_face_detail_dependencies(cfg: dict[str, Any], comfy_url: str) -> dict[str, Any]:
    report = check_face_detail_dependencies(cfg, comfy_url)
    installs = _install_missing_packages_from_disk(cfg)
    if report.get("comfyui_running") and report.get("installable_packages"):
        done = {item["package"] for item in installs}
        remaining = {
            k: v for k, v in report["installable_packages"].items() if k not in done
        }
        if remaining:
            installs.extend(install_node_packages(cfg, remaining))
    return {
        **report,
        "install_results": installs,
        "next_steps": [
            "Restart ComfyUI from Stability Matrix if install_results is non-empty.",
            "Call download_face_detail_assets() for face_yolov8m.pt and sam_vit_b_01ec64.pth.",
            "Re-run check_face_detail_dependencies, then generate_image(..., face_detail=true).",
        ],
    }


def setup_face_detail(cfg: dict[str, Any], comfy_url: str, *, force: bool = False) -> dict[str, Any]:
    install = install_face_detail_dependencies(cfg, comfy_url)
    downloads = download_face_detail_assets(cfg, force=force)
    after = check_face_detail_dependencies(cfg, comfy_url)
    return {
        "install": install,
        "downloads": downloads,
        "readiness_after": after,
        "restart_comfyui_required": bool(install.get("install_results")),
    }


def ensure_face_detail_ready(cfg: dict[str, Any], comfy_url: str) -> None:
    report = check_face_detail_dependencies(cfg, comfy_url)
    if report.get("ready"):
        return
    missing_nodes = report.get("missing_node_types") or []
    missing_assets = (report.get("assets") or {}).get("missing") or []
    parts: list[str] = []
    if missing_nodes:
        parts.append(f"missing nodes: {', '.join(missing_nodes)} — call install_face_detail_dependencies()")
    if missing_assets:
        names = ", ".join(a["filename"] for a in missing_assets)
        parts.append(f"missing models: {names} — call download_face_detail_assets()")
    if not report.get("comfyui_running"):
        parts.append("ComfyUI is not running — start it from Stability Matrix")
    raise RuntimeError(
        "Face detail (FaceDetailer) is not ready. " + "; ".join(parts) + "."
    )
