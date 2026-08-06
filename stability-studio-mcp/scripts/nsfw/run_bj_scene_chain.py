"""Run remaining BJ scene I2V beats in order (quality MoE). Safe to leave unattended."""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "general"))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

from recycle_path import recycle  # noqa: E402

SCENE = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\scene_packs\01 BJ Scene"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
LOG = ROOT / "outputs" / "bj_scene_chain.log"

ORAL = [
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

# Remaining pack — skip any beat whose mp4 already exists.
BEATS = [
    {
        "id": "BJ04",
        "image": "BJ04.png",
        "skip_if_done": True,
        "prompt": (
            "nsfw, she is giving him a blowjob, "
            "head bobs gently up and down on the shaft, "
            "lips stay on the cock, looking up, soft eye blink, steady camera"
        ),
        "amp": 0.6,
    },
    {
        "id": "BJ05",
        "image": "BJ05 Still.png",
        "skip_if_done": True,
        "prompt": (
            "nsfw, she holds still with his cock in her mouth, "
            "subtle breathing, soft eye blink, tiny micro movement only, "
            "looking up, steady camera"
        ),
        "amp": 0.35,
    },
    {
        "id": "BJ06",
        "image": "BJ06 Lick.png",
        "skip_if_done": True,
        "prompt": (
            "nsfw, she licks his cock slowly with her tongue, "
            "tongue slides along the shaft, looking up, "
            "gentle motion, steady camera"
        ),
        "amp": 0.55,
    },
    {
        "id": "BJ07",
        "image": "BJ07 Clean.png",
        "skip_if_done": True,
        "prompt": (
            "nsfw, she cleans his cock with her mouth and tongue, "
            "slow licking and soft sucking, cum on her face stays, "
            "looking up, gentle motion, steady camera"
        ),
        "amp": 0.5,
    },
]

NEG = (
    "fast motion, violent thrusting, "
    "pulling away, withdrawing, empty mouth, "
    "circular head motion, head circling, "
    "melting face, morphing face, flicker, "
    "deflating penis, shrinking penis, "
    "talking, chewing, biting, cartoon, chibi"
)


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def wait_for_existing(path: Path, timeout_s: float = 7200) -> bool:
    """If another runner is still writing this beat, wait until stable."""
    if not path.is_file():
        return False
    last = -1
    stable = 0
    t0 = time.time()
    while time.time() - t0 < 120:
        sz = path.stat().st_size
        if sz > 100_000 and sz == last:
            stable += 1
            if stable >= 3:
                return True
        else:
            stable = 0
        last = sz
        time.sleep(5)
    return path.is_file() and path.stat().st_size > 100_000


def run_beat(engine: GenerationEngine, beat: dict) -> bool:
    beat_id = beat["id"]
    start = SCENE / beat["image"]
    dest = OUT_DIR / f"{beat_id}.mp4"

    if beat.get("skip_if_done") and dest.is_file() and dest.stat().st_size > 100_000:
        log(f"SKIP {beat_id} already exists ({dest.stat().st_size} bytes)")
        return True

    if not start.is_file():
        log(f"MISSING image {start}")
        return False

    log(f"===== I2V {beat_id} quality amp={beat['amp']} =====")
    log(f"image {start}")

    result = engine.generate_video(
        prompt=beat["prompt"],
        mode="i2v",
        negative_prompt=NEG,
        workflow_id="i2v",
        content_rating="open",
        image_path=str(start),
        num_frames=65,
        frame_rate=16.0,
        loras=ORAL,
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

    ok = bool(promoted)
    log(f"{'OK' if ok else 'FAIL'} {beat_id} -> {promoted}")
    summary = {
        "ok": ok,
        "id": beat_id,
        "path": str(promoted) if promoted else None,
        "preset": (result.get("moe") or {}).get("preset"),
    }
    (ROOT / "outputs" / f"{beat_id.lower()}_quality_i2v.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return ok


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log("BJ scene chain START (BJ04→BJ07)")
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

    all_ok = True
    for beat in BEATS:
        try:
            ok = run_beat(engine, beat)
        except Exception as e:
            log(f"EXCEPTION {beat['id']}: {e}")
            ok = False
        all_ok = all_ok and ok
        if not ok:
            log(f"STOP chain after failure on {beat['id']}")
            break

    log("BJ scene chain DONE" if all_ok else "BJ scene chain STOPPED WITH ERRORS")
    (ROOT / "outputs" / "bj_scene_chain_complete.txt").write_text(
        time.strftime("%Y-%m-%d %H:%M:%S") + (" OK\n" if all_ok else " FAIL\n"),
        encoding="utf-8",
    )
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
