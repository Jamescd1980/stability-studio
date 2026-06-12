#!/usr/bin/env python3
"""Move local test artifacts from outputs/ to outputs/local/ (keeps README + .gitkeep)."""

from __future__ import annotations

import shutil
from pathlib import Path

KEEP = {".gitkeep", "README.md"}
OUT = Path(__file__).resolve().parents[1] / "outputs"
LOCAL = OUT / "local"


def main() -> int:
    LOCAL.mkdir(parents=True, exist_ok=True)
    moved = 0
    for item in sorted(OUT.iterdir()):
        if item.name in KEEP or item.name == "local":
            continue
        dest = LOCAL / item.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        shutil.move(str(item), str(dest))
        moved += 1
        print(f"moved {item.name} -> local/")
    print(f"Done: {moved} items -> {LOCAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
