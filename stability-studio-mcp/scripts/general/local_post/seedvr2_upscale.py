# -*- coding: utf-8 -*-
"""SeedVR2 standalone CLI wrapper (main-rig 5060 Ti / dedicated .venv)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def upscale(
    src: Path,
    dest: Path,
    *,
    python: Path,
    cli: Path,
    model_dir: Path,
    dit_model: str = "seedvr2_ema_3b_fp8_e4m3fn.safetensors",
    resolution: int = 1080,
    batch_size: int = 5,
    blocks_to_swap: int = 16,
    crf_note: str = "",
    load_cap: int = 0,
    debug: bool = False,
) -> dict:
    if not python.is_file():
        raise FileNotFoundError(f"SeedVR2 python not found: {python}")
    if not cli.is_file():
        raise FileNotFoundError(f"SeedVR2 CLI not found: {cli}")
    if not src.is_file():
        raise FileNotFoundError(f"Video not found: {src}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(python),
        str(cli),
        str(src),
        "--output",
        str(dest),
        "--model_dir",
        str(model_dir),
        "--dit_model",
        dit_model,
        "--resolution",
        str(int(resolution)),
        "--batch_size",
        str(int(batch_size)),
        "--video_backend",
        "ffmpeg",
        "--color_correction",
        "lab",
        "--dit_offload_device",
        "cpu",
        "--vae_offload_device",
        "cpu",
        "--blocks_to_swap",
        str(int(blocks_to_swap)),
        "--swap_io_components",
        "--vae_encode_tiled",
        "--vae_decode_tiled",
        "--attention_mode",
        "sdpa",
    ]
    if load_cap > 0:
        cmd.extend(["--load_cap", str(int(load_cap))])
    if debug:
        cmd.append("--debug")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    # SeedVR2 may write beside dest with _upscaled suffix depending on version
    candidates = [dest]
    if dest.suffix:
        candidates.append(dest.with_name(f"{dest.stem}_upscaled{dest.suffix}"))
        candidates.append(dest.parent / "output" / dest.name)
    produced = next((p for p in candidates if p.is_file() and p.stat().st_size > 500), None)

    if proc.returncode != 0 and produced is None:
        err = (proc.stderr or proc.stdout or "")[-3000:]
        raise RuntimeError(f"SeedVR2 failed (code {proc.returncode}): {err}")

    if produced is None:
        # search recent mp4 in dest parent
        mp4s = sorted(dest.parent.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in mp4s[:5]:
            if p.resolve() != src.resolve() and p.stat().st_size > 500:
                produced = p
                break
    if produced is None:
        err = (proc.stderr or proc.stdout or "")[-3000:]
        raise RuntimeError(f"SeedVR2 produced no output file. Log: {err}")

    if produced.resolve() != dest.resolve():
        if dest.exists():
            dest.unlink()
        produced.replace(dest)
        produced = dest

    return {
        "ok": True,
        "method": "seedvr2",
        "dit_model": dit_model,
        "resolution": int(resolution),
        "batch_size": int(batch_size),
        "blocks_to_swap": int(blocks_to_swap),
        "source": str(src),
        "output": str(dest),
        "model_dir": str(model_dir),
        "note": crf_note or "SeedVR2 3B FP8 + VAE tiling + BlockSwap (16GB path)",
        "log_tail": ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-1500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="SeedVR2 video upscale")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--cli", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--dit-model", default="seedvr2_ema_3b_fp8_e4m3fn.safetensors")
    ap.add_argument("--resolution", type=int, default=1080)
    ap.add_argument("--batch-size", type=int, default=5)
    ap.add_argument("--blocks-to-swap", type=int, default=16)
    ap.add_argument("--load-cap", type=int, default=0)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    try:
        payload = upscale(
            Path(args.input),
            Path(args.output),
            python=Path(args.python),
            cli=Path(args.cli),
            model_dir=Path(args.model_dir),
            dit_model=args.dit_model,
            resolution=args.resolution,
            batch_size=args.batch_size,
            blocks_to_swap=args.blocks_to_swap,
            load_cap=args.load_cap,
            debug=args.debug,
        )
        print(json.dumps(payload))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
