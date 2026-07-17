#!/usr/bin/env python3
"""Download curated NSFW still-image LoRAs (Illustrious / Pony) into Stability Matrix Lora/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.nsfw_image_loras import (
    NSFW_IMAGE_LORA_BUNDLES,
    check_nsfw_image_loras,
    download_nsfw_image_loras,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download NSFW image LoRAs into Stability Matrix Lora/")
    parser.add_argument("--ids", default="", help="Comma-separated ids (ntr_mix_style, hentai_manga_pony, …)")
    parser.add_argument(
        "--bundle",
        default="",
        choices=[""] + list(NSFW_IMAGE_LORA_BUNDLES),
        help="Preset: illustrious_intimacy, illustrious_romance, pony_explicit, fantasy_romance",
    )
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    parser.add_argument("--check", action="store_true", help="Status only")
    args = parser.parse_args()

    cfg = load_config()
    ids = [s.strip() for s in args.ids.split(",") if s.strip()] or None

    if args.check:
        print(json.dumps(check_nsfw_image_loras(cfg, ids), indent=2))
        return 0

    results = download_nsfw_image_loras(cfg, lora_ids=ids, bundle=args.bundle, force=args.force)
    print(json.dumps(results, indent=2))
    print(json.dumps(check_nsfw_image_loras(cfg, ids), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
