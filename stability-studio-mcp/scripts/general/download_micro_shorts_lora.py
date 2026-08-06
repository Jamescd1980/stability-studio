# -*- coding: utf-8 -*-
"""Download micro shorts Illustrious LoCon into SM Lora/ + Extra Models LoRa's."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.civitai_download import civitai_api_key, download_civitai_checkpoint

# CivitAI: https://civitai.com/models/764799/micro-shortssdillpony
MODEL_PAGE = "https://civitai.com/models/764799/micro-shortssdillpony"
VERSION_ID = 993176  # v1.0 illustrious
FILENAME = "micro shorts_illustrious_V1.0.safetensors"
TRIGGER = "micro shorts, midriff, navel"

LOCAL_LORA = Path(r"D:\StabilityMatrix-win-x64\Data\Models\Lora")
EXTRA_LORA = Path(r"D:\Extra Models") / "LoRa's"


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    key = civitai_api_key(cfg)
    if not key:
        raise SystemExit("Missing civitai.api_key in config.yaml")

    sm_dest = LOCAL_LORA / FILENAME
    extra_dest = EXTRA_LORA / FILENAME
    EXTRA_LORA.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {FILENAME} (version {VERSION_ID}) …", flush=True)
    download_civitai_checkpoint(
        version_id=VERSION_ID,
        dest=sm_dest,
        api_key=key,
        force=False,
    )
    print(f"SM: {sm_dest} ({sm_dest.stat().st_size} bytes)", flush=True)

    if not extra_dest.is_file() or extra_dest.stat().st_size != sm_dest.stat().st_size:
        shutil.copy2(sm_dest, extra_dest)
        print(f"Extra Models: {extra_dest}", flush=True)
    else:
        print(f"Extra Models already present: {extra_dest}", flush=True)

    print("source:", MODEL_PAGE)
    print("trigger:", TRIGGER)


if __name__ == "__main__":
    main()
