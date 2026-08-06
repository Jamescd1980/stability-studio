"""SS03-3 from-below doggy quality MoE — cock in-out (COCK_R1 stack).

Same keeper stack as SS03_1_v2_T1 / SS03_2_cock_R1:
  - Doggy Sex HIGH+LOW @ 1.0/1.0, 41f, quality (no Lightning)
  - MCP cannot pass Doggy action pair — use this Python engine path
  - Amp 0.38; hand/thumb stay; length-morph negs; partial withdraw only

Usage:
  py -3 run_ss03_3_from_below.py V2_T1
  py -3 run_ss03_3_from_below.py V2_T2
  py -3 run_ss03_3_from_below.py EXT_A1
  py -3 run_ss03_3_from_below.py EXT_B1
"""

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
from studio.engine import GenerationEngine  # noqa: E402

from recycle_path import recycle  # noqa: E402

PACK = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\scene_packs\Frieren Saloon"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon")
DIAG_ROOT = ROOT / "outputs" / "saloon_diag_frames" / "ss03_3_below"

# Cock travel: kill length-morph illusion + hand/thumb motion; keep exit/melt block.
NEG_COCK_TRAVEL = (
    "fast motion, violent slam, jerky motion, "
    "moving hand, hand pulling away, thumb pulling out, shifting grip, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, extra hands, four hands, "
    "thumb leaving, finger pulling out, empty asshole, hand leaving ass, "
    "thumb out, finger exit, thumb withdrawing, thumb sliding out, "
    "thumb shoving deeper, finger pushing in, "
    "changing penis length, stretching penis, elongating shaft, shrinking penis, "
    "morphing penis, rubber penis, melting shaft, "
    "deflating penis, disappearing shaft, blob penis, "
    "camera pan, camera drift, sliding out of frame, character drifting, "
    "frame slide, background sliding, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

# EXT_B1: same + jumping/twitching penis (last-try from shallower pre-deep still).
NEG_COCK_TRAVEL_JUMP = (
    NEG_COCK_TRAVEL
    + ", jumping penis, twitching penis, bouncing shaft, sudden twitch, "
    "penis length change, shaft melting"
)

DOGGY_SEX_LORAS = [
    {
        "id": "doggy_sex_high",
        "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "high",
    },
    {
        "id": "doggy_sex_low",
        "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "low",
    },
]

BEATS = {
    "V2_T1": {
        "id": "SS03_3_v2_T1",
        "hypothesis": (
            "SS03-3.png from-below jack-o doggy (face toward viewer). Same stack as "
            "SS03_2_cock_R1 (Doggy Sex 1.0/1.0, amp 0.38, 41f quality). One verb: "
            "cock thrusting in and out; hand/thumb stay; length-morph + exit negs."
        ),
        "image": PACK / "SS03-3.png",
        "prompt": (
            "nsfw, from below, doggystyle, "
            "his cock thrusting in and out of her pussy, "
            "hip thrust driving the shaft, partial withdraw only, "
            "vaginal penetration, hand and thumb stay in place on her ass, "
            "steady grip, steady view"
        ),
        "neg": NEG_COCK_TRAVEL,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.38,
        "frames": 41,
    },
    "V2_T2": {
        "id": "SS03_3_v2_T2",
        "hypothesis": (
            "SS03-3.png from-below jack-o. T1 kept (thrust in-out). T2 = deeper "
            "penetration try: one verb family shove/bury cock deep. Same Doggy Sex "
            "1.0/1.0, amp 0.40, 41f quality. Hand/thumb stay; length-morph + exit negs."
        ),
        "image": PACK / "SS03-3.png",
        "prompt": (
            "nsfw, from below, doggystyle, "
            "he shoves his cock deep into her pussy, deep penetration, "
            "partial withdraw only, vaginal penetration, "
            "hand and thumb stay in place on her ass, steady grip, steady view"
        ),
        "neg": NEG_COCK_TRAVEL,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.40,
        "frames": 41,
    },
    "EXT_A1": {
        "id": "SS03_3_v2_T1_ext_A1",
        "hypothesis": (
            "Chain from T1 max-insert still @ 1.5625s (f25). T2 rejected. "
            "Continue fucking/thrusting from deep; partial withdraw only; "
            "Doggy Sex 1.0/1.0, amp 0.38, 41f quality. Hand/thumb stay."
        ),
        "image": OUT_DIR / "SS03_3_v2_T1_maxinsert.png",
        "prompt": (
            "nsfw, from below, doggystyle, "
            "he keeps fucking her pussy from deep, slow hip thrust, "
            "partial withdraw only, vaginal penetration, "
            "hand and thumb stay in place on her ass, steady grip, steady view"
        ),
        "neg": NEG_COCK_TRAVEL,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.38,
        "frames": 41,
    },
    "EXT_B1": {
        "id": "SS03_3_v2_T1_ext_B1",
        "hypothesis": (
            "Last try: start ~0.2–0.4s BEFORE max-insert (~1.25s, shallower) so "
            "there is room to thrust in. SS03-1 hip-style prompt; Doggy Sex "
            "1.0/1.0, amp 0.30, 41f quality. Hand/thumb stay."
        ),
        "image": OUT_DIR / "SS03_3_T1_predeep.png",
        "prompt": (
            "nsfw, from below, doggystyle, "
            "he fucks her pussy from behind, thrusting his hips forward and back, "
            "shoves his cock deep into her pussy, partial withdraw only, "
            "vaginal penetration, steady view"
        ),
        "neg": NEG_COCK_TRAVEL_JUMP,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.30,
        "frames": 41,
    },
}


def extract_frames(video: Path, diag_dir: Path, fps: float = 16.0) -> dict[str, Path]:
    diag_dir.mkdir(parents=True, exist_ok=True)
    dur_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video),
    ]
    try:
        dur = float(subprocess.check_output(dur_cmd, text=True).strip())
    except Exception:
        dur = 41 / fps
    probes = {"f0": 0.0, "mid": dur / 2, "last": max(0.0, dur - (1 / fps))}
    out: dict[str, Path] = {}
    for label, t in probes.items():
        dest = diag_dir / f"{video.stem}_{label}.png"
        cmd = [
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
        ]
        subprocess.run(cmd, capture_output=True, check=False)
        if dest.is_file():
            out[label] = dest
    return out


def run_try(engine: GenerationEngine, beat: dict) -> dict:
    start = Path(beat["image"])
    dest = OUT_DIR / f"{beat['id']}.mp4"
    if not start.is_file():
        return {"ok": False, "id": beat["id"], "error": f"missing {start}"}

    print(
        f"===== I2V {beat['id']} quality amp={beat['amp']} frames={beat['frames']} =====",
        flush=True,
    )
    print("hypothesis:", beat.get("hypothesis", ""), flush=True)
    print("image", start, flush=True)
    print("prompt:", beat["prompt"], flush=True)
    print(
        "loras HIGH/LOW:",
        [(x["file"], x["weight"], x["branch"]) for x in beat["loras"]],
        flush=True,
    )

    result = engine.generate_video(
        prompt=beat["prompt"],
        mode="i2v",
        negative_prompt=beat["neg"],
        workflow_id="i2v",
        content_rating="open",
        image_path=str(start),
        num_frames=int(beat["frames"]),
        frame_rate=16.0,
        loras=beat["loras"],
        moe_preset="quality",
        smooth_motion=False,
        motion_amplitude=float(beat["amp"]),
    )

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
        diag = DIAG_ROOT / beat["id"]
        extracted = extract_frames(promoted, diag)
        frames = {k: str(v) for k, v in extracted.items()}

    summary = {
        "ok": bool(promoted),
        "id": beat["id"],
        "hypothesis": beat.get("hypothesis"),
        "image": str(start),
        "path": str(promoted) if promoted else None,
        "preset": (result.get("moe") or {}).get("preset"),
        "motion_amplitude": beat["amp"],
        "frames": beat["frames"],
        "loras": beat["loras"],
        "prompt": beat["prompt"],
        "negative": beat["neg"],
        "diag_frames": frames,
        "result_ok": result.get("ok"),
        "error": result.get("error") or result.get("message"),
    }
    out_json = ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> int:
    beat_key = sys.argv[1] if len(sys.argv) > 1 else "V2_T1"
    if beat_key not in BEATS:
        print(f"unknown beat {beat_key}; known: {list(BEATS)}", flush=True)
        return 2
    beat = BEATS[beat_key]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    summary = run_try(engine, beat)
    print("DONE", ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json", flush=True)
    return 0 if summary.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
