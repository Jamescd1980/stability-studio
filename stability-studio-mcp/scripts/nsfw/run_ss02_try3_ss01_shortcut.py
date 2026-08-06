"""SS02 Try 3 — SS01 deepest clean frame shortcut + Missionary Sex thrust."""

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

SS01_VIDEO = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon\SS01.mp4")
SS01_DEEP_FRAME = Path(
    r"D:\studio-agent\stability-studio-mcp\outputs\saloon_diag_frames\ss01_deep_pick\t05s.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon")
BEAT_ID = "SS02_try3_ss01_shortcut_sex"

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

SEX_LORAS = [
    {
        "id": "missionary_sex_high",
        "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "high",
    },
    {
        "id": "missionary_sex_low",
        "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "low",
    },
]

PROMPT = (
    "nsfw, A naked man and a naked woman having sex. "
    "He thrusts his penis in and out of her vagina. a pov shot. "
    "cock stays inside, partial withdraw only, vaginal penetration, steady view"
)


def main() -> int:
    if not SS01_DEEP_FRAME.is_file():
        print(f"missing {SS01_DEEP_FRAME}", flush=True)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    shortcut_still = OUT_DIR / "SS02_from_SS01_deep.png"
    if shortcut_still.is_file():
        recycle(shortcut_still)
    shutil.copy2(SS01_DEEP_FRAME, shortcut_still)
    print("shortcut still (SS01 t=0.5s)", shortcut_still, flush=True)

    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

    print(f"===== I2V {BEAT_ID} quality amp=0.32 frames=33 =====", flush=True)
    result = engine.generate_video(
        prompt=PROMPT,
        mode="i2v",
        negative_prompt=NEG,
        workflow_id="i2v",
        content_rating="open",
        image_path=str(shortcut_still),
        num_frames=33,
        frame_rate=16.0,
        loras=SEX_LORAS,
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
        "experiment": BEAT_ID,
        "approach": "SS01 deepest clean frame (t=0.5s) shortcut -> Missionary Sex thrust",
        "shortcut_note": "NOT SS02 pack identity — SS01 composition/props; thrust beat only",
        "source_video": str(SS01_VIDEO),
        "source_frame": str(SS01_DEEP_FRAME),
        "image": str(shortcut_still),
        "path": str(promoted) if promoted else None,
        "preset": (result.get("moe") or {}).get("preset"),
        "motion_amplitude": 0.32,
        "frames": 33,
        "loras": SEX_LORAS,
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
