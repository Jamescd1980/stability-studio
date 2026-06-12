#!/usr/bin/env python3
"""Rin storyboard clip 1 — walk toward camera (Wan2GP hero I2V)."""
from __future__ import annotations

import json
import shutil
import sys
import traceback
from pathlib import Path

#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

_LEGACY = Path(__file__).resolve().parent
sys.path.insert(0, str(_LEGACY))
from _bootstrap import setup_paths

setup_paths()
MCP_ROOT = setup_paths()
import rin_project_paths as P

P.ensure_layout()
PROJECT_DIR = P.ROOT
IMAGE = P.HERO_STILL
PROMPT = (
    "anime kitsune fox girl Rin, white hair, white fox ears, fluffy white fox tails, "
    "dark blue military uniform and peaked cap, walking slowly toward the camera on a "
    "cherry blossom stone path, gentle steady forward walk, facing viewer, natural arm swing, "
    "soft daylight, sakura petals falling, cinematic"
)
NEGATIVE = (
    "blurry, distorted, bad anatomy, bad hands, camera shake, fast motion, running, "
    "bowing, jumping, low quality"
)
VIDEO_LENGTH = 49
RESOLUTION = "832x480"
SEED = 424250
MOTION = 1.12


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_clip1_walk_hero.json"
    try:
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        if not IMAGE.is_file():
            raise FileNotFoundError(IMAGE)

        cfg = load_config()
        cat = StyleCatalog(catalog_path(cfg), cfg)
        engine = GenerationEngine(cfg, cat)

        print("Starting clip 1 hero I2V (walk toward camera)...", flush=True)
        result = engine.generate_video_hero(
            prompt=PROMPT,
            image_path=str(IMAGE),
            negative_prompt=NEGATIVE,
            video_length=VIDEO_LENGTH,
            resolution=RESOLUTION,
            seed=SEED,
            motion_amplitude=MOTION,
        )

        saved = result.get("saved_files") or result.get("delivered_files") or []
        dest = P.CLIP1_WALK
        if saved:
            shutil.copy2(saved[0], dest)
            result["project_copy"] = str(dest)

        payload = {
            "clip": 1,
            "beat": "walk toward camera — dialogue: Greetings",
            "status": "success",
            "image": str(IMAGE),
            "prompt": PROMPT,
            "seed": SEED,
            "motion_amplitude": MOTION,
            "result": result,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, P.LOGS / "rin_clip1_walk_hero.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
