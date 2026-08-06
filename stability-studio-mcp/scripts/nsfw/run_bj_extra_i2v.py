"""BJ_extra — facial cumshot from still: cum shoots onto her face, light flinch."""

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
    r"\scene_packs\01 BJ Scene\BJ_extra.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
BEAT_ID = "BJ_extra"

PROMPT = (
    "nsfw, Facial, cum shot, sticky cum, "
    "thick erect penis in front of her face, tip pointed at her face, "
    "cum shoots out the tip of the penis onto her face, "
    "ropes of cum land on her cheeks, nose, lips, and chin, "
    "she flinches slightly as the cum hits, small startled blink, "
    "head tips back a little, mouth slightly open, "
    "looking up, steady camera, same face"
)
NEG = (
    "no cum, dry face, cum missing, weak dribble only, "
    "penis in mouth, sucking, oral insertion, going back in, "
    "coke bottle penis, bottle shaped penis, hourglass shaft, "
    "deformed tip, warped glans, melting tip, misshapen tip, "
    "deflating penis, shrinking penis, morphing genitals, "
    "melting face, morphing face, identity change, "
    "fast whip pan, violent thrashing, "
    "talking, chewing, biting, cartoon, chibi"
)

LORAS = [
    {
        "id": "facial_high",
        "file": "CloseUpFacialCum-v10_High.safetensors",
        "weight": 0.95,
        "branch": "high",
    },
    {
        "id": "facial_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 0.95,
        "branch": "low",
    },
    {
        "id": "oral_high",
        "file": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "weight": 0.25,
        "branch": "high",
    },
    {
        "id": "oral_low",
        "file": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "weight": 0.25,
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
    print(f"===== I2V {BEAT_ID} (facial cumshot + flinch) =====", flush=True)

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
        "motion_amplitude": 0.55,
        "note": "cum shoots onto face, slight flinch",
    }
    (ROOT / "outputs" / "bj_extra_i2v.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
