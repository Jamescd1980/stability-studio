#!/usr/bin/env python3
"""Wan2GP hero I2V bow test — same kitsune still as ComfyUI MCP path."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
from _bootstrap import ROOT, load_engine, setup_path  # noqa: E402

setup_path()
from studio.wan2gp_assets import check_wan2gp_assets, wan2gp_root  # noqa: E402

OUT = ROOT / "outputs"

BOW_PROMPT = (
    "(at 0 seconds: anime kitsune fox girl, white hair, red eyes, fox ears and tails, "
    "navy military uniform with cherry blossom patterns, standing on sakura park path, camera static).\n"
    "(at 1 second: same character bends forward in polite Japanese ojigi bow, waist bend, tails flow behind, smooth motion).\n"
    "(at 2 seconds: same character returns upright, calm expression, cherry blossom petals falling)."
)


def build_settings(image_path: Path, *, frames: int = 49) -> dict:
    return {
        "settings_version": 2.56,
        "model_type": "i2v_2_2_Enhanced_Lightning_v2",
        "base_model_type": "i2v_2_2",
        "prompt": BOW_PROMPT,
        "negative_prompt": "static, frozen, blurry, deformed, bad anatomy, different character",
        "resolution": "832x480",
        "video_length": frames,
        "batch_size": 1,
        "seed": 424242,
        "num_inference_steps": 4,
        "guidance_scale": 1,
        "guidance2_scale": 1,
        "guidance_phases": 2,
        "switch_threshold": 900,
        "flow_shift": 5,
        "sample_solver": "unipc",
        "image_prompt_type": "S",
        "motion_amplitude": 1.05,
        "multi_prompts_gen_type": "FG",
        "image_start": str(image_path.resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Wan2GP kitsune bow I2V test")
    parser.add_argument("--image", required=True, help="Hero still (absolute path)")
    parser.add_argument("--frames", type=int, default=49)
    parser.add_argument("--dry-run", action="store_true", help="Validate settings only")
    parser.add_argument("--run", action="store_true", help="Run full Wan2GP CLI generation")
    args = parser.parse_args()

    cfg, _, _ = load_engine()
    status = check_wan2gp_assets(cfg)
    if not status["summary"].get("lightning_v2_i2v"):
        print(json.dumps(status, indent=2), file=sys.stderr)
        print("Wan2GP Lightning v2 assets missing.", file=sys.stderr)
        return 1

    root = wan2gp_root(cfg)
    wgp = root / "wgp.py"
    venv_py = root / "venv" / "Scripts" / "python.exe"
    py = str(venv_py if venv_py.is_file() else sys.executable)

    image = Path(args.image)
    if not image.is_file():
        print(f"Image not found: {image}", file=sys.stderr)
        return 1

    settings_path = OUT / "wan2gp_bow_settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(build_settings(image, frames=args.frames), indent=2), encoding="utf-8")

    delivery = status.get("outputs") or str(root / "outputs")
    cmd = [
        py,
        str(wgp),
        "--process",
        str(settings_path),
        "--output_dir",
        str(delivery),
    ]
    if args.dry_run or not args.run:
        cmd.append("--dry-run")

    print(f"Wan2GP root: {root}", flush=True)
    print(f"Command: {' '.join(cmd)}", flush=True)
    if args.run and not args.dry_run:
        print(
            "WARNING: Stop ComfyUI and other GPU jobs before hero Wan2GP on 16 GB.",
            flush=True,
        )

    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)

    log = {
        "date": datetime.now(timezone.utc).isoformat(),
        "settings": str(settings_path),
        "delivery": delivery,
        "dry_run": args.dry_run or not args.run,
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-4000:] if proc.stdout else "",
    }
    log_path = OUT / "wan2gp_bow_test.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"Log: {log_path}", flush=True)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
