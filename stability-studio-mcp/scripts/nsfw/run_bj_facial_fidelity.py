# -*- coding: utf-8 -*-
"""
Facial money-shot from oral-creampie last frame (good fidelity), not facial_00001.

CloseUpFacialCum at 1.0–1.15 + CFG 4+ was melting eyes/glans. Author notes higher
strength/CFG exaggerates cum but costs quality. Dial down + face naturalizer + locks.
"""
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
CREAM = VIDEO_DIR / "studio_agent_wan22_sq25_oralcream_00001.mp4"
BOBBING = VIDEO_DIR / "studio_agent_wan22_sq_bobbing19.mp4"
FINAL = VIDEO_DIR / "studio_agent_wan22_sq_25s_cum.mp4"
SIZE = 720

# Fidelity-first stack: milder facial cum, face naturalizer, light oral insert
HIGH_LORAS = [
    ("wan2.2-i2v-high-oral-insertion-v1.0.safetensors", 0.25),
    ("CloseUpFacialCum-v10_High.safetensors", 0.75),
    ("wan22-face-naturalizer.safetensors", 0.55),
    ("wan22-k3nk4llinon3-16epoc-full-high-k3nk.safetensors", 0.40),
]
LOW_LORAS = [
    ("wan2.2-i2v-low-oral-insertion-v1.0.safetensors", 0.25),
    ("CloseUpFacialCum-v10_Low.safetensors", 0.75),
    ("wan22-face-naturalizer.safetensors", 0.55),
    ("wan22-k3nk4llinon3-15epoc-full-low-k3nk.safetensors", 0.40),
]

PROMPT = (
    "k3nk4llin0n3, Facial, cum shot, cum, sticky cum, "
    "she pulls cock out of her mouth and shoots cum all over her face, "
    "penis fully withdraws from her lips, tip leaves her mouth completely, "
    "detailed glans, sharp penis head detail preserved, "
    "clear detailed anime eyes same as start frame, sharp iris pupils, "
    "cum shoots from penis onto her face, cum on face, cum on tongue, cum on chin, "
    "multiple thick slimy cum shots, woman mouth is open, woman tongue is extended, "
    "no more sucking, anime style, hold purple hair face identity"
)

NEG = (
    "going back in, reinserting, sucking again, penis stays in mouth, oral creampie, "
    "deformed eyes, messed up eyes, crossed eyes, empty eyes, blurry eyes, "
    "melted glans, blob penis tip, mushy penis head, losing detail, "
    "deflating penis, disappearing shaft, no cum, dry face, "
    "photoreal, identity change, morphing face, splash from above, drench"
)


def main() -> None:
    for p in (CREAM, BOBBING):
        if not p.is_file():
            raise FileNotFoundError(p)

    # face naturalizer is a single file — use on both stacks if only one exists
    import requests

    opts = requests.get(
        "http://192.168.50.57:8188/object_info/LoraLoaderModelOnly", timeout=30
    ).json()["LoraLoaderModelOnly"]["input"]["required"]["lora_name"][0]
    if "wan22-face-naturalizer.safetensors" not in opts:
        HIGH_LORAS[:] = [x for x in HIGH_LORAS if "face-naturalizer" not in x[0]]
        LOW_LORAS[:] = [x for x in LOW_LORAS if "face-naturalizer" not in x[0]]
        print("WARN: face-naturalizer not visible; continuing without it", flush=True)

    _wan22.HIGH_LORAS = HIGH_LORAS
    _wan22.LOW_LORAS = LOW_LORAS

    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)

    last = IMPORT_DIR / "close_up_sq25_cream_end_for_facial.png"
    extract_last_frame(CREAM, last)
    print(f"START fidelity facial from oralcream last frame {last}", flush=True)

    uploaded = eng.comfy.upload_image(last)
    api = build_api(
        image_name=uploaded,
        prompt=PROMPT,
        negative=NEG,
        width=SIZE,
        height=SIZE,
        length=49,
        steps=24,
        switch_step=12,
        cfg=3.5,
        seed=304,
    )
    api["70"]["inputs"]["filename_prefix"] = "studio_agent_wan22_sq25_facial_fid"
    prompt_id = eng.comfy.queue_prompt(api)
    history = eng.comfy.wait_for_completion(prompt_id)
    outputs = eng.comfy.collect_outputs(history)
    saved = eng._save_comfy_outputs(outputs, extensions=(".mp4", ".webm", ".gif", ".png"))
    if not saved:
        raise RuntimeError("No facial fidelity video")
    facial = Path(saved[0])

    joined = VIDEO_DIR / "studio_agent_wan22_sq_25s_cum_fid.mp4"
    concat_videos([BOBBING, CREAM, facial], joined)
    FINAL.write_bytes(joined.read_bytes())

    result = {
        "ok": True,
        "seed_frame": str(last),
        "seed_from": str(CREAM),
        "facial": str(facial),
        "final": str(FINAL),
        "also": str(joined),
        "duration_sec": probe_video(FINAL)["duration_sec"],
        "prompt_id": prompt_id,
        "loras_high": HIGH_LORAS,
        "cfg": 3.5,
        "facial_cum_strength": 0.75,
        "note": "Seeded from oralcream (not facial_00001). Milder FacialCum + face naturalizer.",
    }
    (ROOT / "outputs" / "bj_facial_fidelity.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("OK", json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
