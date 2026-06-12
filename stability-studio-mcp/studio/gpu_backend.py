"""Exclusive GPU backend policy — ComfyUI vs Wan2GP on ≤16 GB (and offline agents)."""

from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Literal

BackendName = Literal["comfyui", "wan2gp", "idle"]

_LOCK_NAME = ".gpu_backend.lock"


class GpuBackendConflict(RuntimeError):
    """Raised when the requested backend conflicts with an active GPU consumer."""

    def __init__(self, info: dict[str, Any]) -> None:
        self.info = info
        super().__init__(json.dumps(info, indent=2))


def _gpu_config(cfg: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "enforce_exclusive": True,
        "comfyui_port": 8188,
        "wan2gp_ui_port": 7860,
        "wan2gp_mcp_port": 7867,
        "lock_dir": "",
        "min_free_vram_gb_comfyui": 4.0,
        "min_free_vram_gb_wan2gp": 10.0,
        "block_comfyui_when_wan2gp_ui": True,
        "require_comfyui_stopped_for_hero": True,
    }
    merged = dict(defaults)
    merged.update(cfg.get("gpu_backend") or {})
    return merged


def lock_path(cfg: dict[str, Any]) -> Path:
    g = _gpu_config(cfg)
    base = Path(g["lock_dir"]) if g.get("lock_dir") else Path(cfg.get("_package_root", ".")) / "outputs"
    base.mkdir(parents=True, exist_ok=True)
    return base / _LOCK_NAME


def _read_lock(cfg: dict[str, Any]) -> dict[str, Any] | None:
    path = lock_path(cfg)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _write_lock(cfg: dict[str, Any], holder: BackendName, detail: str = "") -> None:
    path = lock_path(cfg)
    payload = {
        "holder": holder,
        "detail": detail,
        "since": time.time(),
        "pid": None,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def release_gpu_lock(cfg: dict[str, Any], holder: BackendName | None = None) -> dict[str, Any]:
    """Clear MCP GPU lock (optionally only if holder matches)."""
    path = lock_path(cfg)
    current = _read_lock(cfg)
    if not current:
        return {"released": False, "reason": "no lock"}
    if holder and current.get("holder") != holder:
        return {"released": False, "reason": f"lock held by {current.get('holder')}"}
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return {"released": False, "error": str(exc)}
    return {"released": True, "previous": current}


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pid_on_port_windows(port: int) -> int | None:
    try:
        out = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        needle = f":{port}"
        for line in out.stdout.splitlines():
            if "LISTENING" not in line or needle not in line:
                continue
            parts = line.split()
            if parts:
                try:
                    return int(parts[-1])
                except ValueError:
                    continue
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _process_exe_windows(pid: int) -> str | None:
    try:
        out = subprocess.run(
            ["wmic", "process", "where", f"processid={pid}", "get", "ExecutablePath"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip() and "ExecutablePath" not in ln]
        return lines[0] if lines else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _vram_free_gb() -> float | None:
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        mib = float(out.stdout.strip().splitlines()[0].strip())
        return round(mib / 1024, 2)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def inspect_gpu_backend(cfg: dict[str, Any], *, comfyui_running: bool | None = None) -> dict[str, Any]:
    """Snapshot ComfyUI / Wan2GP / lock / VRAM for agents (Jan, LM Studio, Cursor)."""
    g = _gpu_config(cfg)
    comfy_port = int(g["comfyui_port"])
    ui_port = int(g["wan2gp_ui_port"])
    mcp_port = int(g["wan2gp_mcp_port"])

    if comfyui_running is None:
        comfyui_running = _port_open("127.0.0.1", comfy_port)

    wan2gp_ui = _port_open("127.0.0.1", ui_port)
    wan2gp_mcp = _port_open("127.0.0.1", mcp_port)
    ui_pid = _pid_on_port_windows(ui_port) if wan2gp_ui else None
    ui_python = _process_exe_windows(ui_pid) if ui_pid else None

    lock = _read_lock(cfg)
    vram_free = _vram_free_gb()
    tier = (cfg.get("_generation_tier") or "")  # optional injection

    allowed: list[str] = []
    blocks: list[dict[str, str]] = []

    if g["enforce_exclusive"]:
        if lock and lock.get("holder") == "wan2gp":
            blocks.append(
                {
                    "backend": "comfyui",
                    "reason": "Wan2GP hero job active (MCP lock). Wait or call release_gpu_lock.",
                }
            )
        if lock and lock.get("holder") == "comfyui":
            blocks.append(
                {
                    "backend": "wan2gp",
                    "reason": "ComfyUI MCP job lock active. Wait for completion.",
                }
            )
        if wan2gp_ui and g["block_comfyui_when_wan2gp_ui"]:
            blocks.append(
                {
                    "backend": "comfyui",
                    "reason": "Wan2GP Gradio UI is running — stop it before ComfyUI GPU generation on 16 GB.",
                }
            )
        if comfyui_running and g["require_comfyui_stopped_for_hero"]:
            blocks.append(
                {
                    "backend": "wan2gp",
                    "reason": "ComfyUI is running — stop ComfyUI from Stability Matrix before hero Wan2GP.",
                }
            )

    if not any(b["backend"] == "comfyui" for b in blocks):
        allowed.append("comfyui")
    if not any(b["backend"] == "wan2gp" for b in blocks):
        allowed.append("wan2gp")

    if vram_free is not None and vram_free < float(g["min_free_vram_gb_comfyui"]):
        if "comfyui" in allowed:
            allowed.remove("comfyui")
            blocks.append(
                {
                    "backend": "comfyui",
                    "reason": f"Low free VRAM ({vram_free} GB). Stop other GPU jobs first.",
                }
            )
    if vram_free is not None and vram_free < float(g["min_free_vram_gb_wan2gp"]):
        if "wan2gp" in allowed:
            allowed.remove("wan2gp")
            blocks.append(
                {
                    "backend": "wan2gp",
                    "reason": f"Need ≥{g['min_free_vram_gb_wan2gp']} GB free for hero Wan2GP (have {vram_free} GB).",
                }
            )

    recommendation = "One GPU backend at a time on 16 GB."
    if "wan2gp" in allowed and not wan2gp_mcp and not wan2gp_ui:
        recommendation = "Start Wan2GP MCP via generate_video_hero (auto) or Stability Matrix → Wan2GP → MCP mode."
    elif blocks:
        recommendation = blocks[0]["reason"]

    return {
        "enforce_exclusive": bool(g["enforce_exclusive"]),
        "comfyui": {"running": comfyui_running, "port": comfy_port},
        "wan2gp": {
            "ui_running": wan2gp_ui,
            "ui_port": ui_port,
            "ui_pid": ui_pid,
            "ui_python": ui_python,
            "mcp_running": wan2gp_mcp,
            "mcp_port": mcp_port,
        },
        "lock": lock,
        "vram_free_gb": vram_free,
        "allowed_backends": allowed,
        "blocks": blocks,
        "recommendation": recommendation,
        "offline_agent_note": (
            "Call check_gpu_backend before generate_video / generate_video_hero / generate_audio. "
            "Jan and LM Studio must not run ComfyUI and Wan2GP video concurrently."
        ),
    }


def assert_backend_available(
    cfg: dict[str, Any],
    backend: BackendName,
    *,
    comfyui_running: bool | None = None,
    operation: str = "",
) -> dict[str, Any]:
    """Raise GpuBackendConflict if backend is blocked by policy."""
    status = inspect_gpu_backend(cfg, comfyui_running=comfyui_running)
    if backend not in status["allowed_backends"]:
        info = {
            "error_code": "gpu_backend_conflict",
            "requested_backend": backend,
            "operation": operation,
            "summary": status["recommendation"],
            "status": status,
            "hint_restart_comfyui": backend == "comfyui",
            "hint_stop_wan2gp_ui": status["wan2gp"].get("ui_running"),
        }
        raise GpuBackendConflict(info)
    return status


def acquire_gpu_lock(cfg: dict[str, Any], holder: BackendName, detail: str = "") -> None:
    current = _read_lock(cfg)
    if current and current.get("holder") not in {None, holder}:
        raise GpuBackendConflict(
            {
                "error_code": "gpu_backend_lock_held",
                "summary": f"GPU lock held by {current.get('holder')}",
                "lock": current,
            }
        )
    _write_lock(cfg, holder, detail)


def gpu_backend_policy_for_context(cfg: dict[str, Any]) -> dict[str, Any]:
    g = _gpu_config(cfg)
    return {
        "enforce_exclusive": g["enforce_exclusive"],
        "require_comfyui_stopped_for_hero": g["require_comfyui_stopped_for_hero"],
        "block_comfyui_when_wan2gp_ui": g["block_comfyui_when_wan2gp_ui"],
        "min_free_vram_gb_comfyui": g["min_free_vram_gb_comfyui"],
        "min_free_vram_gb_wan2gp": g["min_free_vram_gb_wan2gp"],
        "tools": ["check_gpu_backend", "release_gpu_lock", "check_wan2gp_runtime", "generate_video_hero"],
        "doc": "RESTART-GUIDE.md",
    }
