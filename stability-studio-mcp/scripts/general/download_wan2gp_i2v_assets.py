#!/usr/bin/env python3
"""Download missing Wan2GP I2V assets (disk/network only; does not start Wan2GP)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.wan2gp_assets import check_wan2gp_assets, download_wan2gp_lightning


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Wan2GP Lightning I2V weights")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    if args.check:
        print(json.dumps(check_wan2gp_assets(cfg), indent=2))
        return 0

    log_path = ROOT / "outputs" / "wan2gp_download_log.json"
    results = download_wan2gp_lightning(cfg, force=args.force)
    for entry in results:
        print(f"{entry.get('filename')}: {entry.get('status')}", flush=True)
    log_path.write_text(
        json.dumps({"results": results, "status": check_wan2gp_assets(cfg)}, indent=2),
        encoding="utf-8",
    )
    print(f"\nLog: {log_path}", flush=True)
    failed = sum(1 for r in results if r.get("status") == "error")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
