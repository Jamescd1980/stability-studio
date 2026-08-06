"""One-shot HQ Wild Fern darkness→Fern strap doggy I2V (quality-first)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402
from studio.hardware_profile import build_generation_limits, fit_i2v_dimensions  # noqa: E402

IMAGE = Path(r"D:\ComfyBox Images and Videos\User Import\Movie_WildFern_04_darkness_strap.png")

LORAS = [
    {
        "id": "doggy_high",
        "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "weight": 0.55,
        "branch": "high",
    },
    {
        "id": "doggy_low",
        "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "weight": 0.55,
        "branch": "low",
    },
]


def main() -> int:
    cfg = load_config()
    limits = build_generation_limits(20.0, cfg)
    caps = limits["video_i2v"]
    print("caps", json.dumps(caps, indent=2), flush=True)
    w, h = fit_i2v_dimensions(1920, 1080, int(caps["max_width"]), int(caps["max_height"]))
    print(f"target dims {w}x{h}", flush=True)

    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    result = engine.generate_video(
        prompt=(
            "they are having doggy style sex, front-to-back hip thrusts, "
            "pelvis pumps forward then slight pullback, strap stays inside, hips only"
        ),
        mode="i2v",
        workflow_id="i2v",
        content_rating="open",
        moe_preset="quality",
        draft=False,
        image_path=str(IMAGE),
        loras=LORAS,
        num_frames=49,
        frame_rate=16.0,
        negative_prompt=(
            "talking, speaking, mouth moving, lips moving, lip sync, chewing, jaw moving, "
            "open close mouth, facial animation, face moving, head turn, looking around, "
            "eye blink spam, glowing eyes, blank eyes, asymmetrical eyes, deformed eyes, "
            "expression change, smiling, camera pan, zoom, morphing, melting, extra limbs, "
            "full withdrawal, penis exit, deflating cock"
        ),
    )
    print(json.dumps(result, indent=2, default=str), flush=True)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
