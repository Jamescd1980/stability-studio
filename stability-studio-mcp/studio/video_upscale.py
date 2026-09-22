"""Local CUDA upscale for Wan videos on the main rig (5060 Ti)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from studio.output_paths import deliver_files
from studio.video_utils import probe_video

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MODELS = {
    "anime_sharp_2x": "2x-AnimeSharpV4_RCAN.safetensors",
    "realesrgan_anime_4x": "RealESRGAN_x4plus_anime_6B.pth",
}

DEFAULT_RIFE_DIR = ROOT / "tools" / "rife"
DEFAULT_SEEDVR2_ROOT = ROOT / "tools" / "seedvr2_videoupscaler"
DEFAULT_SEEDVR2_DIT = "seedvr2_ema_3b_fp8_e4m3fn.safetensors"
DEFAULT_SEEDVR2_VAE = "ema_vae_fp16.safetensors"


def _post_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return dict(cfg.get("local_post") or {})


def post_python(cfg: dict[str, Any]) -> Path:
    pc = _post_cfg(cfg)
    raw = pc.get("python") or str(ROOT / ".venv-post" / "Scripts" / "python.exe")
    path = Path(str(raw))
    if not path.is_file():
        raise FileNotFoundError(
            f"Local post Python not found: {path}. "
            "Create with: py -3.10 -m venv .venv-post && "
            ".venv-post\\Scripts\\pip install torch torchvision --index-url "
            "https://download.pytorch.org/whl/cu128 && "
            ".venv-post\\Scripts\\pip install spandrel opencv-python-headless numpy Pillow"
        )
    return path


def models_dir(cfg: dict[str, Any]) -> Path:
    pc = _post_cfg(cfg)
    if pc.get("models_dir"):
        return Path(str(pc["models_dir"]))
    sm = cfg.get("stability_matrix") or {}
    return Path(str(sm.get("models") or ROOT / "models")) / "RealESRGAN"


def resolve_upscale_model(cfg: dict[str, Any], model: str = "") -> Path:
    pc = _post_cfg(cfg)
    key = (model or pc.get("default_upscale_model") or "anime_sharp_2x").strip()
    filename = DEFAULT_MODELS.get(key, key)
    path = models_dir(cfg) / filename
    if not path.is_file():
        # allow absolute / relative path
        alt = Path(filename)
        if alt.is_file():
            return alt
        raise FileNotFoundError(
            f"Upscale model missing: {path}. "
            f"Known keys: {', '.join(DEFAULT_MODELS)}. "
            "Copy from generation-host RealESRGAN/ or download AnimeSharp / RealESRGAN anime."
        )
    return path


def resolve_rife_exe(cfg: dict[str, Any]) -> Path:
    pc = _post_cfg(cfg)
    candidates = [
        Path(str(pc["rife_exe"])) if pc.get("rife_exe") else None,
        Path(str(pc["rife_dir"])) / "rife-ncnn-vulkan.exe" if pc.get("rife_dir") else None,
        DEFAULT_RIFE_DIR / "rife-ncnn-vulkan.exe",
        ROOT
        / "tools"
        / "rife-ncnn-vulkan"
        / "rife-ncnn-vulkan-refs"
        / "heads"
        / "master-windows"
        / "rife-ncnn-vulkan.exe",
    ]
    for c in candidates:
        if c is not None and c.is_file():
            return c
    raise FileNotFoundError(
        "RIFE-ncnn-vulkan.exe not found. Expected under tools/rife/ "
        "(TNTwise windows build)."
    )


def resolve_seedvr2_paths(cfg: dict[str, Any]) -> dict[str, Path]:
    pc = _post_cfg(cfg)
    root = Path(str(pc.get("seedvr2_root") or DEFAULT_SEEDVR2_ROOT))
    python = Path(str(pc.get("seedvr2_python") or (root / ".venv" / "Scripts" / "python.exe")))
    cli = Path(str(pc.get("seedvr2_cli") or (root / "inference_cli.py")))
    model_dir = Path(str(pc.get("seedvr2_model_dir") or (root / "models" / "SEEDVR2")))
    dit = model_dir / (pc.get("seedvr2_dit_model") or DEFAULT_SEEDVR2_DIT)
    vae = model_dir / (pc.get("seedvr2_vae_model") or DEFAULT_SEEDVR2_VAE)
    missing = [str(p) for p in (python, cli, dit, vae) if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "SeedVR2 stack incomplete. Missing: " + "; ".join(missing)
        )
    return {
        "root": root,
        "python": python,
        "cli": cli,
        "model_dir": model_dir,
        "dit": dit,
        "vae": vae,
    }


def check_local_post(cfg: dict[str, Any]) -> dict[str, Any]:
    """Inspect main-rig post stack (CUDA venv + upscale weights + RIFE/SeedVR2)."""
    info: dict[str, Any] = {"ok": True, "role": "main_rig_wan_post"}
    try:
        py = post_python(cfg)
        info["python"] = str(py)
    except Exception as exc:
        info["ok"] = False
        info["python_error"] = str(exc)
        py = None

    md = models_dir(cfg)
    info["models_dir"] = str(md)
    models = {}
    for key, name in DEFAULT_MODELS.items():
        p = md / name
        models[key] = {"filename": name, "present": p.is_file(), "path": str(p)}
    info["models"] = models

    if py is not None:
        try:
            out = subprocess.check_output(
                [
                    str(py),
                    "-c",
                    "import torch; print(torch.cuda.is_available()); "
                    "print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''); "
                    "print(round(torch.cuda.get_device_properties(0).total_memory/1024**3,1) "
                    "if torch.cuda.is_available() else 0)",
                ],
                text=True,
                timeout=60,
            ).strip().splitlines()
            info["cuda"] = out[0].strip().lower() == "true"
            info["gpu"] = out[1].strip() if len(out) > 1 else ""
            info["vram_gb"] = float(out[2]) if len(out) > 2 else 0.0
            if not info["cuda"]:
                info["ok"] = False
        except Exception as exc:
            info["ok"] = False
            info["cuda_error"] = str(exc)

    # RIFE
    rife: dict[str, Any] = {"present": False}
    try:
        exe = resolve_rife_exe(cfg)
        rife = {
            "present": True,
            "exe": str(exe),
            "model_default": (_post_cfg(cfg).get("rife_model") or "rife-v4.26"),
            "models_sample": sorted(
                [p.name for p in exe.parent.iterdir() if p.is_dir() and p.name.startswith("rife")]
            )[:12],
        }
    except Exception as exc:
        rife = {"present": False, "error": str(exc)}
        info["best_path_ok"] = False
    info["rife"] = rife

    # SeedVR2
    seed: dict[str, Any] = {"present": False}
    try:
        paths = resolve_seedvr2_paths(cfg)
        seed = {
            "present": True,
            "root": str(paths["root"]),
            "python": str(paths["python"]),
            "cli": str(paths["cli"]),
            "model_dir": str(paths["model_dir"]),
            "dit": str(paths["dit"]),
            "vae": str(paths["vae"]),
            "dit_bytes": paths["dit"].stat().st_size,
            "recommended": "3B FP8 + blocks_to_swap=16 + VAE tiling (16GB)",
            "wishlist_if_more_vram": "7B FP16 / 7B sharp, blocks_to_swap=0, batch_size=21+",
        }
        # quick cuda check on seed venv
        try:
            out = subprocess.check_output(
                [
                    str(paths["python"]),
                    "-c",
                    "import torch; print(torch.cuda.is_available()); "
                    "print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')",
                ],
                text=True,
                timeout=60,
                env={**os.environ, "PYTHONUTF8": "1"},
            ).strip().splitlines()
            seed["cuda"] = out[0].strip().lower() == "true"
            seed["gpu"] = out[1].strip() if len(out) > 1 else ""
            if not seed["cuda"]:
                info["ok"] = False
        except Exception as exc:
            seed["cuda_error"] = str(exc)
            info["ok"] = False
    except Exception as exc:
        seed = {"present": False, "error": str(exc)}
        info["best_path_ok"] = False
    info["seedvr2"] = seed

    info["best_path_ok"] = bool(rife.get("present") and seed.get("present"))
    info["default_upscale_model"] = (_post_cfg(cfg).get("default_upscale_model") or "anime_sharp_2x")
    info["paths"] = {
        "legacy": "interpolate_video(minterpolate) → upscale_video_local(AnimeSharp) / polish_wan_video",
        "best_free": "interpolate_video(method=rife) → upscale SeedVR2 / polish_wan_best",
    }
    info["note"] = (
        "Generate Wan on generation-host (7900 XT). Polish here: RIFE + SeedVR2 (best) or "
        "minterpolate + AnimeSharp (fast fallback) on 5060 Ti."
    )
    return info


def upscale_video_local(
    cfg: dict[str, Any],
    video_path: str | Path,
    *,
    model: str = "",
    output_dir: Path | None = None,
    crf: int = 17,
    max_frames: int = 0,
) -> dict[str, Any]:
    """Upscale a Wan MP4 on the main-rig CUDA venv."""
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video not found: {src}")

    py = post_python(cfg)
    model_path = resolve_upscale_model(cfg, model)
    out_root = output_dir or src.parent
    out_root.mkdir(parents=True, exist_ok=True)
    scale_tag = "2x" if "2x" in model_path.name.lower() else "4x"
    dest = out_root / f"{src.stem}_upscale_{scale_tag}.mp4"

    worker = ROOT / "scripts" / "general" / "local_post" / "upscale_video.py"
    cmd = [
        str(py),
        str(worker),
        "--input",
        str(src),
        "--output",
        str(dest),
        "--model",
        str(model_path),
        "--crf",
        str(int(crf)),
        "--max-frames",
        str(int(max_frames)),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2500:]
        raise RuntimeError(f"upscale_video failed: {err}")

    # worker prints JSON on last line
    line = (proc.stdout or "").strip().splitlines()[-1]
    payload = json.loads(line)
    if not dest.is_file():
        raise RuntimeError(f"Upscale produced no file: {dest}")

    saved = [str(dest)]
    saved, delivered = deliver_files(cfg, saved, bucket="temp")
    payload["saved_files"] = saved
    payload["delivered_files"] = delivered
    payload["probe"] = probe_video(Path(saved[0]))
    return payload


def upscale_video_seedvr2(
    cfg: dict[str, Any],
    video_path: str | Path,
    *,
    output_dir: Path | None = None,
    resolution: int = 1080,
    batch_size: int = 5,
    blocks_to_swap: int = 16,
    dit_model: str = "",
    load_cap: int = 0,
) -> dict[str, Any]:
    """Upscale a Wan MP4 with SeedVR2 standalone CLI (best free quality path)."""
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video not found: {src}")

    paths = resolve_seedvr2_paths(cfg)
    pc = _post_cfg(cfg)
    dit = (dit_model or pc.get("seedvr2_dit_model") or DEFAULT_SEEDVR2_DIT).strip()
    out_root = output_dir or src.parent
    out_root.mkdir(parents=True, exist_ok=True)
    dest = out_root / f"{src.stem}_seedvr2_{int(resolution)}.mp4"

    worker = ROOT / "scripts" / "general" / "local_post" / "seedvr2_upscale.py"
    cmd = [
        str(paths["python"]),
        str(worker),
        "--input",
        str(src),
        "--output",
        str(dest),
        "--python",
        str(paths["python"]),
        "--cli",
        str(paths["cli"]),
        "--model-dir",
        str(paths["model_dir"]),
        "--dit-model",
        dit,
        "--resolution",
        str(int(resolution)),
        "--batch-size",
        str(int(batch_size)),
        "--blocks-to-swap",
        str(int(blocks_to_swap)),
        "--load-cap",
        str(int(load_cap)),
    ]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-3000:]
        raise RuntimeError(f"seedvr2_upscale failed: {err}")

    line = (proc.stdout or "").strip().splitlines()[-1]
    payload = json.loads(line)
    if not dest.is_file():
        raise RuntimeError(f"SeedVR2 produced no file: {dest}")

    saved = [str(dest)]
    saved, delivered = deliver_files(cfg, saved, bucket="temp")
    payload["saved_files"] = saved
    payload["delivered_files"] = delivered
    payload["probe"] = probe_video(Path(saved[0]))
    return payload
