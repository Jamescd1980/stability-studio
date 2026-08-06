# -*- coding: utf-8 -*-
"""SS04_001 / SS04_002 quality MoE I2V — lean cum drip + fingers/thumb, FacialCum @0.40."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "general"))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio import engine as engine_mod  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402
from recycle_path import recycle  # noqa: E402

OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon")
DIAG_ROOT = Path(r"D:\Bad boy\outputs\saloon_diag_frames\ss04_001_002")
NOTES_JSON = Path(r"D:\studio-agent\stability-studio-mcp\outputs")

FACIAL_CUM_040 = [
    {
        "id": "facial_cum_high",
        "file": "CloseUpFacialCum-v10_High.safetensors",
        "weight": 0.40,
        "branch": "high",
    },
    {
        "id": "facial_cum_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 0.40,
        "branch": "low",
    },
]

BEATS = {
    "SS04_001_v1": {
        "image": OUT_DIR / "001.png",
        "prompt": (
            "nsfw, sticky cum, semen, cumshot, "
            "cum dripping onto her face, "
            "two fingers working into her ass"
        ),
        "neg": "honey, water, transparent",
        "amp": 0.43,
        "frames": 64,
    },
    "SS04_002_v1": {
        "image": OUT_DIR / "002.png",
        "prompt": (
            "nsfw, sticky cum, semen, cumshot, lots of cum, "
            "cum dripping onto her face, "
            "thumb working into her ass"
        ),
        "neg": "honey, water, transparent",
        "amp": 0.43,
        "frames": 64,
    },
    # v2: lower amp vs genital melt; hero motions = drip + fingers/thumb + swallow;
    # penis twitch only; soft face lock (no head-turn verbs).
    "SS04_001_v2": {
        "image": OUT_DIR / "001.png",
        "prompt": (
            "nsfw, sticky cum, cumshot, "
            "cum dripping onto her face, "
            "two fingers working into her ass, "
            "she swallows, penis twitches slightly, face nearly still"
        ),
        "neg": "deformed balls, melting penis, morphing genitals, turning head, honey, water",
        "amp": 0.40,
        "frames": 64,
    },
    "SS04_002_v2": {
        "image": OUT_DIR / "002.png",
        "prompt": (
            "nsfw, sticky cum, cumshot, "
            "cum dripping onto her face, "
            "thumb working into her ass, "
            "she swallows, penis twitches slightly, face nearly still"
        ),
        "neg": "deformed balls, melting penis, morphing genitals, turning head, honey, water",
        "amp": 0.40,
        "frames": 64,
    },
    # v3: v1 stack + nipple lock; finger motion hero; penis twitch only (no swallow/head).
    "SS04_001_v3": {
        "image": OUT_DIR / "001.png",
        "prompt": (
            "nsfw, sticky cum, cumshot, "
            "cum dripping onto her face, "
            "two fingers working into her ass, "
            "penis twitches slightly"
        ),
        "neg": "deformed balls, melting penis, moving nipples, bouncing breasts",
        "amp": 0.40,
        "frames": 64,
    },
    # v3: lean drip + thumb penetrate + mouth open; no swallow/twitch/head essays.
    "SS04_002_v3": {
        "image": OUT_DIR / "002.png",
        "prompt": (
            "nsfw, sticky cum, cumshot, "
            "cum dripping onto her face, "
            "thumb pushing into her ass, "
            "mouth open"
        ),
        "neg": "deformed balls, melting penis, closed mouth, honey, water",
        "amp": 0.41,
        "frames": 64,
    },
}


def extract_frames(video: Path, diag_dir: Path, fps: float = 16.0) -> dict[str, Path]:
    diag_dir.mkdir(parents=True, exist_ok=True)
    try:
        dur = float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(video),
                ],
                text=True,
            ).strip()
        )
    except Exception:
        dur = 64 / fps
    probes = {"f0": 0.0, "mid": dur / 2, "last": max(0.0, dur - (1 / fps))}
    out: dict[str, Path] = {}
    for label, t in probes.items():
        dest = diag_dir / f"{video.stem}_{label}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{t:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(dest),
            ],
            capture_output=True,
            check=False,
        )
        if dest.is_file():
            out[label] = dest
    return out


def run_one(engine: GenerationEngine, beat_id: str) -> dict:
    beat = BEATS[beat_id]
    start = Path(beat["image"])
    dest = OUT_DIR / f"{beat_id}.mp4"
    if not start.is_file():
        return {"ok": False, "id": beat_id, "error": f"missing {start}"}

    print(f"===== {beat_id} quality amp={beat['amp']} frames={beat['frames']} =====", flush=True)
    print("image", start, flush=True)
    print("prompt:", beat["prompt"], flush=True)
    print("neg:", beat["neg"], flush=True)

    prev = engine_mod.ANATOMY_NEGATIVE_HINT
    engine_mod.ANATOMY_NEGATIVE_HINT = ""
    try:
        result = engine.generate_video(
            prompt=beat["prompt"],
            mode="i2v",
            negative_prompt=beat["neg"],
            workflow_id="i2v",
            content_rating="open",
            image_path=str(start),
            num_frames=int(beat["frames"]),
            frame_rate=16.0,
            loras=FACIAL_CUM_040,
            moe_preset="quality",
            smooth_motion=False,
            motion_amplitude=float(beat["amp"]),
        )
    finally:
        engine_mod.ANATOMY_NEGATIVE_HINT = prev

    saved = result.get("saved_files") or []
    if isinstance(saved, str):
        saved = [saved]

    promoted = None
    for p in saved:
        src = Path(str(p))
        if src.is_file() and src.suffix.lower() == ".mp4":
            if dest.is_file():
                recycle(dest)
            shutil.move(str(src), str(dest))
            promoted = dest
            break

    frames: dict[str, str] = {}
    if promoted:
        extracted = extract_frames(promoted, DIAG_ROOT / beat_id)
        frames = {k: str(v) for k, v in extracted.items()}

    summary = {
        "ok": bool(promoted),
        "id": beat_id,
        "image": str(start),
        "path": str(promoted) if promoted else None,
        "preset": (result.get("moe") or {}).get("preset"),
        "motion_amplitude": beat["amp"],
        "frames": beat["frames"],
        "prompt": beat["prompt"],
        "negative": beat["neg"],
        "loras": FACIAL_CUM_040,
        "diag_frames": frames,
        "raw_ok": result.get("ok"),
        "error": result.get("error") or result.get("message"),
    }
    NOTES_JSON.mkdir(parents=True, exist_ok=True)
    (NOTES_JSON / f"{beat_id}_i2v.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    ids = list(BEATS) if which == "both" else [which]
    for beat_id in ids:
        if beat_id not in BEATS:
            print("unknown", beat_id, file=sys.stderr)
            return 2
        summary = run_one(engine, beat_id)
        if not summary.get("ok"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
