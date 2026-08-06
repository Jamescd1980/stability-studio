# -*- coding: utf-8 -*-
"""CLI: best free Wan polish — RIFE then SeedVR2 (main-rig 5060 Ti)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.video_post import polish_wan_best  # noqa: E402
from studio.video_upscale import check_local_post  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Best free Wan polish (RIFE → SeedVR2)")
    ap.add_argument("--input", default="", help="Locked master MP4 (required unless --check-only)")
    ap.add_argument("--target-fps", type=float, default=24.0)
    ap.add_argument("--skip-interpolate", action="store_true")
    ap.add_argument("--skip-upscale", action="store_true")
    ap.add_argument("--rife-model", default="")
    ap.add_argument("--resolution", type=int, default=0, help="SeedVR2 short-side (default config/1080)")
    ap.add_argument("--batch-size", type=int, default=0)
    ap.add_argument("--blocks-to-swap", type=int, default=-1)
    ap.add_argument("--max-frames", type=int, default=0, help="Smoke: limit frames")
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    status = check_local_post(cfg)
    if args.check_only:
        print(json.dumps(status, indent=2))
        return 0 if status.get("ok") and status.get("best_path_ok") else 1

    if not args.input:
        print(json.dumps({"ok": False, "error": "--input required unless --check-only"}, indent=2))
        return 2

    if not status.get("best_path_ok"):
        print(json.dumps({"ok": False, "error": "best path incomplete", "status": status}, indent=2))
        return 1

    result = polish_wan_best(
        cfg,
        args.input,
        target_fps=args.target_fps,
        skip_interpolate=args.skip_interpolate,
        skip_upscale=args.skip_upscale,
        crf=args.crf,
        rife_model=args.rife_model,
        seedvr2_resolution=args.resolution,
        seedvr2_batch_size=args.batch_size,
        seedvr2_blocks_to_swap=args.blocks_to_swap,
        max_frames=args.max_frames,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
