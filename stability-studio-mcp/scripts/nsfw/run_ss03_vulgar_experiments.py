"""SS03 vulgar-prompt experiments — quality MoE Doggy Sex, one try per invocation.

Usage:
  py -3 run_ss03_vulgar_experiments.py 1   # T1 vulgar fuck/thrust, amp 0.35, 41f
  py -3 run_ss03_vulgar_experiments.py 2   # T2 pound/cunt variant, amp 0.38, 33f
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
DIAG_ROOT = ROOT / "outputs" / "saloon_diag_frames" / "ss03_vulgar"

# No hip-shake / hip-wiggle block — doggy needs axial hip motion.
NEG_DOGGY = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, shifting grip, extra hands, four hands, "
    "side to side, lateral sway, swinging sideways, left right wobble, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, shifting labia, jumping genitals, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

DOGGY_SEX_LORAS = [
    {
        "id": "doggy_sex_high",
        "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "weight": 0.85,
        "branch": "high",
    },
    {
        "id": "doggy_sex_low",
        "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "weight": 0.85,
        "branch": "low",
    },
]

TRIES: dict[int, dict] = {
    1: {
        "id": "SS03_vulgar_T1",
        "hypothesis": (
            "Prior SS03 used mild cock/pussy/thrust tags, not house-style vulgar act "
            "sentences. T1: Doggy Sex 0.85/0.85 + explicit fuck/thrust/sliding, amp 0.35, 41f."
        ),
        "image": PACK / "SS03.png",
        "prompt": (
            "nsfw, they are having doggy style sex, "
            "he fucks her pussy from behind, thrusting his hips forward and back, "
            "sliding his cock in and out of her wet pussy, cock stays inside, "
            "partial withdraw only, vaginal penetration, steady view"
        ),
        "neg": NEG_DOGGY,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.35,
        "frames": 41,
    },
    2: {
        "id": "SS03_vulgar_T2",
        "hypothesis": (
            "T1 failed frame-gate: different vulgar angle — short hard thrusts / "
            "cock buried / fucking her pussy, Doggy Sex 0.85/0.85, amp 0.38, 33f."
        ),
        "image": PACK / "SS03.png",
        "prompt": (
            "nsfw, doggystyle, he pounds her pussy from behind with short hard thrusts, "
            "cock buried in her cunt, fucking her in her pussy, stays inside, "
            "partial withdraw only, steady view"
        ),
        "neg": NEG_DOGGY,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.38,
        "frames": 33,
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
    if len(sys.argv) < 2:
        print("usage: run_ss03_vulgar_experiments.py <1|2>", flush=True)
        return 2

    try_num = int(sys.argv[1])
    if try_num not in TRIES:
        print(f"unknown try {try_num}", flush=True)
        return 2

    beat = TRIES[try_num]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    summary = run_try(engine, beat)
    print("DONE", ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json", flush=True)
    return 0 if summary.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
