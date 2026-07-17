"""Forge (A1111/SD-WebUI) stills backend — generation host :7860 + GPU switch via SSH."""

from __future__ import annotations

import base64
import json
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


def _forge_config(cfg: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "enabled": True,
        "url": "",
        "port": 7860,
        "timeout_seconds": 5,
        "generate_timeout_seconds": 900,
        # Set forge.ssh_host in config.yaml (never commit real hostnames).
        "ssh_host": "",
        "gpu_backend_script": "~/bin/gpu_backend.sh",
        "switch_wait_seconds": 180,
        "doc": "COMFYBOX-FORGE.md",
    }
    merged = dict(defaults)
    merged.update(cfg.get("forge") or {})
    return merged


def forge_url(cfg: dict[str, Any]) -> str:
    """Resolve Forge API base URL (empty string if disabled / unset)."""
    g = _forge_config(cfg)
    if not g.get("enabled", True):
        return ""
    explicit = str(g.get("url") or "").rstrip("/")
    if explicit:
        return explicit
    comfy = str((cfg.get("comfyui") or {}).get("url") or "http://127.0.0.1:8188")
    parsed = urlparse(comfy)
    host = parsed.hostname or "127.0.0.1"
    # Local Windows :7860 is usually Wan2GP Gradio — do not assume Forge
    if host in {"127.0.0.1", "localhost"}:
        return ""
    port = int(g.get("port") or 7860)
    scheme = parsed.scheme or "http"
    return f"{scheme}://{host}:{port}"


def forge_is_reachable(cfg: dict[str, Any], *, timeout: float | None = None) -> bool:
    """True when Forge answers the A1111 API (not Wan2GP Gradio)."""
    url = forge_url(cfg)
    if not url:
        return False
    g = _forge_config(cfg)
    t = float(timeout if timeout is not None else g.get("timeout_seconds") or 5)
    try:
        r = requests.get(f"{url}/sdapi/v1/sd-models", timeout=t)
        return r.status_code == 200 and isinstance(r.json(), list)
    except (requests.RequestException, ValueError):
        return False


def inspect_forge_backend(cfg: dict[str, Any]) -> dict[str, Any]:
    """Status blob for get_generation_context / check_forge_backend."""
    g = _forge_config(cfg)
    url = forge_url(cfg)
    running = forge_is_reachable(cfg) if url else False
    return {
        "enabled": bool(g.get("enabled", True)),
        "url": url or None,
        "port": int(g.get("port") or 7860),
        "running": running,
        "mcp_drives_forge": True,
        "tools": [
            "switch_stills_backend",
            "check_forge_backend",
            "generate_image_forge",
            "refine_image_forge",
        ],
        "purpose": "ADetailer / hires stills on the generation host. Exclusive with ComfyUI.",
        "exclusive_with": "comfyui",
        "switch": "switch_stills_backend(backend='forge'|'comfy'|'status')",
        "ssh_host": g.get("ssh_host") or "",
        "doc": g.get("doc") or "COMFYBOX-FORGE.md",
        "offline_agent_note": (
            "Workflow: Comfy generate_image -> switch_stills_backend(forge) -> "
            "refine_image_forge -> switch_stills_backend(comfy) -> generate_video."
        ),
        "video_note": (
            "Default clip: workflow_id=i2v_5b (Wan 2.2 5B). "
            "Wan 14B (i2v / i2v_gpu) is optional on 20GB — slow/OOM-prone; prefer 5B."
        ),
    }


def _ssh_run(cfg: dict[str, Any], remote_cmd: str, *, timeout: float = 120) -> dict[str, Any]:
    g = _forge_config(cfg)
    host = str(g.get("ssh_host") or "").strip()
    if not host:
        return {
            "ok": False,
            "error": "forge.ssh_host is unset — set it in local config.yaml (never commit hostnames)",
            "cmd": None,
        }
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, remote_cmd]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-2000:],
        "cmd": cmd,
    }


def switch_stills_backend(
    cfg: dict[str, Any],
    backend: str,
    *,
    wait: bool = True,
) -> dict[str, Any]:
    """
    Exclusive GPU switch on the generation host: comfy | forge | status | stop-all.

    Uses SSH + ~/bin/gpu_backend.sh (same script as manual ops).
    """
    from studio.gpu_backend import comfyui_is_reachable

    backend = (backend or "").strip().lower()
    if backend not in {"comfy", "forge", "status", "stop-all"}:
        return {
            "ok": False,
            "error": "backend must be comfy, forge, status, or stop-all",
        }

    g = _forge_config(cfg)
    script = str(g.get("gpu_backend_script") or "~/bin/gpu_backend.sh")
    remote = f"bash {script} {backend}"
    result = _ssh_run(cfg, remote, timeout=90)
    out: dict[str, Any] = {
        "ok": result.get("ok"),
        "requested": backend,
        "ssh": result,
        "forge": inspect_forge_backend(cfg),
        "comfyui_running": comfyui_is_reachable(cfg),
    }

    if backend == "status" or not wait or not result.get("ok"):
        return out

    wait_s = float(g.get("switch_wait_seconds") or 180)
    t0 = time.time()
    if backend == "forge":
        while time.time() - t0 < wait_s:
            if forge_is_reachable(cfg, timeout=3):
                out["ready"] = True
                out["waited_s"] = round(time.time() - t0, 1)
                out["forge"] = inspect_forge_backend(cfg)
                out["comfyui_running"] = comfyui_is_reachable(cfg)
                return out
            time.sleep(3)
        out["ready"] = False
        out["error"] = f"Forge did not become ready within {wait_s}s"
        return out

    if backend == "comfy":
        while time.time() - t0 < wait_s:
            if comfyui_is_reachable(cfg, timeout=3):
                out["ready"] = True
                out["waited_s"] = round(time.time() - t0, 1)
                out["forge"] = inspect_forge_backend(cfg)
                out["comfyui_running"] = True
                return out
            time.sleep(3)
        out["ready"] = False
        out["error"] = f"ComfyUI did not become ready within {wait_s}s"
        return out

    return out


def _b64_image_file(path: Path) -> str:
    raw = path.read_bytes()
    return base64.b64encode(raw).decode("ascii")


def _save_forge_images(
    cfg: dict[str, Any],
    images_b64: list[str],
    *,
    prefix: str,
) -> list[str]:
    root = Path(cfg.get("_package_root") or ".") / "outputs"
    root.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    stamp = int(time.time())
    for i, b64 in enumerate(images_b64):
        payload = b64
        if "," in payload[:64]:
            payload = payload.split(",", 1)[1]
        dest = root / f"{prefix}_{stamp}_{i:02d}.png"
        dest.write_bytes(base64.b64decode(payload))
        saved.append(str(dest))
    return saved


def _adetailer_payload(
    *,
    enabled: bool,
    ad_prompt: str = "",
    ad_negative: str = "",
    denoise: float = 0.4,
) -> dict[str, Any]:
    if not enabled:
        return {}
    return {
        "adetailer": {
            "args": [
                True,
                False,
                {
                    "ad_model": "face_yolov8n.pt",
                    "ad_tab_enable": True,
                    "ad_prompt": ad_prompt or "",
                    "ad_negative_prompt": ad_negative
                    or "blurry face, deformed face, bad anatomy",
                    "ad_confidence": 0.25,
                    "ad_dilate_erode": 4,
                    "ad_mask_blur": 4,
                    "ad_denoising_strength": denoise,
                    "ad_inpaint_only_masked": True,
                    "ad_inpaint_only_masked_padding": 32,
                },
            ]
        }
    }


def _set_checkpoint(cfg: dict[str, Any], checkpoint: str) -> None:
    url = forge_url(cfg)
    if not url or not checkpoint:
        return
    g = _forge_config(cfg)
    timeout = float(g.get("generate_timeout_seconds") or 900)
    requests.post(
        f"{url}/sdapi/v1/options",
        json={"sd_model_checkpoint": checkpoint},
        timeout=min(180, timeout),
    )
    time.sleep(2)


def generate_image_forge(
    cfg: dict[str, Any],
    *,
    prompt: str,
    negative_prompt: str = "",
    checkpoint: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 30,
    cfg_scale: float = 6.0,
    seed: int = -1,
    sampler_name: str = "Euler a",
    adetailer: bool = True,
    ad_prompt: str = "",
) -> dict[str, Any]:
    """txt2img via Forge A1111 API. Requires Forge running (switch_stills_backend forge)."""
    from studio.gpu_backend import comfyui_is_reachable

    url = forge_url(cfg)
    if not url:
        return {"ok": False, "error": "forge.url not configured (remote ComfyUI host required)"}
    if not forge_is_reachable(cfg):
        return {
            "ok": False,
            "error": "Forge is not reachable. Call switch_stills_backend(backend='forge') first.",
            "forge": inspect_forge_backend(cfg),
        }
    if comfyui_is_reachable(cfg):
        return {
            "ok": False,
            "error": (
                "ComfyUI is still running — exclusive GPU. "
                "Call switch_stills_backend(backend='forge') first."
            ),
        }

    g = _forge_config(cfg)
    timeout = float(g.get("generate_timeout_seconds") or 900)
    if checkpoint:
        _set_checkpoint(cfg, checkpoint)

    payload: dict[str, Any] = {
        "prompt": prompt,
        "negative_prompt": negative_prompt
        or "lowres, bad anatomy, bad hands, text, watermark, blurry",
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "sampler_name": sampler_name,
        "seed": seed,
        "batch_size": 1,
    }
    always = _adetailer_payload(enabled=adetailer, ad_prompt=ad_prompt)
    if always:
        payload["alwayson_scripts"] = always

    r = requests.post(f"{url}/sdapi/v1/txt2img", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    images = data.get("images") or []
    saved = _save_forge_images(cfg, images, prefix="forge_txt2img")
    return {
        "ok": True,
        "backend": "forge",
        "checkpoint": checkpoint or None,
        "adetailer": adetailer,
        "saved_files": saved,
        "info": data.get("info"),
    }


def refine_image_forge(
    cfg: dict[str, Any],
    *,
    image_path: str,
    prompt: str,
    negative_prompt: str = "",
    checkpoint: str = "",
    denoising_strength: float = 0.35,
    steps: int = 28,
    cfg_scale: float = 5.5,
    seed: int = -1,
    sampler_name: str = "Euler a",
    adetailer: bool = True,
    ad_prompt: str = "",
    resize_mode: int = 0,
) -> dict[str, Any]:
    """img2img refine via Forge (ADetailer optional). Requires Forge running."""
    from studio.gpu_backend import comfyui_is_reachable

    url = forge_url(cfg)
    if not url:
        return {"ok": False, "error": "forge.url not configured"}
    if not forge_is_reachable(cfg):
        return {
            "ok": False,
            "error": "Forge is not reachable. Call switch_stills_backend(backend='forge') first.",
            "forge": inspect_forge_backend(cfg),
        }
    if comfyui_is_reachable(cfg):
        return {
            "ok": False,
            "error": (
                "ComfyUI is still running — exclusive GPU. "
                "Call switch_stills_backend(backend='forge') first."
            ),
        }

    src = Path(image_path)
    if not src.is_file():
        return {"ok": False, "error": f"image not found: {image_path}"}

    g = _forge_config(cfg)
    timeout = float(g.get("generate_timeout_seconds") or 900)
    if checkpoint:
        _set_checkpoint(cfg, checkpoint)

    from PIL import Image

    with Image.open(src) as im:
        w, h = im.size

    payload: dict[str, Any] = {
        "init_images": [_b64_image_file(src)],
        "prompt": prompt,
        "negative_prompt": negative_prompt
        or "lowres, bad anatomy, bad hands, text, watermark, blurry",
        "denoising_strength": denoising_strength,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": w,
        "height": h,
        "sampler_name": sampler_name,
        "seed": seed,
        "resize_mode": resize_mode,
        "batch_size": 1,
    }
    always = _adetailer_payload(enabled=adetailer, ad_prompt=ad_prompt)
    if always:
        payload["alwayson_scripts"] = always

    r = requests.post(f"{url}/sdapi/v1/img2img", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    images = data.get("images") or []
    saved = _save_forge_images(cfg, images, prefix="forge_refine")
    return {
        "ok": True,
        "backend": "forge",
        "source": str(src),
        "checkpoint": checkpoint or None,
        "denoising_strength": denoising_strength,
        "adetailer": adetailer,
        "saved_files": saved,
        "info": data.get("info"),
    }
