"""Single BJ7 quality I2V link from Frierenbj7_forge (no Lightning, one beat)."""

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
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\pass1\Frierenbj7_forge.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
BEAT_ID = "bj7_bob"

# Axis lock: BJ7 is top-down vertical POV — "sliding" alone often becomes tip-orbit.
PROMPT = (
    "nsfw, she is giving him a blowjob, "
    "hands hold her head steady, "
    "her head bobs straight up and down along the shaft, "
    "deeper then shallower on the same axis, "
    "vertical bobbing only, "
    "cock stays in her mouth, lips sealed on the shaft, "
    "looking up, steady camera"
)
NEG = (
    "circular head motion, head circling, orbital head motion, "
    "head swaying side to side, rotating head, head rolling, "
    "pulling away, withdrawing, empty mouth, "
    "deflating penis, shrinking penis, disappearing shaft, "
    "melting face, morphing face, flicker, "
    "talking, chewing, biting, cartoon, chibi"
)

# Proven oral pair only (one action pair on quality MoE).
LORAS = [
    {
        "id": "oral_high",
        "file": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "weight": 0.75,
        "branch": "high",
    },
    {
        "id": "oral_low",
        "file": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "weight": 0.75,
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

    print(f"===== I2V {BEAT_ID} (quality) =====", flush=True)
    print("image", START, flush=True)

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
        motion_amplitude=0.75,
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
        "image": str(START),
        "path": str(promoted) if promoted else None,
        "moe": result.get("moe"),
        "preset": (result.get("moe") or {}).get("preset"),
    }
    out_json = ROOT / "outputs" / "bj7_quality_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "moe"}, indent=2), flush=True)
    print("DONE", out_json, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
