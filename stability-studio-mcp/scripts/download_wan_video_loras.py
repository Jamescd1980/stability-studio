#!/usr/bin/env python3
"""Download optional Wan 2.2 video LoRAs (motion, face, lighting)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.wan_video_loras import (
    WAN_VIDEO_LORA_BUNDLES,
    check_wan_video_loras,
    download_wan_video_loras,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Wan video LoRAs into Stability Matrix Lora/")
    parser.add_argument(
        "--ids",
        default="",
        help="Comma-separated LoRA ids (face_naturalizer, light_volumetric, …)",
    )
    parser.add_argument(
        "--bundle",
        default="",
        choices=[""] + list(WAN_VIDEO_LORA_BUNDLES),
        help="Preset bundle: smooth_character, walk_cycle, cinematic_church, motion_boost",
    )
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    parser.add_argument("--check", action="store_true", help="Status only, no download")
    args = parser.parse_args()

    cfg = load_config()
    ids = [s.strip() for s in args.ids.split(",") if s.strip()] or None

    if args.check:
        print(json.dumps(check_wan_video_loras(cfg, ids), indent=2))
        return 0

    results = download_wan_video_loras(cfg, lora_ids=ids, bundle=args.bundle, force=args.force)
    print(json.dumps(results, indent=2))
    print(json.dumps(check_wan_video_loras(cfg, ids), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
