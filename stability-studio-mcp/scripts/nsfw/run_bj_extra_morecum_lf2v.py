"""BJ_extra LF2V continue — more cum on face from last frame, then splice to ~8s."""

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
from studio.video_utils import extract_last_frame  # noqa: E402

from recycle_path import recycle  # noqa: E402

OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
EDIT = OUT_DIR / "_bj_edit"
BASE = OUT_DIR / "BJ_extra.mp4"
LAST = OUT_DIR / "BJ_extra_lastframe.png"
CONT = OUT_DIR / "BJ_extra_morecum.mp4"
BEAT_ID = "BJ_extra_morecum"

PROMPT = (
    "nsfw, Facial, cum shot, sticky cum, more cum, heavy facial, "
    "thick erect penis in front of her face, tip pointed at her face, "
    "another thick rope of cum shoots onto her face, "
    "more cum lands on her cheeks, forehead, nose, lips, and chin, "
    "cum already on her face gets thicker and wetter, "
    "fresh white streaks drip down her face, "
    "she flinches slightly as more cum hits, small blink, "
    "mouth slightly open, looking up, steady camera, same face, same pose"
)
NEG = (
    "clean face, wiping cum off, dry face, cum disappearing, "
    "less cum, cum vanishing, face cleaned, "
    "penis in mouth, sucking, oral insertion, going back in, "
    "coke bottle penis, bottle shaped penis, hourglass shaft, "
    "deformed tip, warped glans, melting tip, misshapen tip, "
    "deflating penis, shrinking penis, morphing genitals, "
    "melting face, morphing face, identity change, "
    "fast whip pan, violent thrashing, "
    "talking, chewing, biting, cartoon, chibi"
)

LORAS = [
    {
        "id": "facial_high",
        "file": "CloseUpFacialCum-v10_High.safetensors",
        "weight": 1.0,
        "branch": "high",
    },
    {
        "id": "facial_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 1.0,
        "branch": "low",
    },
]


def _norm(src: Path, dst: Path) -> None:
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vf",
            "scale=720:720:force_original_aspect_ratio=decrease,"
            "pad=720:720:(ow-iw)/2:(oh-ih)/2,fps=16",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-preset",
            "medium",
            str(dst),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def splice_to_8s(base: Path, cont: Path, dest: Path) -> Path:
    EDIT.mkdir(parents=True, exist_ok=True)
    a = EDIT / "bj_extra_base_norm.mp4"
    b = EDIT / "bj_extra_cont_norm.mp4"
    _norm(base, a)
    _norm(cont, b)
    lst = EDIT / "bj_extra_splice.txt"
    lst.write_text(f"file '{a.as_posix()}'\nfile '{b.as_posix()}'\n", encoding="utf-8")
    raw = EDIT / "bj_extra_spliced_raw.mp4"
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(raw),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # trim/pad to exactly 8s
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(raw),
            "-t",
            "8",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-an",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return dest


def main() -> int:
    if not BASE.is_file():
        print(f"missing {BASE}", flush=True)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EDIT.mkdir(parents=True, exist_ok=True)

    print(f"extracting last frame -> {LAST}", flush=True)
    extract_last_frame(BASE, LAST)

    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    engine.comfy.timeout = max(getattr(engine.comfy, "timeout", 600), 7200)
    print(f"===== I2V {BEAT_ID} (LF2V more facial cum) =====", flush=True)

    result = engine.generate_video(
        prompt=PROMPT,
        mode="i2v",
        negative_prompt=NEG,
        workflow_id="i2v",
        content_rating="open",
        image_path=str(LAST),
        num_frames=65,
        frame_rate=16.0,
        loras=LORAS,
        moe_preset="quality",
        smooth_motion=False,
        motion_amplitude=0.45,
    )

    saved = result.get("saved_files") or []
    if isinstance(saved, str):
        saved = [saved]
    promoted = None
    for p in saved:
        src = Path(str(p))
        if src.is_file() and src.suffix.lower() == ".mp4":
            if CONT.is_file():
                recycle(CONT)
            shutil.move(str(src), str(CONT))
            promoted = CONT
            break

    if not promoted:
        summary = {"ok": False, "id": BEAT_ID, "path": None}
        print(json.dumps(summary, indent=2), flush=True)
        return 2

    # Keep original as BJ_extra_part1, write spliced 8s as BJ_extra.mp4
    part1 = OUT_DIR / "BJ_extra_part1.mp4"
    if not part1.is_file():
        shutil.copy2(BASE, part1)
    else:
        # refresh backup of current base before overwrite
        shutil.copy2(BASE, EDIT / "BJ_extra_before_morecum_splice.mp4")

    final = splice_to_8s(part1 if part1.is_file() else BASE, CONT, BASE)
    dur = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(final),
        ],
        text=True,
    ).strip()

    summary = {
        "ok": True,
        "id": BEAT_ID,
        "continuation": str(CONT),
        "last_frame": str(LAST),
        "final": str(final),
        "duration": dur,
        "note": "LF2V more cum on face + splice to ~8s",
    }
    (ROOT / "outputs" / "bj_extra_morecum_i2v.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
