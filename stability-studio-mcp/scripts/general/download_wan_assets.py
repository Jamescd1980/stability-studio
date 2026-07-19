#!/usr/bin/env python3
"""Download missing Wan LoRAs / models for catalog video workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.wan_assets import check_all_video_assets, download_missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Wan assets for I2V / T2V workflows")
    parser.add_argument("--workflow", default="i2v_5b", help="Catalog id: i2v_5b, i2v, i2v_wan21, t2v, i2v_gpu")
    parser.add_argument("--all", action="store_true", help="Check all workflows (no download)")
    parser.add_argument("--include-large", action="store_true", help="Download multi-GB diffusion models")
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    args = parser.parse_args()

    cfg = load_config()
    if args.all:
        print(json.dumps(check_all_video_assets(cfg), indent=2))
        return 0

    if not args.include_large:
        print("Downloading small assets only (LoRAs, VAE). Pass --include-large for multi-GB diffusion models.")
    results = download_missing(
        cfg,
        args.workflow,
        include_large=args.include_large,
        force=args.force,
    )
    print(json.dumps(results, indent=2))
    status = check_all_video_assets(cfg)
    print(json.dumps(status["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
