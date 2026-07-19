#!/usr/bin/env python3
"""Download a catalog style checkpoint (Civitai) into Stability Matrix StableDiffusion folder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog
from studio.civitai_download import civitai_api_key, download_style_checkpoint
from studio.config import catalog_path, load_config
from studio.style_assets import check_style_assets


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a style checkpoint from Civitai")
    parser.add_argument("--style", default="ilustmix", help="Catalog style id")
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    args = parser.parse_args()

    cfg = load_config()
    catalog = StyleCatalog(catalog_path(cfg), cfg)
    sid = catalog._find_style_key(args.style)
    style = catalog.styles[sid]

    before = check_style_assets(cfg, catalog, sid)
    print(f"Style: {sid}  ready={before['ready']}")
    if before["missing"]:
        print("Missing:", before["missing"])

    if not civitai_api_key(cfg):
        print(
            "\nNo Civitai API key. Add to stability-studio-mcp/config.yaml:\n"
            "  civitai:\n"
            "    api_key: \"YOUR_KEY\"\n"
            "Or set CIVITAI_API_TOKEN. Create key at https://civitai.com/user/account\n"
            "Alternative: download via Stability Matrix → Models → Civitai → iLustMix → v10"
        )
        sys.exit(1)

    path = download_style_checkpoint(cfg, style, force=args.force)
    print(f"Downloaded: {path}")

    after = check_style_assets(cfg, catalog, sid)
    print(f"Ready: {after['ready']}")


if __name__ == "__main__":
    main()
