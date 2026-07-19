# -*- coding: utf-8 -*-
"""
Redo climax from almost-out pose with stacked cum prompts + Facial Cum LoRA.

Author triggers (checked on CivitAI):
- Oral Insertion: \"A man appears and she sucks his penis\"
- DeepThroat K3NK: long deepthroat sentence (skip for cum beats — fights withdraw)
- K3NK helper: k3nk4llin0n3
- Close-Up Facial Cum: no single trigger; use cum shoots / sticky / facial tags
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
# User: end of second climax clip — tip almost out. Hold there for oral creampie.
SEED_CLIP = VIDEO_DIR / "studio_agent_wan22_sq25_money_00001.mp4"
BOBBING = VIDEO_DIR / "studio_agent_wan22_sq_bobbing19.mp4"
FINAL = VIDEO_DIR / "studio_agent_wan22_sq_25s_cum.mp4"
SIZE = 720

# Climax stack: oral insertion + facial cum + helper (drop deepthroat for finish)
HIGH_LORAS = [
    ("wan2.2-i2v-high-oral-insertion-v1.0.safetensors", 0.55),
    ("CloseUpFacialCum-v10_High.safetensors", 1.0),
    ("wan22-k3nk4llinon3-16epoc-full-high-k3nk.safetensors", 0.55),
]
LOW_LORAS = [
    ("wan2.2-i2v-low-oral-insertion-v1.0.safetensors", 0.55),
    ("CloseUpFacialCum-v10_Low.safetensors", 1.0),
    ("wan22-k3nk4llinon3-15epoc-full-low-k3nk.safetensors", 0.55),
]

CUM_CORE = "cum shot, cum, sticky cum, "

BEATS = [
    {
        "seed": 301,
        "prefix": "studio_agent_wan22_sq25_oralcream",
        "prompt": (
            "k3nk4llin0n3, A man appears and she sucks his penis, "
            + CUM_CORE
            + "oral creampie, she holds still with only the tip of the thick erect penis "
            "in her lips, he cums in her mouth, sticky cum fills her mouth, "
            "cum spurts from penis into her mouth, cum on tongue, "
            "lips sealed on the tip, anime style, same purple hair face, no camera jump"
        ),
        "negative": (
            "pulling fully out, empty mouth, no cum, dry mouth, clear saliva only, "
            "deflating penis, disappearing shaft, chewing, photoreal, identity change, "
            "morphing face, splash from above, drench"
        ),
    },
    {
        "seed": 302,
        "prefix": "studio_agent_wan22_sq25_facial",
        "prompt": (
            "k3nk4llin0n3, "
            + CUM_CORE
            + "Facial, money shot, she pulls the thick erect penis fully out of her mouth, "
            "penis withdraws from lips still solid constant girth, "
            "cum shoots from penis onto her face, cum on face, cum on tongue, "
            "sticky cum, woman mouth is open, woman tongue is extended, "
            "multiple thick slimy cum shots, anime style, same purple hair face"
        ),
        "negative": (
            "staying inserted, oral creampie only, empty finish, no cum, "
            "deflating penis, disappearing shaft, photoreal, identity change, "
            "morphing face, splash from above, drench"
        ),
    },
]


def _build_with_loras(**kwargs):
    # Monkeypatch LoRA lists on the shared module for this run
    _wan22.HIGH_LORAS = HIGH_LORAS
    _wan22.LOW_LORAS = LOW_LORAS
    return build_api(**kwargs)


def main() -> None:
    if not SEED_CLIP.is_file():
        raise FileNotFoundError(SEED_CLIP)
    if not BOBBING.is_file():
        raise FileNotFoundError(BOBBING)

    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)

    # Confirm facial LoRAs visible
    import requests

    opts = requests.get(
        f"{eng.comfy.base_url}/object_info/LoraLoaderModelOnly", timeout=30
    ).json()["LoraLoaderModelOnly"]["input"]["required"]["lora_name"][0]
    for need in ("CloseUpFacialCum-v10_High.safetensors", "CloseUpFacialCum-v10_Low.safetensors"):
        if need not in opts:
            raise RuntimeError(f"ComfyUI cannot see {need} yet — refresh model list / restart Comfy")

    working_parts = []
    # Start climax from almost-out money last frame
    last = IMPORT_DIR / "close_up_sq25_almost_out.png"
    extract_last_frame(SEED_CLIP, last)
    current_image = last
    climax_clips = []

    for i, beat in enumerate(BEATS):
        print(f"CLIMAX-CUM beat {i+1}/2 seed={beat['seed']}", flush=True)
        uploaded = eng.comfy.upload_image(current_image)
        api = _build_with_loras(
            image_name=uploaded,
            prompt=beat["prompt"],
            negative=beat["negative"],
            width=SIZE,
            height=SIZE,
            length=49,
            steps=20,
            switch_step=10,
            cfg=4.0,  # facial-cum author: bump CFG for thicker cum
            seed=beat["seed"],
        )
        api["70"]["inputs"]["filename_prefix"] = beat["prefix"]
        prompt_id = eng.comfy.queue_prompt(api)
        history = eng.comfy.wait_for_completion(prompt_id)
        outputs = eng.comfy.collect_outputs(history)
        saved = eng._save_comfy_outputs(outputs, extensions=(".mp4", ".webm", ".gif", ".png"))
        if not saved:
            raise RuntimeError(f"No video for beat {i+1}")
        cont = Path(saved[0])
        climax_clips.append(cont)
        # next beat continues from this segment's last frame
        nxt = IMPORT_DIR / f"close_up_sq25_cum_last_{i}.png"
        extract_last_frame(cont, nxt)
        current_image = nxt
        print(f"OK beat {i+1} → {cont.name}", flush=True)

    # Bobbing + new climax
    joined = VIDEO_DIR / "studio_agent_wan22_sq_25s_cum_build.mp4"
    concat_videos([BOBBING, *climax_clips], joined)
    FINAL.write_bytes(joined.read_bytes())
    result = {
        "ok": True,
        "seed_clip": str(SEED_CLIP),
        "seed_frame": str(last),
        "bobbing": str(BOBBING),
        "climax_clips": [str(c) for c in climax_clips],
        "final": str(FINAL),
        "duration_sec": probe_video(FINAL)["duration_sec"],
        "loras_high": HIGH_LORAS,
        "note": "oral creampie then Facial; CloseUpFacialCum @1.0; triggers included",
    }
    (ROOT / "outputs" / "bj_climax_cum_fix.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("OK", json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
