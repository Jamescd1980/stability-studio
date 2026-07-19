"""Copy approved pass1 masters into game scene packs (stills only)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from frieren_sex_scenes_refine_kit import OUT_DIR, SCENE_PACKS, SCENE_PACKS_DIR  # noqa: E402


def main() -> int:
    SCENE_PACKS_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    missing = []
    for pack, names in SCENE_PACKS.items():
        pack_dir = SCENE_PACKS_DIR / pack
        pack_dir.mkdir(parents=True, exist_ok=True)
        for i, name in enumerate(names, start=1):
            src = OUT_DIR / f"{Path(name).stem}_forge.png"
            if not src.is_file():
                missing.append(str(src))
                continue
            dest = pack_dir / f"{i:02d}_{src.name}"
            shutil.copy2(src, dest)
            copied.append({"pack": pack, "src": str(src), "dest": str(dest)})

    readme = SCENE_PACKS_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Frieren Sex Scenes — still packs",
                "",
                "Approved Forge masters from `_refined/pass1` (Stage3 + bj7 escalated).",
                "Face QA refs: recreate_003 (primary), recreate_007 (secondary).",
                "",
                "Packs:",
                "- `01_tease` — Stage1→4",
                "- `02_cowgirl` — Preinsert → Cowgirl1",
                "- `03_missionary` — Missionary1",
                "- `04_rear_lookback` — Doggystyle3",
                "- `05_oral` — bj4 / bj6 / bj7",
                "",
                "Next: Wan i2v on ComfyBox; polish (interp/upscale) on main rig.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    summary = {
        "ok": not missing,
        "packs_dir": str(SCENE_PACKS_DIR),
        "copied": copied,
        "missing": missing,
    }
    out_json = ROOT / "outputs" / "frieren_sex_scenes_packs.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
