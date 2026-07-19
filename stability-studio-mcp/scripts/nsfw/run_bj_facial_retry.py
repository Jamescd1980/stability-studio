# -*- coding: utf-8 -*-
"""Retry facial money-shot from failed facial last frame — strong pull-out + face cum."""
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
SEED_CLIP = VIDEO_DIR / "studio_agent_wan22_sq25_facial_00001.mp4"
BOBBING = VIDEO_DIR / "studio_agent_wan22_sq_bobbing19.mp4"
CREAM = VIDEO_DIR / "studio_agent_wan22_sq25_oralcream_00001.mp4"
FINAL = VIDEO_DIR / "studio_agent_wan22_sq_25s_cum.mp4"
SIZE = 720

HIGH_LORAS = [
    ("wan2.2-i2v-high-oral-insertion-v1.0.safetensors", 0.35),
    ("CloseUpFacialCum-v10_High.safetensors", 1.15),
    ("wan22-k3nk4llinon3-16epoc-full-high-k3nk.safetensors", 0.50),
]
LOW_LORAS = [
    ("wan2.2-i2v-low-oral-insertion-v1.0.safetensors", 0.35),
    ("CloseUpFacialCum-v10_Low.safetensors", 1.15),
    ("wan22-k3nk4llinon3-15epoc-full-low-k3nk.safetensors", 0.50),
]

PROMPT = (
    "k3nk4llin0n3, Facial, cum shot, cum, sticky cum, "
    "she pulls cock out of her mouth and shoot cum all over her face, "
    "penis fully withdraws from her lips, tip leaves her mouth, "
    "thick erect penis outside her mouth shoots cum onto her face, "
    "cum shoots from penis, cum on face, cum on tongue, cum on chin, "
    "multiple thick slimy cum shots, woman mouth is open, woman tongue is extended, "
    "no more sucking, anime style, same purple hair face"
)

NEG = (
    "going back in, reinserting, sucking again, oral insertion, "
    "penis stays in mouth, oral creampie, deepthroat, "
    "deflating penis, disappearing shaft, no cum, dry face, "
    "photoreal, identity change, morphing face, splash from above, drench"
)


def main() -> None:
    for p in (SEED_CLIP, BOBBING, CREAM):
        if not p.is_file():
            raise FileNotFoundError(p)

    _wan22.HIGH_LORAS = HIGH_LORAS
    _wan22.LOW_LORAS = LOW_LORAS

    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)

    last = IMPORT_DIR / "close_up_sq25_facial_retry_last.png"
    extract_last_frame(SEED_CLIP, last)
    print(f"START facial retry from {last}", flush=True)

    uploaded = eng.comfy.upload_image(last)
    api = build_api(
        image_name=uploaded,
        prompt=PROMPT,
        negative=NEG,
        width=SIZE,
        height=SIZE,
        length=49,
        steps=20,
        switch_step=10,
        cfg=4.5,
        seed=303,
    )
    api["70"]["inputs"]["filename_prefix"] = "studio_agent_wan22_sq25_facial2"
    prompt_id = eng.comfy.queue_prompt(api)
    history = eng.comfy.wait_for_completion(prompt_id)
    outputs = eng.comfy.collect_outputs(history)
    saved = eng._save_comfy_outputs(outputs, extensions=(".mp4", ".webm", ".gif", ".png"))
    if not saved:
        raise RuntimeError("No facial retry video saved")
    facial = Path(saved[0])

    joined = VIDEO_DIR / "studio_agent_wan22_sq_25s_cum_build2.mp4"
    concat_videos([BOBBING, CREAM, facial], joined)
    FINAL.write_bytes(joined.read_bytes())

    result = {
        "ok": True,
        "seed_clip": str(SEED_CLIP),
        "seed_frame": str(last),
        "facial": str(facial),
        "final": str(FINAL),
        "duration_sec": probe_video(FINAL)["duration_sec"],
        "prompt_id": prompt_id,
        "prompt": PROMPT,
    }
    (ROOT / "outputs" / "bj_facial_retry.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("OK", json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
