# -*- coding: utf-8 -*-
"""Download [ILLUST] Jessie | Pokémon into SM Lora/Jessie + Extra Models LoRa's."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.civitai_download import civitai_api_key, download_civitai_checkpoint

# CivitAI: https://civitai.com/models/1280858/illust-jessie-or-pokemon
MODEL_PAGE = "https://civitai.com/models/1280858/illust-jessie-or-pokemon"
VERSION_ID = 1445037  # v1.0 Illustrious
FILENAME = "jessie_pokemon_illust.safetensors"
TRIGGER = "jessie (pokemon)"

LOCAL_LORA = Path(r"D:\StabilityMatrix-win-x64\Data\Models\Lora") / "Jessie"
EXTRA_LORA = Path(r"D:\Extra Models") / "LoRa's"


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    key = civitai_api_key(cfg)
    if not key:
        raise SystemExit("Missing civitai.api_key in config.yaml")

    LOCAL_LORA.mkdir(parents=True, exist_ok=True)
    EXTRA_LORA.mkdir(parents=True, exist_ok=True)
    sm_dest = LOCAL_LORA / FILENAME
    extra_dest = EXTRA_LORA / FILENAME

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
