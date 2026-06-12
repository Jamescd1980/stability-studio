from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import requests

from studio.workflow_converter import ui_to_api

# Known third-party node types → git package to install into ComfyUI/custom_nodes.
NODE_PACKAGES: dict[str, dict[str, str]] = {
    "IPAdapterUnifiedLoader": {
        "package": "ComfyUI_IPAdapter_plus",
        "git_url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
        "note": "IP-Adapter Plus for SDXL reference images.",
    },
    "IPAdapterAdvanced": {
        "package": "ComfyUI_IPAdapter_plus",
        "git_url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
    },
    "IPAdapterModelLoader": {
        "package": "ComfyUI_IPAdapter_plus",
        "git_url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
    },
    "CLIPVisionLoader": {
        "package": "ComfyUI_IPAdapter_plus",
        "git_url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
    },
    "DepthAnythingPreprocessor": {
        "package": "comfyui_controlnet_aux",
        "git_url": "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
        "note": "Depth preprocessor for ControlNet depth in inpaint_advanced.",
    },
    "GroundingDinoModelLoader": {
        "package": "comfyui_controlnet_aux",
        "git_url": "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
        "note": "Text-prompt segmentation for edit_image masks.",
    },
    "SAMLoader": {
        "package": "comfyui_controlnet_aux",
        "git_url": "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
    },
    "GroundingDinoSAMSegment": {
        "package": "comfyui_controlnet_aux",
        "git_url": "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
    },
    "TextCombinerTwo": {
        "package": "ComfyUI_Mira",
        "git_url": "https://github.com/mirabarukaso/ComfyUI_Mira.git",
        "note": "Also provides TextBoxMira and other text utilities.",
    },
    "TextBoxMira": {
        "package": "ComfyUI_Mira",
        "git_url": "https://github.com/mirabarukaso/ComfyUI_Mira.git",
    },
    "JWInteger": {
        "package": "comfyui-various",
        "git_url": "https://github.com/jamesWalker55/comfyui-various.git",
    },
    "JWString": {
        "package": "comfyui-various",
        "git_url": "https://github.com/jamesWalker55/comfyui-various.git",
    },
    "PainterI2V": {
        "package": "ComfyUI-PainterI2V",
        "git_url": "https://github.com/princepainter/ComfyUI-PainterI2V.git",
        "note": "Wan 2.2 I2V motion_amplitude node (slow-motion fix). Use workflow_id=i2v_5b_painter or use_painter_i2v=true.",
    },
    "FaceDetailer": {
        "package": "ComfyUI-Impact-Pack",
        "git_url": "https://github.com/ltdrdata/ComfyUI-Impact-Pack.git",
        "note": "ADetailer-style face refinement pass (face_detail=true on generate_image).",
    },
    "UltralyticsDetectorProvider": {
        "package": "ComfyUI-Impact-Subpack",
        "git_url": "https://github.com/ltdrdata/ComfyUI-Impact-Subpack.git",
        "note": "YOLO face detector for FaceDetailer; install alongside Impact Pack.",
    },
}

# Optional quality-of-life bootstrap (ComfyUI Manager UI).
BOOTSTRAP_PACKAGES: dict[str, dict[str, str]] = {
    "ComfyUI-Manager": {
        "git_url": "https://github.com/Comfy-Org/ComfyUI-Manager.git",
        "note": "Enables in-ComfyUI extension search/install UI after restart.",
    },
}


def comfy_custom_nodes_dir(cfg: dict[str, Any]) -> Path:
    sm = cfg.get("stability_matrix", {})
    packages = sm.get("packages", {})
    comfy_root = Path(packages.get("comfyui", ""))
    return comfy_root / "custom_nodes"


def fetch_installed_node_types(comfy_url: str, timeout: int = 15) -> set[str]:
    r = requests.get(f"{comfy_url.rstrip('/')}/object_info", timeout=timeout)
    r.raise_for_status()
    return set(r.json().keys())


def required_node_types_for_workflow(ui_workflow: dict[str, Any]) -> set[str]:
    api = ui_to_api(ui_workflow)
    return {node["class_type"] for node in api.values()}


def packages_for_missing_nodes(missing: set[str]) -> dict[str, dict[str, str]]:
    needed: dict[str, dict[str, str]] = {}
    for node_type in sorted(missing):
        meta = NODE_PACKAGES.get(node_type)
        if not meta:
            continue
        pkg = meta["package"]
        if pkg not in needed:
            needed[pkg] = {
                "git_url": meta["git_url"],
                "node_types": [node_type],
                "note": meta.get("note", ""),
            }
        else:
            needed[pkg]["node_types"].append(node_type)
    return needed


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def install_git_package(custom_nodes_dir: Path, package_name: str, git_url: str) -> dict[str, Any]:
    custom_nodes_dir.mkdir(parents=True, exist_ok=True)
    target = custom_nodes_dir / package_name

    if target.exists():
        if (target / ".git").exists():
            pull = _run_git(["pull", "--ff-only"], cwd=target)
            return {
                "package": package_name,
                "path": str(target),
                "action": "updated" if pull.returncode == 0 else "update_failed",
                "stdout": (pull.stdout or "")[-500:],
                "stderr": (pull.stderr or "")[-500:],
            }
        return {
            "package": package_name,
            "path": str(target),
            "action": "skipped_exists_not_git",
        }

    clone = _run_git(["clone", "--depth", "1", git_url, str(target)])
    if clone.returncode != 0:
        return {
            "package": package_name,
            "path": str(target),
            "action": "clone_failed",
            "stderr": (clone.stderr or "")[-1000:],
        }

    req = target / "requirements.txt"
    pip_result = None
    if req.exists():
        pip = subprocess.run(
            ["pip", "install", "-r", str(req)],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        pip_result = {
            "returncode": pip.returncode,
            "stderr": (pip.stderr or "")[-500:],
        }

    return {
        "package": package_name,
        "path": str(target),
        "action": "installed",
        "pip": pip_result,
    }


def check_workflow_dependencies(
    *,
    cfg: dict[str, Any],
    ui_workflow: dict[str, Any],
    comfy_url: str,
) -> dict[str, Any]:
    required = required_node_types_for_workflow(ui_workflow)
    try:
        installed = fetch_installed_node_types(comfy_url)
        comfy_running = True
    except requests.RequestException as exc:
        return {
            "comfyui_running": False,
            "error": str(exc),
            "required_node_types": sorted(required),
            "note": "Start ComfyUI from Stability Matrix before checking dependencies.",
        }

    missing = sorted(required - installed)
    packages = packages_for_missing_nodes(set(missing))
    unknown = sorted(node for node in missing if node not in NODE_PACKAGES)

    return {
        "comfyui_running": comfy_running,
        "required_node_types": sorted(required),
        "missing_node_types": missing,
        "installable_packages": packages,
        "unknown_missing_node_types": unknown,
        "ready": not missing,
        "restart_required_after_install": bool(packages),
        "note": (
            "Call install_comfyui_dependencies, then restart ComfyUI from Stability Matrix "
            "before generate_video."
        ),
    }


def check_node_types(
    *,
    cfg: dict[str, Any],
    comfy_url: str,
    required: set[str],
) -> dict[str, Any]:
    """Check whether ComfyUI exposes the given node class types."""
    try:
        installed = fetch_installed_node_types(comfy_url)
        comfy_running = True
    except requests.RequestException as exc:
        return {
            "comfyui_running": False,
            "error": str(exc),
            "required_node_types": sorted(required),
            "note": "Start ComfyUI from Stability Matrix before checking dependencies.",
        }

    missing = sorted(required - installed)
    packages = packages_for_missing_nodes(set(missing))
    unknown = sorted(node for node in missing if node not in NODE_PACKAGES)

    return {
        "comfyui_running": comfy_running,
        "required_node_types": sorted(required),
        "missing_node_types": missing,
        "installable_packages": packages,
        "unknown_missing_node_types": unknown,
        "ready": not missing,
        "restart_required_after_install": bool(packages),
    }


def install_node_packages(
    cfg: dict[str, Any],
    packages: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    custom_nodes = comfy_custom_nodes_dir(cfg)
    installs: list[dict[str, Any]] = []
    for package_name, meta in packages.items():
        installs.append(install_git_package(custom_nodes, package_name, meta["git_url"]))
    return installs


def install_workflow_dependencies(
    *,
    cfg: dict[str, Any],
    ui_workflow: dict[str, Any],
    comfy_url: str,
    include_manager: bool = False,
) -> dict[str, Any]:
    report = check_workflow_dependencies(cfg=cfg, ui_workflow=ui_workflow, comfy_url=comfy_url)
    if not report.get("comfyui_running"):
        # Still allow install even if ComfyUI is down.
        required = required_node_types_for_workflow(ui_workflow)
        missing = set(report.get("missing_node_types") or required)
        packages = packages_for_missing_nodes(missing)
    else:
        packages = report.get("installable_packages") or {}

    custom_nodes = comfy_custom_nodes_dir(cfg)
    installs: list[dict[str, Any]] = []

    for package_name, meta in packages.items():
        installs.append(
            install_git_package(custom_nodes, package_name, meta["git_url"])
        )

    if include_manager:
        meta = BOOTSTRAP_PACKAGES["ComfyUI-Manager"]
        installs.append(
            install_git_package(custom_nodes, "ComfyUI-Manager", meta["git_url"])
        )

    return {
        **report,
        "install_results": installs,
        "custom_nodes_dir": str(custom_nodes),
        "next_steps": [
            "Restart ComfyUI from Stability Matrix (required for new nodes to load).",
            "Call check_comfyui_dependencies again to verify.",
            "Then call generate_video.",
        ],
    }
