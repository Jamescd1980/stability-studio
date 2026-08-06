"""BJ7: hold deep, oral creampie — cum leaks while cock stays fully in. Minimal bobbing."""

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

START = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\bj7_deep_hold_start.png")
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
BEAT_ID = "bj7_cum_hold"

PROMPT = (
    "nsfw, she is giving him a blowjob, "
    "his hands grip her head and twin tails firmly, "
    "he holds her head down deep on his cock, "
    "cock stays buried all the way in, she cannot pull back, "
    "almost no head movement, held still deep, "
    "he cums in her mouth, small oral creampie, "
    "a little thick white cum leaks from the corners of her lips around the shaft, "
    "light drip only, not a lot of cum, "
    "penis stays fully inserted, looking up, steady camera"
)
NEG = (
    "pulling out, withdrawing, empty mouth, money shot, facial, "
    "hands leaving her head, letting go, head free, "
    "bobbing, head moving up and down, thrusting head, "
    "circular head motion, head circling, "
    "milk, spewing cum, cum fountain, cum explosion, "
    "excessive cum, flooding cum, cum everywhere, gushing, "
    "deflating penis, shrinking penis, disappearing shaft, "
    "melting face, morphing face, flicker, "
    "talking, chewing, biting, cartoon, chibi, no cum, dry mouth"
)

LORAS = [
    {
        "id": "oral_high",
        "file": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "weight": 0.7,
        "branch": "high",
    },
    {
        "id": "oral_low",
        "file": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "weight": 0.7,
        "branch": "low",
    },
    {
        "id": "dt_high",
        "file": "wan22-ultimatedeepthroat-i2v-102epoc-high-k3nk.safetensors",
        "weight": 0.45,
        "branch": "high",
    },
    {
        "id": "dt_low",
        "file": "wan22-ultimatedeepthroat-I2V-101epoc-low-k3nk.safetensors",
        "weight": 0.45,
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
        motion_amplitude=0.65,
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
        "preset": (result.get("moe") or {}).get("preset"),
    }
    out_json = ROOT / "outputs" / "bj7_cum_hold_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print("DONE", out_json, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
