"""SS02 bury-first ladder — Try 1: SS02_bury_A1 (quality MoE, split Insertion weights)."""

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
    r"\scene_packs\Frieren Saloon\SS02.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon")
BEAT_ID = "SS02_bury_A1"

PROMPT = (
    "nsfw, a pov shot, he slowly pushes his cock into her pussy and stays buried, "
    "cock remains inside, vaginal penetration, hands stay gripping thighs, steady view"
)

NEG = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, shifting grip, squeezing thighs, extra hands, four hands, "
    "side to side, lateral sway, swinging sideways, left right wobble, "
    "hip shake, hip wiggle, shaking hips, body shake, "
    "penis pulse, pulsing cock, throbbing only, shaft pulse without thrust, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, shifting labia, jumping genitals, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

LORAS = [
    {
        "id": "missionary_insertion_high",
        "file": "wan2.2-i2v-high-pov-missionary-insertion-v1.safetensors",
        "weight": 0.35,
        "branch": "high",
    },
    {
        "id": "missionary_insertion_low",
        "file": "wan2.2-i2v-low-pov-missionary-insertion-v1.safetensors",
        "weight": 1.0,
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

    print(f"===== I2V {BEAT_ID} quality amp=0.31 frames=33 =====", flush=True)
    print("image", START, flush=True)

    result = engine.generate_video(
        prompt=PROMPT,
        mode="i2v",
        negative_prompt=NEG,
        workflow_id="i2v",
        content_rating="open",
        image_path=str(START),
        num_frames=33,
        frame_rate=16.0,
        loras=LORAS,
        moe_preset="quality",
        smooth_motion=False,
        motion_amplitude=0.31,
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
        "experiment": BEAT_ID,
        "image": str(START),
        "path": str(promoted) if promoted else None,
        "preset": (result.get("moe") or {}).get("preset"),
        "motion_amplitude": 0.31,
        "frames": 33,
        "frame_rate": 16.0,
        "loras": LORAS,
        "prompt": PROMPT,
        "result_ok": result.get("ok"),
    }
    out_json = ROOT / "outputs" / f"saloon_{BEAT_ID}_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print("DONE", out_json, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
