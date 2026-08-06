#!/usr/bin/env python3
"""Download CubeyAI WAN General NSFW HIGH+LOW into ComfyBox Lora folder."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stability-studio-mcp"
sys.path.insert(0, str(ROOT))

from studio.civitai_download import civitai_api_key, download_civitai_checkpoint  # noqa: E402
from studio.config import load_config  # noqa: E402

# Destination on ComfyBox share (mounted / visible from Windows as D: game path if mapped)
DEST_DIR = Path(r"D:\ComfyBox Images and Videos")  # may not be Lora
# Prefer Stability Matrix Lora on the generation host via UNC/local mapping used by team.
CANDIDATES = [
    Path(r"\\comfybox\game\StabilityMatrix-win-x64\Data\Models\Lora"),
    Path(r"D:\StabilityMatrix\Data\Models\Lora"),
    Path(r"\\192.168.50.57\game\StabilityMatrix-win-x64\Data\Models\Lora"),
]

FILES = [
    (2073605, "NSFW-22-H-e8.safetensors"),
    (2083303, "NSFW-22-L-e8.safetensors"),
]


def resolve_lora_dir(cfg: dict) -> Path:
    models = Path((cfg.get("stability_matrix") or {}).get("models") or "")
    if models.is_dir():
        d = models / "Lora"
        d.mkdir(parents=True, exist_ok=True)
        return d
    for c in CANDIDATES:
        if c.is_dir():
            return c
    # Fallback: write under studio-agent then scp
    d = Path(r"D:\studio-agent\_downloads\Lora")
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> int:
    cfg = load_config()
    key = civitai_api_key(cfg)
    if not key:
        print("No Civitai API key")
        return 2
    dest_dir = resolve_lora_dir(cfg)
    print("dest", dest_dir)
    for vid, name in FILES:
        dest = dest_dir / name
        if dest.is_file() and dest.stat().st_size > 100_000_000:
            print("skip", name, dest.stat().st_size // (1024 * 1024), "MB")
            continue
        # remove HTML stubs
        if dest.is_file() and dest.stat().st_size < 100_000:
            dest.unlink()
        print("download", name, "version", vid)
        download_civitai_checkpoint(
            version_id=vid, dest=dest, api_key=key, force=True
        )
        print("OK", name, dest.stat().st_size // (1024 * 1024), "MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
