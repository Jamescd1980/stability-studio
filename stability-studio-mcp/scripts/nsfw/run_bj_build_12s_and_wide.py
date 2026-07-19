# -*- coding: utf-8 -*-
"""Build ~12s close-up via last-frame chaining, then re-run fixed wide-angle."""
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
CLOSE_SEED = VIDEO_DIR / "studio_agent_wan22_sq_00001.mp4"
TARGET_SEC = 12.0
SIZE = 720

NEG_CLOSE = (
    "pulling away, pulling back, withdrawing, backing off, chewing, biting, "
    "deflating penis, shrinking penis, disappearing shaft, vanishing tip, "
    "melting genitals, empty mouth, tip missing, hose, metal object, "
    "clipping through lip, penis through face, deformed hands, mutated hands, "
    "photoreal, identity change, morphing face, flicker, warped anatomy"
)

NEG_WIDE = (
    NEG_CLOSE
    + ", hand clipping, bad hands, extra fingers, fused fingers, "
    "penis clipping through bottom lip, mesh intersection"
)

CLOSE_BEATS = [
    (
        101,
        "she continues the blowjob from this exact pose, head moves down the shaft "
        "taking him deeper, rhythmic bobbing, oral insertion, lips sealed around "
        "thick erect penis with constant girth, anime style, same purple hair face room",
    ),
    (
        102,
        "she keeps sucking, steady rhythmic head bob down the shaft then slightly up, "
        "oral insertion, lips sealed no gaps, thick erect penis stays solid constant girth, "
        "anime style, hold purple hair face and framing",
    ),
    (
        103,
        "she continues the blowjob with confident bobbing, deeper on the downstroke, "
        "oral insertion, lips wrap cleanly around shaft, thick erect penis solid, "
        "anime style, same purple hair face, no camera jump",
    ),
]

WIDE_PROMPT = (
    "she is giving him a blowjob, head goes down the shaft taking him deeper, "
    "oral insertion, rhythmic bobbing downward not away, "
    "lips wrap cleanly around the shaft with no clipping through the lip, "
    "thick erect penis remains solid with constant girth, "
    "if a hand is visible it is natural and correctly drawn, "
    "anime style, hold purple ponytail bodies and room"
)


def _engine() -> GenerationEngine:
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)
    return eng


def _gen_segment(
    eng: GenerationEngine,
    *,
    image: Path,
    prompt: str,
    negative: str,
    seed: int,
    prefix: str,
) -> Path:
    uploaded = eng.comfy.upload_image(image)
    api = build_api(
        image_name=uploaded,
        prompt=prompt,
        negative=negative,
        width=SIZE,
        height=SIZE,
        length=49,
        steps=20,
        switch_step=10,
        cfg=3.5,
        seed=seed,
    )
    api["70"]["inputs"]["filename_prefix"] = prefix
    prompt_id = eng.comfy.queue_prompt(api)
    history = eng.comfy.wait_for_completion(prompt_id)
    outputs = eng.comfy.collect_outputs(history)
    saved = eng._save_comfy_outputs(outputs, extensions=(".mp4", ".webm", ".gif", ".png"))
    if not saved:
        raise RuntimeError(f"No video saved for seed={seed} prefix={prefix}")
    return Path(saved[0])


def build_close_12s(eng: GenerationEngine) -> dict:
    if not CLOSE_SEED.is_file():
        raise FileNotFoundError(CLOSE_SEED)

    segments = [CLOSE_SEED]
    working = CLOSE_SEED
    log = []

    while probe_video(working)["duration_sec"] < TARGET_SEC:
        beat_i = len(segments) - 1
        if beat_i >= len(CLOSE_BEATS):
            seed, prompt = CLOSE_BEATS[-1]
            seed = seed + beat_i
        else:
            seed, prompt = CLOSE_BEATS[beat_i]

        last = IMPORT_DIR / f"close_up_sq_chain_last_{beat_i}.png"
        extract_last_frame(working, last)
        print(
            f"CLOSE beat {beat_i + 1}: last-frame → L2V seed={seed} "
            f"(current {probe_video(working)['duration_sec']:.2f}s)",
            flush=True,
        )
        cont = _gen_segment(
            eng,
            image=last,
            prompt=prompt,
            negative=NEG_CLOSE,
            seed=seed,
            prefix=f"studio_agent_wan22_sq_ext{beat_i + 1}",
        )
        joined = VIDEO_DIR / f"studio_agent_wan22_sq_build_{beat_i + 1}.mp4"
        concat_videos([working, cont], joined)
        segments.append(cont)
        working = joined
        info = probe_video(working)
        entry = {
            "beat": beat_i + 1,
            "seed": seed,
            "continuation": str(cont),
            "joined": str(joined),
            "duration_sec": info["duration_sec"],
            "last_frame": str(last),
        }
        log.append(entry)
        print(f"CLOSE joined → {joined.name} ({info['duration_sec']:.2f}s)", flush=True)

    final = VIDEO_DIR / "studio_agent_wan22_sq_12s.mp4"
    if working.resolve() != final.resolve():
        final.write_bytes(working.read_bytes())
    result = {
        "ok": True,
        "final": str(final),
        "duration_sec": probe_video(final)["duration_sec"],
        "segments": [str(s) for s in segments],
        "beats": log,
    }
    (ROOT / "outputs" / "bj_close_12s.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def fix_wide(eng: GenerationEngine) -> dict:
    src = IMPORT_DIR / "wide_angle_bj.png"
    print("WIDE fix: square 720 + lip/hand lock", flush=True)
    # Slightly softer deepthroat on wide by using lower helper stack via prompt emphasis;
    # keep same LoRA stack but stronger anti-clip negatives.
    out = _gen_segment(
        eng,
        image=src,
        prompt=WIDE_PROMPT,
        negative=NEG_WIDE,
        seed=55,
        prefix="studio_agent_wan22_widefix",
    )
    result = {
        "ok": True,
        "saved": str(out),
        "size": f"{SIZE}x{SIZE}",
        "note": "square + anti lip-clip / hand deform negatives",
    }
    (ROOT / "outputs" / "bj_wide_fix.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def main() -> None:
    eng = _engine()
    close = build_close_12s(eng)
    print("CLOSE DONE", json.dumps(close, indent=2), flush=True)
    wide = fix_wide(eng)
    print("WIDE DONE", json.dumps(wide, indent=2), flush=True)
    summary = {"close": close, "wide": wide}
    (ROOT / "outputs" / "bj_build_12s_and_wide.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    sys.exit(0 if close.get("ok") and wide.get("ok") else 1)


if __name__ == "__main__":
    main()
