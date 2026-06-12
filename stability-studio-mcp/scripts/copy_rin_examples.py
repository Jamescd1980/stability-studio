"""Copy Example Images into onboarding/examples/rin/."""
from __future__ import annotations

import shutil
from pathlib import Path

SRC = Path(r"C:\Users\Creel\Desktop\New Images\Example Images")
DST = Path(__file__).resolve().parents[2] / "onboarding" / "examples" / "rin"

COPIES: list[tuple[str, Path]] = [
    ("Rin_kitsune_approved.png", DST / "images" / "Rin_kitsune_approved.png"),
    ("Kitsune_blossom_hero.png", DST / "images" / "Kitsune_blossom_hero.png"),
    ("Kitsune_blossom_clip1_bow_petals.mp4", DST / "clips" / "Rin_clip2_bow_petals.mp4"),
    ("Kitsune_blossom_spliced.mp4", DST / "final" / "Rin_storyboard_spliced.mp4"),
]

walk = next(SRC.glob("2026-06-11*.mp4"), None)
if walk:
    COPIES.append((walk.name, DST / "clips" / "Rin_clip1_walk_hero.mp4"))

for _, target in COPIES:
    target.parent.mkdir(parents=True, exist_ok=True)

for src_name, target in COPIES:
    src = SRC / src_name
    shutil.copy2(src, target)
    mb = target.stat().st_size / (1024 * 1024)
    print(f"{src.name} -> {target.relative_to(DST)} ({mb:.2f} MB)")
