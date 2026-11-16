#!/usr/bin/env python3
"""Move media out of onedesk-mcp/outputs into ComfyBox Images/Video.

JSON/logs stay under studio-agent. Safe to re-run (skips identical files).
"""
from __future__ import annotations

import shutil
from pathlib import Path

MCP_OUT = Path(r"D:\studio-agent\onedesk-mcp\outputs")
IMAGES = Path(r"D:\ComfyBox Images and Videos\Images")
VIDEO = Path(r"D:\ComfyBox Images and Videos\Video")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv", ".avi"}


def main() -> int:
    IMAGES.mkdir(parents=True, exist_ok=True)
    VIDEO.mkdir(parents=True, exist_ok=True)
    moved = skipped = kept_json = 0
    for src in sorted(MCP_OUT.iterdir()):
        if not src.is_file():
            continue
        suf = src.suffix.lower()
        if suf in IMAGE_EXT:
            dest_dir = IMAGES
        elif suf in VIDEO_EXT:
            dest_dir = VIDEO
        else:
            if suf == ".json":
                kept_json += 1
            continue
        dest = dest_dir / src.name
        if dest.is_file() and dest.stat().st_size == src.stat().st_size:
            src.unlink()
            skipped += 1
            print(f"dedupe-delete {src.name}")
            continue
        if dest.is_file():
            dest = dest_dir / f"{src.stem}_from_mcp{src.suffix}"
        shutil.move(str(src), str(dest))
        moved += 1
        print(f"moved {src.name} -> {dest}")
    print(f"done moved={moved} deduped={skipped} json_left={kept_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
