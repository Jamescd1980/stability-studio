"""SS03-2 side-angle quality MoE — thumb-in-ass keep / cock travel.

Same keeper stack as SS03_1_v2_T1 / SS03_2_v2_T1:
  - Doggy Sex HIGH+LOW @ 1.0/1.0, 41f, quality (no Lightning)
  - MCP cannot pass Doggy action pair — use this Python engine path
  - V2_T1 was amp 0.45 jerky + pulled thumb out; V2_T2/T3 drop amp + thumb lock
  - THUMB_A1 = thumb deepen only (dropped by user)
  - COCK_R1/R2 = real axial cock travel; hand/thumb stays; kill length-morph illusion

Usage:
  py -3 run_ss03_2_side_angle.py V2_T2
  py -3 run_ss03_2_side_angle.py V2_T3
  py -3 run_ss03_2_side_angle.py THUMB_A1
  py -3 run_ss03_2_side_angle.py COCK_R1
  py -3 run_ss03_2_side_angle.py COCK_R1b
  py -3 run_ss03_2_side_angle.py COCK_R2
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
DIAG_ROOT = ROOT / "outputs" / "saloon_diag_frames" / "ss03_2_side"

# Exit/melt + hand flail. No hip-shake / side-to-side hip block (intentional beat).
# Thumb-exit block added after V2_T1 pulled thumb out. No jumping genitals / shifting labia.
NEG_DOGGY = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, shifting grip, extra hands, four hands, "
    "thumb leaving, finger pulling out, empty asshole, hand leaving ass, "
    "thumb out, finger exit, thumb withdrawing, "
    "camera pan, camera drift, sliding out of frame, character drifting, "
    "frame slide, background sliding, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

# T3: allow slight thumb press-in; still kill thumb exit / hand flail / melt.
NEG_DOGGY_THUMB_DEEPEN = (
    "fast motion, violent slam, "
    "waving hands, grabbing randomly, flailing hands, extra hands, four hands, "
    "thumb leaving, finger pulling out, empty asshole, hand leaving ass, "
    "thumb out, finger exit, thumb withdrawing, thumb sliding out, "
    "camera pan, camera drift, sliding out of frame, character drifting, "
    "frame slide, background sliding, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

# A1: thumb deepen only — hips nearly still; short mouth hold; no eye/mouth essay.
NEG_THUMB_A1 = (
    "fast motion, violent slam, thrusting hips, bouncing hips, hip slam, "
    "waving hands, grabbing randomly, flailing hands, extra hands, four hands, "
    "thumb leaving, finger pulling out, empty asshole, hand leaving ass, "
    "thumb out, finger exit, thumb withdrawing, thumb sliding out, "
    "mouth wide open, gaping mouth, deformed mouth, melting mouth, "
    "screaming mouth, huge open mouth, open mouth, "
    "camera pan, camera drift, sliding out of frame, character drifting, "
    "frame slide, background sliding, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

# R1b: SS03-1 NEG_DOGGY shape + short thumb-exit/deepen kills + lateral block.
# From outputs/saloon_SS03_1_vs_SS03_2_prompt.md NEG_DOGGY_THUMB_STAY.
NEG_DOGGY_THUMB_STAY = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, shifting grip, extra hands, four hands, "
    "thumb leaving, finger pulling out, empty asshole, hand leaving ass, "
    "thumb out, finger exit, thumb withdrawing, thumb sliding out, thumb shoving deeper, "
    "side to side, lateral sway, swinging sideways, left right wobble, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

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
        "id": "SS03_2_v2_T1",
        "hypothesis": (
            "SS03-2.png only. Same stack as SS03_1_v2_T1 (Doggy Sex 1.0/1.0, amp 0.45, "
            "41f quality). One verb: side-to-side hip sway / lateral fuck motion — not "
            "forward-back thrust. NEG without side-to-side hip block; exit/melt kept."
        ),
        "image": PACK / "SS03-2.png",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "he fucks her pussy from behind with side-to-side hip motion, "
            "hips rocking side to side, partial withdraw only, vaginal penetration, "
            "steady side view"
        ),
        "neg": NEG_DOGGY,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.45,
        "frames": 41,
    },
    "V2_T2": {
        "id": "SS03_2_v2_T2",
        "hypothesis": (
            "Retry after V2_T1: amp 0.45 was jerky and pulled thumb out of her asshole. "
            "Lower amp ~0.32; one gentle side-to-side hip verb; explicit thumb stays in "
            "her asshole. Thumb-exit negs added."
        ),
        "image": PACK / "SS03-2.png",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "slow side-to-side hip motion, "
            "his thumb stays in her asshole, thumb buried in her ass, "
            "partial withdraw only, vaginal penetration, "
            "steady side view"
        ),
        "neg": NEG_DOGGY,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.32,
        "frames": 41,
    },
    "V2_T3": {
        "id": "SS03_2_v2_T3",
        "hypothesis": (
            "Second retry: primary verb = shoving thumb deeper into her asshole; "
            "hips only subtle so thumb wins. Amp ~0.35 (below 0.45). Softened "
            "moving-hands negs so deepen can happen; still kill thumb exit."
        ),
        "image": PACK / "SS03-2.png",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "shoving his thumb deeper into her asshole, "
            "subtle slow hip rock, cock stays in her pussy, "
            "partial withdraw only, vaginal penetration, "
            "steady side view"
        ),
        "neg": NEG_DOGGY_THUMB_DEEPEN,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.35,
        "frames": 41,
    },
    "THUMB_A1": {
        "id": "SS03_2_thumb_A1",
        "hypothesis": (
            "Split plan Clip A only: one verb slowly shoving thumb deeper into her "
            "asshole. Hips nearly still (cock thrust deferred to Clip B LF2V). "
            "Short mouth hold (closed/soft lips); mouth-fail negs. Amp ~0.32. "
            "Stop for human keep before Clip B."
        ),
        "image": PACK / "SS03-2.png",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "slowly shoving his thumb deeper into her asshole, "
            "hips nearly still, closed mouth, soft lips, "
            "cock stays in her pussy, steady side view"
        ),
        "neg": NEG_THUMB_A1,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.32,
        "frames": 41,
        "copy_lastframe": OUT_DIR / "SS03_2_thumb_A1_LF.png",
    },
    "COCK_R1": {
        "id": "SS03_2_cock_R1",
        "hypothesis": (
            "User dropped thumb-insertion attempts. From original SS03-2.png: "
            "one verb = cock thrusting in and out with hip thrust driving the shaft "
            "(partial withdraw only). Hand/thumb stays put — not the hero. "
            "Kill length-morph illusion (veins prove fake stretch). Amp 0.38."
        ),
        "image": PACK / "SS03-2.png",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "his cock thrusting in and out of her pussy, "
            "hip thrust driving the shaft, partial withdraw only, "
            "vaginal penetration, hand and thumb stay in place on her ass, "
            "steady grip, steady side view"
        ),
        "neg": NEG_COCK_TRAVEL,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.38,
        "frames": 41,
    },
    "COCK_R1b": {
        "id": "SS03_2_v2_COCK_R1b",
        "hypothesis": (
            "Borrow SS03-1 prompt shape: hip-as-hero forward/back + short "
            "'thumb stays in her ass'. NEG_DOGGY_THUMB_STAY = SS03-1 lateral block "
            "+ thumb exit/deepen kills (no length-morph essay). Amp 0.42. "
            "Do not recycle pingpong_smooth keeper."
        ),
        "image": PACK / "SS03-2.png",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "he fucks her pussy from behind, thrusting his hips forward and back, "
            "partial withdraw only, vaginal penetration, "
            "thumb stays in her ass, steady side view"
        ),
        "neg": NEG_DOGGY_THUMB_STAY,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.42,
        "frames": 41,
    },
    "COCK_R2": {
        "id": "SS03_2_cock_R2",
        "hypothesis": (
            "Optional retry only if R1 length-morph still dominates. Slightly lower "
            "amp 0.35; emphasize axial slide / veins travel with shaft; hand stays."
        ),
        "image": PACK / "SS03-2.png",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "cock sliding in and out of her pussy with real axial travel, "
            "slow hip thrust, shaft moves in and out, partial withdraw only, "
            "vaginal penetration, thumb stays in place in her ass, "
            "steady grip, steady side view"
        ),
        "neg": NEG_COCK_TRAVEL,
        "loras": DOGGY_SEX_LORAS,
        "amp": 0.35,
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
    lastframe_copy: str | None = None
    if promoted:
        diag = DIAG_ROOT / beat["id"]
        extracted = extract_frames(promoted, diag)
        frames = {k: str(v) for k, v in extracted.items()}
        lf_dest = beat.get("copy_lastframe")
        if lf_dest and extracted.get("last"):
            lf_path = Path(lf_dest)
            lf_path.parent.mkdir(parents=True, exist_ok=True)
            if lf_path.is_file():
                recycle(lf_path)
            shutil.copy2(str(extracted["last"]), str(lf_path))
            lastframe_copy = str(lf_path)

    summary = {
        "ok": bool(promoted),
        "id": beat["id"],
        "hypothesis": beat.get("hypothesis"),
        "image": str(start),
        "path": str(promoted) if promoted else None,
        "lastframe": lastframe_copy,
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
