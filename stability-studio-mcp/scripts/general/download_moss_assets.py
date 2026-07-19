#!/usr/bin/env python3
"""Pre-download MOSS-TTS models for comfyui-moss-tts (disk only; no GPU)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.moss_assets import check_moss_assets, download_moss_models


def main() -> int:
    parser = argparse.ArgumentParser(description="Download MOSS-TTS models for ComfyUI")
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Model id: audio_tokenizer, tts_local, sound_effect, voice_generator (repeatable)",
    )
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    parser.add_argument("--check", action="store_true", help="Check readiness only")
    args = parser.parse_args()

    cfg = load_config()
    if args.check:
        print(json.dumps(check_moss_assets(cfg), indent=2))
        return 0

    log_path = ROOT / "outputs" / "moss_download_log.json"
    results = download_moss_models(cfg, model_ids=args.models, force=args.force)
    for entry in results:
        print(f"{entry.get('id')}: {entry.get('status')}", flush=True)
    log_path.write_text(
        json.dumps({"results": results, "status": check_moss_assets(cfg)}, indent=2),
        encoding="utf-8",
    )
    print(f"\nLog: {log_path}", flush=True)
    failed = sum(1 for r in results if r.get("status") == "error")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
