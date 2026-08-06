"""Frieren Saloon scene pack — I2V for BJ + SS stills (quality MoE, one beat at a time).

Pack:
  D:\\ComfyBox Images and Videos\\User Import\\Frieren Sex Sceens\\scene_packs\\Frieren Saloon

Videos out:
  D:\\ComfyBox Images and Videos\\Video\\Frieren\\Saloon\\

Usage:
  py -3 run_saloon_i2v_chain.py              # run all missing
  py -3 run_saloon_i2v_chain.py BJ01         # one beat
  py -3 run_saloon_i2v_chain.py SS04_Cum
"""

from __future__ import annotations

import json
import shutil
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

ORAL_LORAS = [
    {
        "id": "oral_high",
        "file": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "weight": 0.7,
        "branch": "high",
    },
    {
        "id": "oral_low",
        "file": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "weight": 0.7,
        "branch": "low",
    },
]

# Continuous thrusting Missionary Sex pair (playtime_ai / HF mirror).
# Use for already-in thrusting beats (SS02+). Tip-at-entrance SS01: Sex LoRA
# caused full exit + vagina melt — prefer Insertion pair + stay-buried prompt.
SEX_MISSIONARY_LORAS = [
    {
        "id": "missionary_sex_high",
        "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "weight": 0.55,
        "branch": "high",
    },
    {
        "id": "missionary_sex_low",
        "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "weight": 0.55,
        "branch": "low",
    },
]

# Tip→in contact hold (POV Missionary Insertion HIGH+LOW).
INSERTION_MISSIONARY_LORAS = [
    {
        "id": "missionary_insertion_high",
        "file": "wan2.2-i2v-high-pov-missionary-insertion-v1.safetensors",
        "weight": 0.6,
        "branch": "high",
    },
    {
        "id": "missionary_insertion_low",
        "file": "wan2.2-i2v-low-pov-missionary-insertion-v1.safetensors",
        "weight": 0.6,
        "branch": "low",
    },
]

# Doggy Style Sex (playtime_ai I2V HIGH+LOW). Use for SS03 rear pose — not Missionary.
SEX_DOGGY_LORAS = [
    {
        "id": "doggy_sex_high",
        "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "weight": 0.6,
        "branch": "high",
    },
    {
        "id": "doggy_sex_low",
        "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "weight": 0.6,
        "branch": "low",
    },
]

# Optional shaft lock if penis melts while contact holds (do not stack with 2 action pairs).
PENIS_LOCK_LORAS = [
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
]

NEG_ORAL = (
    "fast motion, violent thrusting, "
    "pulling away, withdrawing, empty mouth, "
    "circular head motion, head circling, "
    "melting face, morphing face, flicker, "
    "deflating penis, shrinking penis, "
    "talking, chewing, biting, cartoon, chibi"
)

NEG_SEX = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, shifting grip, squeezing thighs, extra hands, four hands, "
    "side to side, lateral sway, swinging sideways, left right wobble, "
    "hip shake, hip wiggle, shaking hips, body shake, "
    "penis pulse, pulsing cock, throbbing only, shaft pulse without thrust, "
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

# SS04 cum: pulse/drip OK — drop pulse/hip-shake block from NEG_SEX.
NEG_SEX_CUM = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "side to side, lateral sway, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "sudden new splash, exploding fluid, disappearing fluid, dry insertion, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

# Still → video beats only (PS + Post BJ stay stills).
BEATS: list[dict] = [
    {
        "id": "BJ01",
        "image": "BJ01.png",  # may be BJ01_start_from_clip upscaled (2s frame)
        "prompt": (
            "nsfw, she is giving him a blowjob, "
            "well formed glans tip in her mouth, "
            "lips stay sealed on the tip, gentle suck, "
            "small bob along the shaft axis, looking up, "
            "steady view"
        ),
        "neg": NEG_ORAL
        + ", deformed penis, melting glans, misshapen tip, blob tip",
        "loras": ORAL_LORAS,
        "amp": 0.5,
        "frames": 65,
    },
    {
        "id": "BJ02",
        "image": "BJ02.png",
        "prompt": (
            "nsfw, deep blowjob, "
            "mouth stays on the shaft, small bob up and down, "
            "looking up, soft eye blink, "
            "steady view"
        ),
        "neg": NEG_ORAL,
        "loras": ORAL_LORAS,
        "amp": 0.6,
        "frames": 65,
    },
    {
        # Tip-at-entrance. Goal: 1–2 clean thrusts, no deform / disappearing anatomy.
        # Prefer short shallow in-out that never fully exits (ping-pong first ~2s if deeper fails).
        # ONE verb family. Insertion pair @0.6. Optional deep-stroke chain: gate deepest
        # clean frame → Forge refine → I2V deeper (LF→I2V), then ping-pong.
        "id": "SS01",
        "image": "SS01.png",
        "prompt": (
            "nsfw, he slowly pushes his cock into her pussy, "
            "one short front-to-back thrust, cock stays inside, "
            "partial withdraw only, vaginal penetration, steady view"
        ),
        "neg": NEG_SEX,
        "loras": INSERTION_MISSIONARY_LORAS,
        "amp": 0.32,
        "frames": 49,
    },
    {
        # Same recipe as SS01 keeper: original pack still (hi-res) + Insertion LoRA +
        # one short stay-inside thrust — then ping-pong the good seconds. Do NOT replace
        # with upscaled video frames (quality loss).
        "id": "SS02",
        "image": "SS02.png",
        "prompt": (
            "nsfw, he slowly pushes his cock into her pussy, "
            "one short front-to-back thrust, cock stays inside, "
            "partial withdraw only, vaginal penetration, steady view"
        ),
        "neg": NEG_SEX,
        "loras": INSERTION_MISSIONARY_LORAS,
        "amp": 0.32,
        "frames": 49,
    },
    {
        # Original SS03 pack still (hi-res). Doggy Sex + one short axial thrust (SS01 pattern).
        "id": "SS03",
        "image": "SS03.png",
        "prompt": (
            "nsfw, they are having doggy style sex, "
            "from behind he slowly pushes his cock into her pussy, "
            "one short front-to-back thrust, cock stays inside, "
            "partial withdraw only, vaginal penetration, steady view"
        ),
        "neg": NEG_SEX,
        "loras": SEX_DOGGY_LORAS,
        "amp": 0.35,
        "frames": 49,
    },
    {
        # Cum already painted — few pumps + drip; penis pulse OK here.
        "id": "SS04_Cum",
        "image": "SS04_Cum.png",
        "prompt": (
            "nsfw, they are having doggy style sex, "
            "a few slow front-to-back hip pumps, cock stays inside, "
            "painted fluid keeps dripping, steady view"
        ),
        "neg": NEG_SEX_CUM,
        "loras": SEX_DOGGY_LORAS,
        "amp": 0.35,
        "frames": 49,
    },
]


def run_beat(engine: GenerationEngine, beat: dict) -> dict:
    start = PACK / beat["image"]
    dest = OUT_DIR / f"{beat['id']}.mp4"
    if not start.is_file():
        return {"ok": False, "id": beat["id"], "error": f"missing {start}"}

    print(f"===== I2V {beat['id']} quality amp={beat['amp']} =====", flush=True)
    print("image", start, flush=True)

    kwargs = dict(
        prompt=beat["prompt"],
        mode="i2v",
        negative_prompt=beat["neg"],
        workflow_id="i2v",
        content_rating="open",
        image_path=str(start),
        num_frames=int(beat["frames"]),
        frame_rate=16.0,
        moe_preset="quality",
        smooth_motion=False,
        motion_amplitude=float(beat["amp"]),
    )
    if beat.get("loras"):
        kwargs["loras"] = beat["loras"]

    result = engine.generate_video(**kwargs)
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

    summary = {
        "ok": bool(promoted),
        "id": beat["id"],
        "image": str(start),
        "path": str(promoted) if promoted else None,
        "preset": (result.get("moe") or {}).get("preset"),
        "motion_amplitude": beat["amp"],
    }
    out_json = ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None

    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

    selected = [b for b in BEATS if only is None or b["id"] == only]
    if only and not selected:
        print(f"unknown beat {only}; choose: " + ", ".join(b["id"] for b in BEATS), flush=True)
        return 2

    results = []
    for beat in selected:
        dest = OUT_DIR / f"{beat['id']}.mp4"
        if only is None and dest.is_file() and dest.stat().st_size > 10_000:
            print(f"skip existing {dest.name}", flush=True)
            results.append({"ok": True, "id": beat["id"], "path": str(dest), "skipped": True})
            continue
        results.append(run_beat(engine, beat))

    summary = {
        "ok": all(r.get("ok") for r in results),
        "out_dir": str(OUT_DIR),
        "results": results,
        "stills_not_video": [
            "PS01-PS07",
            "Post BJ Pre Sex Stll.png",
        ],
    }
    out_json = ROOT / "outputs" / "saloon_i2v_chain.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print("DONE", out_json, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
