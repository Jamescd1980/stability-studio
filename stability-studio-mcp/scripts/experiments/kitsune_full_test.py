#!/usr/bin/env python3
"""Full kitsune pipeline test: T2I → I2I → T2V → I2V (hero) → V2V (curtsy) → 8s final."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
from _bootstrap import ROOT, load_engine  # noqa: E402
from studio.video_utils import concat_videos, probe_video

OUT = ROOT / "outputs" / "kitsune_park"
REF = OUT / "reference.png"
DEFAULT_HERO = OUT / "hero.png"

CHAR = (
    "1girl, kitsune fox girl, multiple fluffy white fox tails, silver white hair, blunt bangs, "
    "sharp red eyes, dark navy military peaked cap with gold sakura emblem, large red bow, "
    "cherry blossom print uniform, consistent character design"
)

T2I_PROMPT = (
    f"{CHAR}, standing on paved path in Japanese park, cherry blossom trees blooming, "
    "medium close-up, soft spring daylight, anime illustration, masterpiece"
)
I2I_PROMPT = (
    f"{CHAR}, Japanese park path, sakura trees, close-up medium shot, walking pose, "
    "soft spring light, anime illustration, masterpiece"
)
T2V_PROMPT = (
    f"{CHAR}, cherry blossom park path, gentle breeze, petals falling, cinematic anime, smooth camera pan"
)
I2V_PROMPT = (
    f"same {CHAR}, skipping forward along sakura park path, legs stepping, arms swinging, "
    "medium close-up camera tracking, white tails flowing, fluid body motion, spring daylight"
)
V2V_PROMPT = (
    f"same {CHAR}, curtsying politely while smiling warmly at camera, cherry blossom park, "
    "close-up portrait, graceful bow, same outfit and face, smooth natural motion"
)

NEG_IMG = "lowres, bad anatomy, bad hands, text, watermark, poster background, propaganda"
NEG_VID = (
    "static, frozen, still image, blurry, deformed, bad anatomy, jittery, morphing face, "
    "different character, outfit change, hair color change, extra limbs"
)

SEG_FRAMES = 49
SEG_FPS = 16.0
MOTION_AMPLITUDE = 1.2
T2V_FRAMES = 33
T2V_FPS = 16.0


def save_result(result: dict, dest: Path) -> Path:
    saved = result.get("saved_files") or []
    if not saved:
        raise RuntimeError(json.dumps(result, indent=2))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(saved[0], dest)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Kitsune full pipeline test")
    parser.add_argument(
        "--from-step",
        choices=["t2i", "i2i", "t2v", "i2v", "v2v"],
        default="t2i",
        help="Resume from this step (skips earlier steps)",
    )
    parser.add_argument(
        "--hero",
        default="",
        help="Hero still for I2V (default: outputs/kitsune_park/hero.png)",
    )
    args = parser.parse_args()
    hero = Path(args.hero) if args.hero else DEFAULT_HERO
    order = ["t2i", "i2i", "t2v", "i2v", "v2v"]
    start_idx = order.index(args.from_step)

    if not hero.is_file():
        print(f"Missing main character still: {hero}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hero, OUT / "hero_main.png")

    cfg, cat, eng = load_engine()
    if not eng.comfy.is_running():
        print("ComfyUI is not running. Launch from Stability Matrix first.", file=sys.stderr)
        return 1

    results: dict[str, str] = {"hero_main": str(hero)}

    if start_idx <= 0:
        print("\n=== T2I (ilustmix) ===", flush=True)
        dest = OUT / "01_t2i.png"
        save_result(
            eng.generate_image(
                prompt=T2I_PROMPT,
                style="ilustmix",
                negative_prompt=NEG_IMG,
                width=832,
                height=1216,
            ),
            dest,
        )
        results["t2i"] = str(dest)
        print(f"  -> {dest}", flush=True)

    if start_idx <= 1:
        if not REF.is_file():
            print(f"Missing reference: {REF}", file=sys.stderr)
            return 1
        print("\n=== I2I (reference to park) ===", flush=True)
        dest = OUT / "02_i2i.png"
        save_result(
            eng.generate_image_i2i(
                image_path=str(REF),
                prompt=I2I_PROMPT,
                style="ilustmix",
                negative_prompt=NEG_IMG,
                width=832,
                height=1216,
                denoising_strength=0.52,
                steps=28,
            ),
            dest,
        )
        results["i2i"] = str(dest)
        print(f"  -> {dest}", flush=True)

    if start_idx <= 2:
        print("\n=== T2V (smoke test) ===", flush=True)
        dest = OUT / "03_t2v.mp4"
        save_result(
            eng.generate_video(
                prompt=T2V_PROMPT,
                mode="t2v",
                workflow_id="t2v",
                style="ilustmix",
                negative_prompt=NEG_VID,
                num_frames=T2V_FRAMES,
                frame_rate=T2V_FPS,
            ),
            dest,
        )
        results["t2v"] = str(dest)
        print(f"  -> {dest}", flush=True)

    if start_idx <= 3:
        print(f"\n=== I2V ({hero.name} - park walk) ===", flush=True)
        dest = OUT / "04_i2v_park.mp4"
        save_result(
            eng.generate_video(
                prompt=I2V_PROMPT,
                mode="i2v",
                image_path=str(hero),
                style="ilustmix",
                negative_prompt=NEG_VID,
                workflow_id="i2v_5b_painter",
                use_painter_i2v=True,
                motion_amplitude=MOTION_AMPLITUDE,
                smooth_motion=False,
                num_frames=SEG_FRAMES,
                frame_rate=SEG_FPS,
                concat_source=False,
            ),
            dest,
        )
        results["i2v"] = str(dest)
        info = probe_video(dest)
        print(f"  -> {dest} ({info['duration_sec']:.2f}s)", flush=True)
    else:
        i2v = OUT / "04_i2v_park.mp4"
        if not i2v.is_file():
            print(f"Missing {i2v}", file=sys.stderr)
            return 1

    i2v = OUT / "04_i2v_park.mp4"

    if start_idx <= 4:
        print("\n=== V2V (curtsy + smile) ===", flush=True)
        dest = OUT / "05_v2v_curtsy.mp4"
        save_result(
            eng.generate_video(
                prompt=V2V_PROMPT,
                mode="v2v",
                video_path=str(i2v),
                style="ilustmix",
                negative_prompt=NEG_VID,
                workflow_id="v2v_5b_painter",
                use_painter_i2v=True,
                motion_amplitude=1.15,
                smooth_motion=False,
                num_frames=SEG_FRAMES,
                frame_rate=SEG_FPS,
                concat_source=False,
            ),
            dest,
        )
        results["v2v"] = str(dest)
        info = probe_video(dest)
        print(f"  -> {dest} ({info['duration_sec']:.2f}s)", flush=True)

    v2v = OUT / "05_v2v_curtsy.mp4"
    final = OUT / "kitsune_8s.mp4"
    concat_videos([i2v, v2v], final)
    finfo = probe_video(final)

    meta = {
        "run": datetime.now(timezone.utc).isoformat(),
        "pipeline": ["t2i", "i2i", "t2v", "i2v", "v2v", "concat"],
        "hero_main": str(hero),
        "character_lock": CHAR,
        "duration_target_sec": 8,
        "segment_frames": SEG_FRAMES,
        "segment_fps": SEG_FPS,
        "v2v_motion": "curtsy while smiling at camera",
        "outputs": results,
        "clips": [str(i2v), str(v2v)],
        "final": str(final),
        "duration_sec": finfo["duration_sec"],
        "motion_amplitude_i2v": MOTION_AMPLITUDE,
        "motion_amplitude_v2v": 1.15,
        "smooth_motion": False,
        "note": f"I2V from {hero.name}, V2V curtsy; motion_amplitude 1.2/1.15, {SEG_FRAMES}f @ {SEG_FPS}fps. Bow preset: outputs/kitsune_bow_video_test.json",
    }
    (OUT / "pipeline_result.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log_lines = [
        f"# Kitsune park run — {meta['run']}",
        "",
        f"Hero: {meta['hero_main']}",
        f"Final: {meta['final']} ({meta['duration_sec']:.2f}s)",
        f"I2V: {meta['outputs'].get('i2v', 'n/a')} — amplitude {meta['motion_amplitude_i2v']}",
        f"V2V: {meta['outputs'].get('v2v', 'n/a')} — amplitude {meta['motion_amplitude_v2v']}",
        f"smooth_motion: {meta['smooth_motion']}",
        f"Note: {meta['note']}",
        "",
        json.dumps(meta, indent=2),
    ]
    (OUT / "full_test.log").write_text("\n".join(log_lines), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr, flush=True)
        raise
