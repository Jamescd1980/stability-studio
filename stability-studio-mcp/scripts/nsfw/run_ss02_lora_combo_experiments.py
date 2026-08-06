"""SS02 LoRA combo experiments — quality MoE, one try per invocation (max 4).

Usage:
  py -3 run_ss02_lora_combo_experiments.py 1   # LC01 asymmetric Missionary Sex
  py -3 run_ss02_lora_combo_experiments.py 2   # LC02 general NSFW-22 motion pair
  py -3 run_ss02_lora_combo_experiments.py 3   # LC03 dtwr434 POV Missionary pair
  py -3 run_ss02_lora_combo_experiments.py 4   # LC04 Missionary Sex + PENISLORA stack
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
DIAG_ROOT = ROOT / "outputs" / "saloon_diag_frames" / "ss02_lora_combo"

NEG_THRUST = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, shifting grip, squeezing thighs, extra hands, four hands, "
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

PLAYTIME_PROMPT = (
    "nsfw, A naked man and a naked woman having sex. "
    "He thrusts his penis in and out of her vagina. a pov shot. "
    "partial withdraw only, cock stays inside, vaginal penetration, "
    "hands stay gripping thighs, steady view"
)

DTWR434_PROMPT = (
    "nsfw, with her legs spread having sex with a man, a pov shot. "
    "A man is thrusting his penis back and forth inside her vagina at the bottom of the screen. "
    "partial withdraw only, cock stays inside, vaginal penetration, steady view"
)

NSFW22_PROMPT = (
    "nsfw, nsfwsks, A naked man and a naked woman having sex. "
    "He thrusts his penis in and out of her vagina. a pov shot. "
    "partial withdraw only, cock stays inside, vaginal penetration, steady view"
)

TRIES: dict[int, dict] = {
    1: {
        "id": "SS02_LC01",
        "hypothesis": (
            "T2 borderline: symmetric 0.85 + amp 0.28 too weak. "
            "Cook/community asymmetric High 0.35 / Low 1.0 + amp 0.36 for stronger axial motion without T1 exit."
        ),
        "image": PACK / "SS02.png",
        "prompt": PLAYTIME_PROMPT,
        "neg": NEG_THRUST,
        "loras": [
            {
                "id": "missionary_sex_high",
                "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
                "weight": 0.35,
                "branch": "high",
            },
            {
                "id": "missionary_sex_low",
                "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
                "weight": 1.0,
                "branch": "low",
            },
        ],
        "amp": 0.36,
        "frames": 41,
    },
    2: {
        "id": "SS02_LC02",
        "hypothesis": (
            "General NSFW-22 motion pair (not tried on SS02) may add axial drive "
            "without playtime Sex LoRA at 1.0 exit risk."
        ),
        "image": PACK / "SS02.png",
        "prompt": NSFW22_PROMPT,
        "neg": NEG_THRUST,
        "loras": [
            {
                "id": "general_nsfw_high",
                "file": "NSFW-22-H-e8.safetensors",
                "weight": 0.45,
                "branch": "high",
            },
            {
                "id": "general_nsfw_low",
                "file": "NSFW-22-L-e8.safetensors",
                "weight": 0.5,
                "branch": "low",
            },
        ],
        "amp": 0.35,
        "frames": 41,
    },
    3: {
        "id": "SS02_LC03",
        "hypothesis": (
            "dtwr434 POV Missionary (alternate pair) with creator bottom-of-screen thrust triggers — "
            "different training than playtime Missionary Sex."
        ),
        "image": PACK / "SS02.png",
        "prompt": DTWR434_PROMPT,
        "neg": NEG_THRUST,
        "loras": [
            {
                "id": "dtwr434_pov_missionary_high",
                "file": "wan2.2_i2v_highnoise_pov_missionary_v1.0.safetensors",
                "weight": 0.85,
                "branch": "high",
            },
            {
                "id": "dtwr434_pov_missionary_low",
                "file": "wan2.2_i2v_lownoise_pov_missionary_v1.0.safetensors",
                "weight": 0.85,
                "branch": "low",
            },
        ],
        "amp": 0.32,
        "frames": 41,
    },
    4: {
        "id": "SS02_LC04",
        "hypothesis": (
            "Missionary Sex asymmetric High 1.0 / Low 0.55 + light PENISLORA stack — "
            "shaft rigidity may allow stronger motion without T1 full exit or T2 subtle drift."
        ),
        "image": PACK / "SS02.png",
        "prompt": PLAYTIME_PROMPT,
        "neg": NEG_THRUST,
        "loras": [
            {
                "id": "missionary_sex_high",
                "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
                "weight": 1.0,
                "branch": "high",
            },
            {
                "id": "missionary_sex_low",
                "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
                "weight": 0.55,
                "branch": "low",
            },
            {
                "id": "penis_i2v_high",
                "file": "PENISLORA_wan22_i2v_high.safetensors",
                "weight": 0.45,
                "branch": "high",
            },
            {
                "id": "penis_i2v_low",
                "file": "PENISLORA_wan22_i2v_low.safetensors",
                "weight": 0.45,
                "branch": "low",
            },
        ],
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

    print(f"===== I2V {beat['id']} quality amp={beat['amp']} frames={beat['frames']} =====", flush=True)
    print("hypothesis:", beat.get("hypothesis", ""), flush=True)
    print("image", start, flush=True)

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
    }
    out_json = ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_ss02_lora_combo_experiments.py <1|2|3|4>", flush=True)
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
