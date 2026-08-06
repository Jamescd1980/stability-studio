"""BJ07 quality redo — tip stays in mouth, small bob (no pull-out tip deform)."""

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
    r"\scene_packs\01 BJ Scene\BJ07 Clean.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
BEAT_ID = "BJ07"

PROMPT = (
    "nsfw, she cleans his cock with her mouth, "
    "cock tip stays in her mouth the whole time, "
    "small gentle head bob, short stroke, soft suck, "
    "lips stay sealed near the tip, does not pull off, "
    "does not expose the tip, cum on her face stays, "
    "looking up, steady camera"
)
NEG = (
    "pulling out, pulling off, tip leaving her mouth, exposed tip, "
    "tip popping out, long withdrawal, empty mouth, tongue only, "
    "deformed tip, warped glans, melting tip, misshapen tip, "
    "coke bottle penis, bottle shaped penis, hourglass shaft, "
    "waisted shaft, uneven girth, morphing genitals, "
    "deformed penis, warped penis, melting penis, "
    "deflating penis, shrinking penis, stretchy penis, "
    "fast motion, violent thrusting, "
    "circular head motion, head circling, "
    "melting face, morphing face, flicker, "
    "talking, chewing, biting, cartoon, chibi"
)

LORAS = [
    {
        "id": "oral_high",
        "file": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "weight": 0.58,
        "branch": "high",
    },
    {
        "id": "oral_low",
        "file": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "weight": 0.58,
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
    print(f"===== I2V {BEAT_ID} REDO2 (stay in, small bob) =====", flush=True)

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
        motion_amplitude=0.32,
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
        "redo": 2,
        "motion_amplitude": 0.32,
        "note": "tip stays in mouth, small bob only — for ffmpeg loop/slice",
    }
    (ROOT / "outputs" / "bj07_redo2_i2v.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
