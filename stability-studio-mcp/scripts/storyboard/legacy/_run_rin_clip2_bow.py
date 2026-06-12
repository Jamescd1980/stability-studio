#!/usr/bin/env python3
"""Rin clip 2 — bow + kunai drop (chain from clip 1 last frame)."""
from __future__ import annotations

import json
import shutil
import subprocess
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
from _env import comfy_python, imageio_ffmpeg

import rin_project_paths as P

P.ensure_layout()
PROJECT_DIR = P.ROOT
CLIP1 = P.CLIP1_WALK
LAST_FRAME = P.CLIP1_LAST

PROMPT = (
    "anime kitsune fox girl Rin, white hair, fox ears, white tails, dark blue military uniform, "
    "bows gently toward camera, respectful Japanese bow, upper body bend, "
    "then rises from bow as a small black kunai drops from her right sleeve into her right hand, "
    "holds kunai, cherry blossom park, soft daylight, cinematic"
)
NEGATIVE = (
    "blurry, distorted, bad anatomy, bad hands, extra fingers, walking away, running, "
    "already stabbing, sword swing, low quality"
)
VIDEO_LENGTH = 49
RESOLUTION = "832x480"
SEED = 424251
MOTION = 1.05


FFMPEG = imageio_ffmpeg()


def extract_last_frame(video: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    ff = str(FFMPEG) if FFMPEG.is_file() else "ffmpeg"
    # 49-frame clip → last index 48
    subprocess.run(
        [
            ff,
            "-y",
            "-i",
            str(video),
            "-vf",
            "select=eq(n\\,48)",
            "-vframes",
            "1",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    if not dest.is_file() or dest.stat().st_size < 500:
        raise RuntimeError(f"Failed to extract last frame to {dest}")


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_clip2_bow_hero.json"
    try:
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        if not CLIP1.is_file():
            raise FileNotFoundError(CLIP1)

        print("Extracting last frame from clip 1...", flush=True)
        extract_last_frame(CLIP1, LAST_FRAME)

        cfg = load_config()
        cat = StyleCatalog(catalog_path(cfg), cfg)
        engine = GenerationEngine(cfg, cat)

        print("Starting clip 2 hero I2V (bow + kunai)...", flush=True)
        result = engine.generate_video_hero(
            prompt=PROMPT,
            image_path=str(LAST_FRAME),
            negative_prompt=NEGATIVE,
            video_length=VIDEO_LENGTH,
            resolution=RESOLUTION,
            seed=SEED,
            motion_amplitude=MOTION,
        )

        saved = result.get("saved_files") or result.get("delivered_files") or []
        dest = P.CLIPS / "Rin_clip2_bow_kunai.mp4"
        if saved:
            shutil.copy2(saved[0], dest)
            result["project_copy"] = str(dest)

        payload = {
            "clip": 2,
            "beat": "bow + kunai into hand — dialogue: My name is Rin, you killed my father",
            "status": "success",
            "chain_from": str(LAST_FRAME),
            "prompt": PROMPT,
            "seed": SEED,
            "motion_amplitude": MOTION,
            "result": result,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, P.LOGS / "rin_clip2_bow_hero.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
