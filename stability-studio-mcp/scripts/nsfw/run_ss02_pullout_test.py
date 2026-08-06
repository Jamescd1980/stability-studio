"""SS02/SS03 pull-out polarity test ladder — quality MoE, one try per invocation.

Usage:
  py -3 run_ss02_pullout_test.py 1   # Try 1 — Missionary Sex partial withdraw on SS02
  py -3 run_ss02_pullout_test.py 2   # Try 2 — amp/frames/playtime variant on SS02
  py -3 run_ss02_pullout_test.py 3   # Try 3 — SS02 micro ping-pong OR SS03 doggy (auto if SS02 failed twice)
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
DIAG_ROOT = ROOT / "outputs" / "saloon_diag_frames" / "ss02_pullout"

SEX_MISSIONARY_LORAS_1 = [
    {
        "id": "missionary_sex_high",
        "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "high",
    },
    {
        "id": "missionary_sex_low",
        "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "low",
    },
]

SEX_MISSIONARY_LORAS_2 = [
    {
        "id": "missionary_sex_high",
        "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "weight": 0.85,
        "branch": "high",
    },
    {
        "id": "missionary_sex_low",
        "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "weight": 0.85,
        "branch": "low",
    },
]

SEX_DOGGY_LORAS = [
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

# Withdraw beat: keep exit/melt blocks; allow axial hip motion (no hip-shake neg).
NEG_PULLOUT = (
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

# SS03 doggy: same but explicitly no hip-shake block (doggy needs hip motion).
NEG_DOGGY_PULLOUT = NEG_PULLOUT

TRIES: dict[int, dict] = {
    1: {
        "id": "SS02_pullout_T1",
        "image": PACK / "SS02.png",
        "prompt": (
            "nsfw, a pov shot, he slowly pulls his cock partway out then settles back in, "
            "cock stays inside, partial withdraw only, vaginal penetration, "
            "hands stay gripping thighs, steady view"
        ),
        "neg": NEG_PULLOUT,
        "loras": SEX_MISSIONARY_LORAS_1,
        "amp": 0.32,
        "frames": 49,
    },
    2: {
        "id": "SS02_pullout_T2",
        "image": PACK / "SS02.png",
        "prompt": (
            "nsfw, A naked man and a naked woman having sex. "
            "He thrusts his penis in and out of her vagina. a pov shot. "
            "partial withdraw only, cock stays inside, vaginal penetration, steady view"
        ),
        "neg": NEG_PULLOUT,
        "loras": SEX_MISSIONARY_LORAS_2,
        "amp": 0.28,
        "frames": 33,
    },
    3: {
        # Default SS02 micro; override to SS03 via --ss03 flag
        "id": "SS02_pullout_T3",
        "image": PACK / "SS02.png",
        "prompt": (
            "nsfw, a pov shot, he slowly pulls his cock partway out then settles back in, "
            "cock stays inside, partial withdraw only, vaginal penetration, steady view"
        ),
        "neg": NEG_PULLOUT,
        "loras": SEX_MISSIONARY_LORAS_2,
        "amp": 0.28,
        "frames": 25,
    },
}

TRY3_SS03 = {
    "id": "SS03_pullout_T3",
    "image": PACK / "SS03.png",
    "prompt": (
        "nsfw, they are having doggy style sex, from behind he slides his cock "
        "partway out then pushes back in, partial withdraw only, cock stays inside, "
        "vaginal penetration, steady view"
    ),
    "neg": NEG_DOGGY_PULLOUT,
    "loras": SEX_DOGGY_LORAS,
    "amp": 0.28,
    "frames": 33,
}


def extract_frames(video: Path, diag_dir: Path, fps: float = 16.0) -> dict[str, Path]:
    diag_dir.mkdir(parents=True, exist_ok=True)
    probes = {
        "f0": 0.0,
        "mid": (33 / fps) / 2 if fps else 1.0,
        "last": -1,
    }
    out: dict[str, Path] = {}
    dur_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video),
    ]
    try:
        dur = float(subprocess.check_output(dur_cmd, text=True).strip())
    except Exception:
        dur = 49 / fps
    probes["mid"] = dur / 2
    probes["last"] = max(0.0, dur - (1 / fps))

    for label, t in probes.items():
        if label == "last":
            t = probes["last"]
        dest = diag_dir / f"{video.stem}_{label}.png"
        cmd = [
            "ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-q:v", "2", str(dest),
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
        print("usage: run_ss02_pullout_test.py <1|2|3> [--ss03]", flush=True)
        return 2

    try_num = int(sys.argv[1])
    use_ss03 = "--ss03" in sys.argv

    if try_num not in TRIES:
        print(f"unknown try {try_num}", flush=True)
        return 2

    beat = dict(TRY3_SS03 if (try_num == 3 and use_ss03) else TRIES[try_num])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    summary = run_try(engine, beat)
    print("DONE", ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json", flush=True)
    return 0 if summary.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
