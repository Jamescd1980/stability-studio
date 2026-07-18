# -*- coding: utf-8 -*-
"""Extend close-up shaft-lock clip via last-frame → Wan 2.2 dual+LoRA I2V, then concat."""
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
from studio.video_utils import concat_videos, extract_last_frame

_spec = importlib.util.spec_from_file_location(
    "run_bj_wan22_loras", ROOT / "scripts" / "run_bj_wan22_loras.py"
)
_wan22 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_wan22)
NEG = _wan22.NEG
build_api = _wan22.build_api

SOURCE = Path(r"D:\ComfyBox Images and Videos\Video\studio_agent_00005.mp4")
LAST = Path(r"D:\ComfyBox Images and Videos\User Import\close_up_bj_00005_last.png")
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video")

PROMPT = (
    "she continues the blowjob, head moves down the shaft taking him deeper, "
    "strong rhythmic bobbing, oral insertion, lips sealed around thick erect penis "
    "with constant girth, more motion than before, anime style, same purple hair face"
)


def main() -> None:
    extract_last_frame(SOURCE, LAST)
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)

    uploaded = eng.comfy.upload_image(LAST)
    api = build_api(
        image_name=uploaded,
        prompt=PROMPT,
        negative=NEG,
        # Must match source clip dims for concat (00005 is 480x832).
        width=480,
        height=832,
        length=81,
        steps=20,
        switch_step=10,
        cfg=3.5,
        seed=77,
    )
    # longer filename prefix for the continuation segment
    api["70"]["inputs"]["filename_prefix"] = "studio_agent_wan22_ext"

    print("START v2v extend from 00005 last frame", flush=True)
    prompt_id = eng.comfy.queue_prompt(api)
    history = eng.comfy.wait_for_completion(prompt_id)
    outputs = eng.comfy.collect_outputs(history)
    saved = eng._save_comfy_outputs(outputs, extensions=(".mp4", ".webm", ".gif", ".png"))
    if not saved:
        raise RuntimeError("No continuation video saved")

    cont = Path(saved[0])
    joined = OUT_DIR / "studio_agent_00005_extended.mp4"
    concat_videos([SOURCE, cont], joined)
    result = {
        "ok": True,
        "source": str(SOURCE),
        "last_frame": str(LAST),
        "continuation": str(cont),
        "joined": str(joined),
        "prompt_id": prompt_id,
    }
    out_json = ROOT / "outputs" / "bj_v2v_from_00005.json"
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("OK", json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
