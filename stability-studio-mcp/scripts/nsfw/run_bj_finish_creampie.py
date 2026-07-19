# -*- coding: utf-8 -*-
"""Append oral creampie + pull-out money shot (~6s) to the 12s close-up chain."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

from studio.config import load_config, catalog_path
from studio.engine import GenerationEngine
from studio.catalog import StyleCatalog
from studio.video_utils import concat_videos, extract_last_frame, probe_video

_spec = importlib.util.spec_from_file_location(
    "run_bj_wan22_loras", ROOT / "scripts" / "run_bj_wan22_loras.py"
)
_wan22 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_wan22)
build_api = _wan22.build_api

VIDEO_DIR = Path(r"D:\ComfyBox Images and Videos\Video")
IMPORT_DIR = Path(r"D:\ComfyBox Images and Videos\User Import")
SOURCE = VIDEO_DIR / "studio_agent_wan22_sq_12s.mp4"
SIZE = 720

# Beat 1: stay on shaft, oral creampie. Beat 2: pull out for money shot.
BEATS = [
    {
        "seed": 201,
        "prefix": "studio_agent_wan22_sq_cream",
        "negative": (
            "pulling away early, empty mouth, no cum, dry mouth, "
            "deflating penis, shrinking penis, disappearing shaft, "
            "chewing, biting, deformed hands, photoreal, identity change, "
            "morphing face, flicker, warped anatomy"
        ),
        "prompt": (
            "oral creampie, she keeps sucking as he cums in her mouth, "
            "thick cum fills her mouth around the shaft, lips sealed on thick erect penis "
            "with constant girth, rhythmic bobbing while cumming, anime style, "
            "same purple hair face framing"
        ),
    },
    {
        "seed": 202,
        "prefix": "studio_agent_wan22_sq_money",
        "negative": (
            "staying fully inserted, mouth stays closed on shaft, "
            "deflating penis, shrinking penis, disappearing shaft, melting cum, "
            "chewing, deformed hands, photoreal, identity change, morphing face, "
            "flicker, warped anatomy"
        ),
        "prompt": (
            "money shot, she pulls back off the shaft as he finishes, "
            "thick erect penis withdraws from her lips still solid with constant girth, "
            "cum on her tongue lips and chin, open mouth after oral creampie, "
            "anime style, same purple hair face framing"
        ),
    },
]


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)

    working = SOURCE
    log = []
    for i, beat in enumerate(BEATS):
        last = IMPORT_DIR / f"close_up_sq_finish_last_{i}.png"
        extract_last_frame(working, last)
        print(
            f"FINISH beat {i + 1}/{len(BEATS)} seed={beat['seed']} "
            f"(current {probe_video(working)['duration_sec']:.2f}s)",
            flush=True,
        )
        uploaded = eng.comfy.upload_image(last)
        api = build_api(
            image_name=uploaded,
            prompt=beat["prompt"],
            negative=beat["negative"],
            width=SIZE,
            height=SIZE,
            length=49,
            steps=20,
            switch_step=10,
            cfg=3.5,
            seed=beat["seed"],
        )
        api["70"]["inputs"]["filename_prefix"] = beat["prefix"]
        prompt_id = eng.comfy.queue_prompt(api)
        history = eng.comfy.wait_for_completion(prompt_id)
        outputs = eng.comfy.collect_outputs(history)
        saved = eng._save_comfy_outputs(
            outputs, extensions=(".mp4", ".webm", ".gif", ".png")
        )
        if not saved:
            raise RuntimeError(f"No video for beat {i + 1}")
        cont = Path(saved[0])
        joined = VIDEO_DIR / f"studio_agent_wan22_sq_finish_build_{i + 1}.mp4"
        concat_videos([working, cont], joined)
        working = joined
        entry = {
            "beat": i + 1,
            "seed": beat["seed"],
            "continuation": str(cont),
            "joined": str(joined),
            "duration_sec": probe_video(working)["duration_sec"],
            "last_frame": str(last),
            "prompt_id": prompt_id,
        }
        log.append(entry)
        print(
            f"FINISH joined → {joined.name} ({entry['duration_sec']:.2f}s)",
            flush=True,
        )

    final = VIDEO_DIR / "studio_agent_wan22_sq_final.mp4"
    final.write_bytes(working.read_bytes())
    result = {
        "ok": True,
        "source": str(SOURCE),
        "final": str(final),
        "duration_sec": probe_video(final)["duration_sec"],
        "finish_added_sec": probe_video(final)["duration_sec"]
        - probe_video(SOURCE)["duration_sec"],
        "beats": log,
    }
    out = ROOT / "outputs" / "bj_finish_creampie.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("OK", json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
