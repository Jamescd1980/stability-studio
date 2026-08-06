"""SS03 LoRA combo experiments — quality MoE, one try per invocation (max 3).

Usage:
  py -3 run_ss03_lora_combo_experiments.py 1   # LC01 Doggy Sex symmetric + hip in-out
  py -3 run_ss03_lora_combo_experiments.py 2   # LC02 Doggy Sex asymmetric Cook split
  py -3 run_ss03_lora_combo_experiments.py 3   # LC03 NSFW-22 + Doggy Sex stack
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
DIAG_ROOT = ROOT / "outputs" / "saloon_diag_frames" / "ss03_lora_combo"
EARLY_ROOT = ROOT / "outputs" / "saloon_diag_frames" / "ss03_lc01_early"

# No hip-shake block — doggy needs axial hip motion.
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

DOGGY_INOUT_PROMPT = (
    "nsfw, they are having doggy style sex, "
    "from behind he thrusts his cock in and out of her pussy, "
    "partial withdraw only, cock stays inside, vaginal penetration, steady view"
)

DOGGY_WITHDRAW_PROMPT = (
    "nsfw, they are having doggy style sex, "
    "from behind he slides his cock partway out then settles back in, "
    "partial withdraw only, cock stays inside, vaginal penetration, steady view"
)

DOGGY_SEX_LORAS_SYM = [
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

DOGGY_SEX_LORAS_ASYM = [
    {
        "id": "doggy_sex_high",
        "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "weight": 0.35,
        "branch": "high",
    },
    {
        "id": "doggy_sex_low",
        "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "low",
    },
]

TRIES: dict[int, dict] = {
    1: {
        "id": "SS03_LC01",
        "hypothesis": (
            "SS02 LC01 lesson: symmetric Doggy Sex 0.85/0.85 + playtime hip in-out, "
            "amp 0.32, 41f, no hip-shake negs — partial withdraw stay-inside."
        ),
        "image": PACK / "SS03.png",
        "prompt": DOGGY_INOUT_PROMPT,
        "neg": NEG_DOGGY,
        "loras": DOGGY_SEX_LORAS_SYM,
        "amp": 0.32,
        "frames": 41,
    },
    2: {
        "id": "SS03_LC02",
        "hypothesis": (
            "If T1 subtle: asymmetric High 0.35 / Low 1.0 (Cook split) + withdraw-settle "
            "prompt, amp 0.34 — motion structure on LOW branch."
        ),
        "image": PACK / "SS03.png",
        "prompt": DOGGY_WITHDRAW_PROMPT,
        "neg": NEG_DOGGY,
        "loras": DOGGY_SEX_LORAS_ASYM,
        "amp": 0.34,
        "frames": 41,
    },
    3: {
        "id": "SS03_LC03",
        "hypothesis": (
            "Escalate: NSFW-22 general motion pair stacked with light Doggy Sex "
            "(H0.45/L0.5 NSFW-22 + Doggy H0.55/L0.55) — not dtwr (missionary-only)."
        ),
        "image": PACK / "SS03.png",
        "prompt": DOGGY_INOUT_PROMPT,
        "neg": NEG_DOGGY,
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
            {
                "id": "doggy_sex_high",
                "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
                "weight": 0.55,
                "branch": "high",
            },
            {
                "id": "doggy_sex_low",
                "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
                "weight": 0.55,
                "branch": "low",
            },
        ],
        "amp": 0.32,
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


def extract_early_window(video: Path, diag_dir: Path, max_frame: int = 13) -> list[Path]:
    diag_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for n in range(max_frame + 1):
        dest = diag_dir / f"{video.stem}_f{n:02d}.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"select=eq(n\\,{n})",
            "-vsync",
            "vfr",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(dest),
        ]
        subprocess.run(cmd, capture_output=True, check=False)
        if dest.is_file():
            out.append(dest)
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
    early: list[str] = []
    if promoted:
        diag = DIAG_ROOT / beat["id"]
        extracted = extract_frames(promoted, diag)
        frames = {k: str(v) for k, v in extracted.items()}
        early_dir = EARLY_ROOT / beat["id"]
        early_paths = extract_early_window(promoted, early_dir, max_frame=13)
        early = [str(p) for p in early_paths]

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
        "early_window_frames": early,
        "result_ok": result.get("ok"),
    }
    out_json = ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_ss03_lora_combo_experiments.py <1|2|3>", flush=True)
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
