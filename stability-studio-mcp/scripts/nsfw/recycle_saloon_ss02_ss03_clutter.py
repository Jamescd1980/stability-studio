"""Recycle superseded SS02/SS03 Saloon clips and ss02 diag clutter (SendToRecycleBin)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "general"))

from recycle_path import recycle  # noqa: E402

SALOON = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon")
DIAG = ROOT / "outputs" / "saloon_diag_frames"

KEEP_SS02 = {
    "SS02_LC01_08s_pingpong_long_4x.mp4",
    "SS02_LC01_08s.mp4",
    "SS02_LC01_08s_pingpong.mp4",
}

KEEP_PREFIXES = ("SS01", "SS04", "BJ")

DIAG_CLUTTER = [
    DIAG / "ss02_lc01_early",
    DIAG / "ss02_lora_combo",
    DIAG / "ss02_pullout",
]


def should_keep(name: str) -> bool:
    if name in KEEP_SS02:
        return True
    return any(name.startswith(p) for p in KEEP_PREFIXES)


def main() -> int:
    kept: list[str] = []
    recycled: list[str] = []

    for item in sorted(SALOON.iterdir()):
        if not item.is_file():
            continue
        name = item.name
        upper = name.upper()
        if name.startswith("SS02") or name.startswith("SS03") or upper.startswith("SS02") or upper.startswith("SS03"):
            if should_keep(name):
                kept.append(str(item))
            else:
                if recycle(item):
                    recycled.append(str(item))
                else:
                    print(f"FAIL recycle {item}", flush=True)

    for d in DIAG_CLUTTER:
        if d.exists():
            if recycle(d):
                recycled.append(str(d))
            else:
                print(f"FAIL recycle {d}", flush=True)

    print("\n=== KEPT ===", flush=True)
    for p in kept:
        print(f"KEEP {p}", flush=True)

    print("\n=== RECYCLED ===", flush=True)
    for p in recycled:
        print(f"RECYCLE {p}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
