"""BJ06 quality redo — tongue circles tip (correct spot), then takes cock in mouth.

Goal: usable mid/end frames with tongue placement for a later LF2V continue.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "general"))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

from recycle_path import recycle  # noqa: E402

START = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\scene_packs\01 BJ Scene\BJ06 Lick.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
BEAT_ID = "BJ06"

# Two-beat motion: circle tip → oral take-in. Prefer underside/frenulum contact.
PROMPT = (
    "nsfw, she teases his cock with her tongue then takes him into her mouth, "
    "first her tongue slowly circles around the tip and glans, "
    "tongue presses the underside and frenulum under the tip as it circles, "
    "then she opens her mouth and takes the tip into her mouth, "
    "soft suck after the circle, looking up, steady camera, "
    "shaft keeps constant cylindrical girth"
)
NEG = (
    "tongue stuck only on the top of the penis, tongue glued to the dorsal side, "
    "licking only the upper side of the glans, weird tongue angle, "
    "coke bottle penis, bottle shaped penis, hourglass shaft, "
    "waisted shaft, uneven girth, morphing genitals, "
    "deformed penis, warped penis, melting penis, "
    "fast motion, violent thrusting, head spinning, "
    "melting face, morphing face, flicker, "
    "talking, chewing, biting, cartoon, chibi"
)

LORAS = [
    {
        "id": "oral_high",
        "file": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "weight": 0.55,
        "branch": "high",
    },
    {
        "id": "oral_low",
        "file": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "weight": 0.55,
        "branch": "low",
    },
]


def main() -> int:
    if not START.is_file():
        print(f"missing {START}", flush=True)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    engine.comfy.timeout = max(getattr(engine.comfy, "timeout", 600), 7200)
    print(f"===== I2V {BEAT_ID} REDO (circle tip then mouth) =====", flush=True)

    result = engine.generate_video(
        prompt=PROMPT,
        mode="i2v",
        negative_prompt=NEG,
        workflow_id="i2v",
        content_rating="open",
        image_path=str(START),
        num_frames=65,
        frame_rate=16.0,
        loras=LORAS,
        moe_preset="quality",
        smooth_motion=False,
        motion_amplitude=0.55,
    )

    saved = result.get("saved_files") or []
    if isinstance(saved, str):
        saved = [saved]
    dest = OUT_DIR / f"{BEAT_ID}.mp4"
    promoted = None
    for p in saved:
        src = Path(str(p))
        if src.is_file() and src.suffix.lower() == ".mp4":
            if dest.is_file():
                recycle(dest)
            shutil.move(str(src), str(dest))
            promoted = dest
            break

    summary = {
        "ok": bool(promoted),
        "id": BEAT_ID,
        "path": str(promoted) if promoted else None,
        "redo": True,
        "motion_amplitude": 0.55,
        "note": "tongue circles tip/frenulum then takes into mouth (LF2V seed hunt)",
    }
    (ROOT / "outputs" / "bj06_redo_i2v.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
