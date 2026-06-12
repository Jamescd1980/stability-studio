"""Run hero-quality video via Wan2GP (MCP HTTP or subprocess API)."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from studio.gpu_backend import acquire_gpu_lock, inspect_gpu_backend, release_gpu_lock
from studio.output_paths import deliver_files, delivery_dir
from studio.wan2gp_assets import check_wan2gp_assets, wan2gp_root
from studio.wan2gp_mcp_client import wangp_generate, wangp_get_job
from studio.wan2gp_settings import build_hero_i2v_settings

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_RUNNER = _SCRIPTS / "run_wan2gp_hero.py"


def _wan2gp_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    w = dict(cfg.get("wan2gp") or {})
    w.setdefault("mcp_port", 7867)
    w.setdefault("mcp_host", "127.0.0.1")
    w.setdefault("auto_start_mcp", True)
    w.setdefault("mcp_wait_seconds", 120)
    return w


def mcp_url(cfg: dict[str, Any]) -> str:
    w = _wan2gp_cfg(cfg)
    explicit = (w.get("mcp_url") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    host = w.get("mcp_host", "127.0.0.1")
    port = int(w.get("mcp_port", 7867))
    return f"http://{host}:{port}/mcp"


def resolve_wan2gp_python(cfg: dict[str, Any], status: dict[str, Any] | None = None) -> Path | None:
    w = _wan2gp_cfg(cfg)
    explicit = (w.get("python") or "").strip()
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    root = wan2gp_root(cfg)
    venv_py = root / "venv" / "Scripts" / "python.exe"
    if venv_py.is_file():
        return venv_py
    if status:
        ui_py = status.get("wan2gp", {}).get("ui_python")
        if ui_py and Path(ui_py).is_file():
            return Path(ui_py)
    return None


def check_wan2gp_runtime(cfg: dict[str, Any], *, comfyui_running: bool | None = None) -> dict[str, Any]:
    assets = check_wan2gp_assets(cfg)
    gpu = inspect_gpu_backend(cfg, comfyui_running=comfyui_running)
    w = _wan2gp_cfg(cfg)
    url = mcp_url(cfg)
    return {
        "assets": assets,
        "gpu_backend": gpu,
        "mcp_url": url,
        "mcp_reachable": gpu["wan2gp"].get("mcp_running"),
        "python": str(resolve_wan2gp_python(cfg, gpu) or ""),
        "auto_start_mcp": bool(w.get("auto_start_mcp")),
        "launch_env": {
            "SETUPTOOLS_USE_DISTUTILS": "stdlib",
            "FASTMCP_PORT": str(int(w.get("mcp_port", 7867))),
            "transport": "streamable-http",
        },
        "ready_for_hero": "wan2gp" in gpu.get("allowed_backends", []) and assets["summary"].get("lightning_v2_i2v"),
    }


def _find_git_exe() -> Path | None:
    import os
    import shutil

    for name in ("git.exe", "git"):
        found = shutil.which(name)
        if found:
            return Path(found)
    for candidate in (
        Path(os.environ.get("ProgramFiles", "")) / "Git" / "cmd" / "git.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Git" / "cmd" / "git.exe",
    ):
        if candidate.is_file():
            return candidate
    return None


def _wan2gp_subprocess_env(root: Path, cfg: dict[str, Any] | None = None) -> dict[str, str]:
    """Isolated env for Wan2GP venv subprocesses (fixes SM uv setuptools/distutils clash)."""
    import os

    env: dict[str, str] = {}
    for key in (
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "LOCALAPPDATA",
        "CUDA_PATH",
        "CUDA_VISIBLE_DEVICES",
    ):
        if key in os.environ:
            env[key] = os.environ[key]

    venv = root / "venv"
    path_parts: list[str] = []
    if venv.is_dir():
        env["VIRTUAL_ENV"] = str(venv)
        path_parts.append(str(venv / "Scripts"))
    git = _find_git_exe()
    if git:
        env["GIT_PYTHON_GIT_EXECUTABLE"] = str(git)
        path_parts.append(str(git.parent))
    win = Path(env.get("SYSTEMROOT", r"C:\Windows"))
    path_parts.extend([str(win / "System32"), str(win)])
    env["PATH"] = os.pathsep.join(path_parts)
    # uv/SM venv: local distutils shim asserts against Assets Python stdlib distutils.
    env["SETUPTOOLS_USE_DISTUTILS"] = "stdlib"
    env["GIT_PYTHON_REFRESH"] = "quiet"
    # Wan2GP FastMCP reads host/port from FASTMCP_* (wgp.py --mcp-port is ignored on newer mcp pkg).
    if cfg is not None:
        w = _wan2gp_cfg(cfg)
        env["FASTMCP_HOST"] = str(w.get("mcp_host", "127.0.0.1"))
        env["FASTMCP_PORT"] = str(int(w.get("mcp_port", 7867)))
    return env


def _clean_subprocess_env(root: Path | None = None, cfg: dict[str, Any] | None = None) -> dict[str, str]:
    if root is not None:
        return _wan2gp_subprocess_env(root, cfg)
    import os

    env: dict[str, str] = {}
    for key in ("SYSTEMROOT", "TEMP", "TMP", "PATH"):
        if key in os.environ:
            env[key] = os.environ[key]
    env["SETUPTOOLS_USE_DISTUTILS"] = "stdlib"
    env["GIT_PYTHON_REFRESH"] = "quiet"
    return env


def _start_mcp_server(cfg: dict[str, Any], python: Path, root: Path) -> subprocess.Popen[Any]:
    w = _wan2gp_cfg(cfg)
    port = int(w.get("mcp_port", 7867))
    host = w.get("mcp_host", "127.0.0.1")
    out_dir = delivery_dir(cfg) or (root / "outputs")
    wgp = root / "wgp.py"
    mcp_args = [
        "--mcp",
        f"--mcp-transport=streamable-http",
        f"--mcp-host={host}",
        f"--mcp-port={port}",
        f"--output-dir={out_dir}",
    ]
    # Prefer venv python + isolated env (SETUPTOOLS_USE_DISTUTILS=stdlib). SM patch uses Assets
    # Python and breaks setuptools on uv-based venvs.
    cmd = [str(python), str(wgp), *mcp_args]
    return subprocess.Popen(
        cmd,
        cwd=str(root),
        env=_wan2gp_subprocess_env(root, cfg),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for_mcp(cfg: dict[str, Any], proc: subprocess.Popen[Any] | None) -> bool:
    w = _wan2gp_cfg(cfg)
    deadline = time.time() + float(w.get("mcp_wait_seconds", 120))
    while time.time() < deadline:
        status = inspect_gpu_backend(cfg)
        if status["wan2gp"].get("mcp_running"):
            return True
        if proc and proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"Wan2GP MCP exited early: {err[:2000]}")
        time.sleep(2)
    return False


def _run_subprocess_api(
    cfg: dict[str, Any],
    settings: dict[str, Any],
    python: Path,
    root: Path,
) -> dict[str, Any]:
    out_dir = delivery_dir(cfg) or (root / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    settings_path = Path(cfg["_root"]) / "outputs" / "_wan2gp_hero_task.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    cmd = [str(python), str(_RUNNER), str(root), str(settings_path), str(out_dir)]
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        env=_wan2gp_subprocess_env(root, cfg),
        capture_output=True,
        text=True,
        timeout=7200,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(
            f"Wan2GP subprocess failed ({proc.returncode}): {(proc.stderr or proc.stdout)[:2000]}"
        )
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError(f"Wan2GP subprocess bad output: {proc.stdout[:500]}") from exc
    return payload


def generate_video_hero(
    cfg: dict[str, Any],
    *,
    prompt: str,
    image_path: str,
    negative_prompt: str = "",
    video_length: int = 49,
    resolution: str = "832x480",
    seed: int = -1,
    motion_amplitude: float = 1.05,
    model_type: str = "i2v_2_2_Enhanced_Lightning_v2",
    comfyui_running: bool | None = None,
    prefer_mcp: bool = True,
) -> dict[str, Any]:
    from studio.gpu_backend import assert_backend_available

    status = assert_backend_available(
        cfg, "wan2gp", comfyui_running=comfyui_running, operation="generate_video_hero"
    )
    assets = check_wan2gp_assets(cfg)
    if not assets["summary"].get("lightning_v2_i2v"):
        raise RuntimeError("Wan2GP Lightning v2 I2V weights missing. Run download_wan2gp_assets.")

    if status["wan2gp"].get("ui_running"):
        raise RuntimeError(
            "Wan2GP Gradio UI is running on port 7860. Stop it and use generate_video_hero "
            "(auto-starts Wan2GP MCP) — one Wan2GP runtime at a time."
        )

    settings = build_hero_i2v_settings(
        prompt=prompt,
        image_path=image_path,
        negative_prompt=negative_prompt,
        video_length=video_length,
        resolution=resolution,
        seed=seed,
        motion_amplitude=motion_amplitude,
        model_type=model_type,
    )

    acquire_gpu_lock(cfg, "wan2gp", detail="generate_video_hero")
    mcp_proc: subprocess.Popen[Any] | None = None
    try:
        url = mcp_url(cfg)
        runtime = inspect_gpu_backend(cfg, comfyui_running=comfyui_running)
        if prefer_mcp and not runtime["wan2gp"].get("mcp_running"):
            w = _wan2gp_cfg(cfg)
            if w.get("auto_start_mcp"):
                python = resolve_wan2gp_python(cfg, runtime)
                if not python:
                    raise RuntimeError(
                        "Cannot resolve Wan2GP Python. Set wan2gp.python in config.yaml or launch Wan2GP once from Stability Matrix."
                    )
                root = wan2gp_root(cfg)
                mcp_proc = _start_mcp_server(cfg, python, root)
                if not _wait_for_mcp(cfg, mcp_proc):
                    raise RuntimeError("Wan2GP MCP did not become reachable in time.")

        runtime = inspect_gpu_backend(cfg, comfyui_running=comfyui_running)
        if runtime["wan2gp"].get("mcp_running"):
            snap = wangp_generate(url, settings, wait=True, timeout_s=7200)
            result = snap.get("result") or snap
            files = list(result.get("generated_files") or [])
            if not files and not result.get("success", True):
                errors = result.get("errors") or snap.get("errors") or []
                raise RuntimeError(f"Wan2GP generation failed: {json.dumps(errors)[:1500]}")
            saved, delivered = deliver_files(cfg, files)
            return {
                "backend": "wan2gp",
                "mode": "hero_i2v",
                "model_type": model_type,
                "prompt": prompt,
                "image_path": image_path,
                "settings": settings,
                "mcp_url": url,
                "job_snapshot": snap,
                "saved_files": saved,
                "delivered_files": delivered,
            }

        python = resolve_wan2gp_python(cfg, runtime)
        if not python:
            raise RuntimeError("Wan2GP MCP unreachable and no python executable resolved.")
        payload = _run_subprocess_api(cfg, settings, python, wan2gp_root(cfg))
        if not payload.get("success"):
            raise RuntimeError(json.dumps(payload.get("errors") or payload, indent=2))
        saved, delivered = deliver_files(cfg, payload.get("generated_files") or [])
        return {
            "backend": "wan2gp",
            "mode": "hero_i2v",
            "model_type": model_type,
            "prompt": prompt,
            "image_path": image_path,
            "subprocess": True,
            "saved_files": saved,
            "delivered_files": delivered,
            "raw": payload,
        }
    finally:
        release_gpu_lock(cfg, "wan2gp")
        if mcp_proc and mcp_proc.poll() is None:
            # Leave MCP running for follow-up jobs unless it was started just for this call
            pass
