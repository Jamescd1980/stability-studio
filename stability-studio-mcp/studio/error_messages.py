"""Translate raw ComfyUI / engine errors into agent-friendly messages."""

from __future__ import annotations

import json
import re
from typing import Any


_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"gpu_backend_conflict|gpu_backend_lock", re.I),
        "gpu_backend_conflict",
        "GPU backend conflict — run check_gpu_backend. Stop ComfyUI before hero Wan2GP, or stop Wan2GP UI before ComfyUI video/audio.",
    ),
    (
        re.compile(r"connection lost|Connection refused|Failed to establish", re.I),
        "comfyui_connection",
        "ComfyUI disconnected mid-run. Restart ComfyUI from Stability Matrix, ensure no parallel "
        "video/audio jobs on 16 GB, then retry.",
    ),
    (
        re.compile(r"hostbuf_file_reader_read failed|cast_to_gathered", re.I),
        "gpu_oom",
        "GPU VRAM pressure during sampling (hostbuf read failed). On 16 GB: unload Jan's model from VRAM "
        "before generate, use face_detail=false, lower resolution (832x1216 max), restart ComfyUI, then retry.",
    ),
    (
        re.compile(r"out of memory|CUDA out of memory|OOM", re.I),
        "gpu_oom",
        "GPU ran out of VRAM. Lower num_frames, disable smooth_motion and Wan video LoRAs, "
        "close other GPU jobs (including Wan2GP), then retry.",
    ),
    (
        re.compile(r"36 channels, but got 16", re.I),
        "wan_wrong_checkpoint",
        "T2V workflow loaded an I2V checkpoint. Use workflow_id=t2v and ensure wan2.1_t2v_* is installed.",
    ),
    (
        re.compile(r"num_hidden_layers|MossTTSDelayConfig", re.I),
        "moss_transformers_compat",
        "MOSS-TTS speech failed: transformers/MOSS config mismatch. Update comfyui-moss-tts and "
        "transformers in the ComfyUI venv, then restart ComfyUI. Voice design may still work.",
    ),
    (
        re.compile(r"Cannot copy out of meta tensor", re.I),
        "moss_wrong_encoder",
        "Wrong text encoder for Wan I2V. Use umt5_xxl_fp8_e4m3fn_scaled (not umt5-xxl-enc-bf16) and restart ComfyUI.",
    ),
    (
        re.compile(r"\[Errno 22\].*Invalid argument", re.I),
        "vhs_ffmpeg",
        "Video mux failed (ffmpeg pipe). Set VHS_USE_IMAGEIO_FFMPEG=1 before ComfyUI start; "
        "install imageio-ffmpeg in the ComfyUI venv.",
    ),
    (
        re.compile(r"Missing node types|missing_node_types|was not found", re.I),
        "missing_nodes",
        "ComfyUI is missing custom nodes. Run check_comfyui_dependencies / install_comfyui_dependencies, "
        "then restart ComfyUI.",
    ),
    (
        re.compile(r"Timed out waiting for ComfyUI", re.I),
        "comfyui_timeout",
        "ComfyUI took too long. PainterI2V and MOSS voice_design can run 10–20 min on 16 GB — "
        "retry via Python script or increase tool timeout; avoid parallel GPU jobs.",
    ),
    (
        re.compile(r"finished without (video|audio) outputs", re.I),
        "no_outputs",
        "ComfyUI completed but produced no file. Check the ComfyUI console for validation errors or a stuck queue.",
    ),
]


def humanize_error(exc: BaseException | str, *, context: str = "") -> dict[str, Any]:
    """Return structured error with a short user-facing summary."""
    try:
        from studio.gpu_backend import GpuBackendConflict

        if isinstance(exc, GpuBackendConflict):
            info = dict(exc.info)
            info.setdefault("error_code", "gpu_backend_conflict")
            info.setdefault("summary", info.get("summary") or "GPU backend conflict — run check_gpu_backend.")
            return info
    except ImportError:
        pass

    raw = str(exc).strip()
    code = "unknown"
    summary = raw
    for pattern, err_code, message in _PATTERNS:
        if pattern.search(raw):
            code = err_code
            summary = message
            break
    if context and code == "unknown":
        summary = f"{context}: {raw[:400]}"
    return {
        "error_code": code,
        "summary": summary,
        "raw": raw[:2000],
        "hint_restart_comfyui": code
        in {"comfyui_connection", "gpu_oom", "missing_nodes", "moss_wrong_encoder", "moss_transformers_compat"},
        "hint_restart_mcp": code == "comfyui_timeout",
    }


def raise_humanized(exc: BaseException, *, context: str = "") -> None:
    info = humanize_error(exc, context=context)
    raise RuntimeError(json.dumps(info, indent=2)) from exc
