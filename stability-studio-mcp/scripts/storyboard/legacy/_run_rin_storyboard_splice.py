#!/usr/bin/env python3
"""Splice Rin hero clips frame-accurately (no audio). Drops duplicate chain frames only."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

_LEGACY = Path(__file__).resolve().parent
sys.path.insert(0, str(_LEGACY))
from _bootstrap import setup_paths

setup_paths()
MCP_ROOT = setup_paths()
from _env import comfy_python, imageio_ffmpeg

import rin_project_paths as P

P.ensure_layout()
LOG = P.LOGS / "rin_storyboard_splice.json"

FFMPEG = imageio_ffmpeg()

FPS = 16
CLIP1 = P.CLIP1_WALK
CLIP2 = P.CLIP2_BOW
CLIP3 = P.CLIP3_STAB_FADE
OUT_DEFAULT = P.STORYBOARD_SPLICED
OUT_ALT = P.STORYBOARD_SPLICED_ALT


def ff() -> str:
    return str(FFMPEG) if FFMPEG.is_file() else "ffmpeg"


def probe(path: Path) -> dict:
    sys.path.insert(0, str(ROOT))
    from studio.video_utils import probe_video

    info = probe_video(path)
    info["file"] = path.name
    return info


def splice(*, tail_drop: int, skip_head: int, out_path: Path) -> dict:
    """Join clips at I2V chain points.

    tail_drop: frames to drop from the end of clip1/clip2 (1 = last frame, 2 = last two).
    skip_head: frames to skip at the start of clip2/clip3 (1 = skip duplicate of prior last).
    """
    for p in (CLIP1, CLIP2, CLIP3):
        if not p.is_file():
            raise FileNotFoundError(p)

    c1_end = 49 - tail_drop - 1  # inclusive last index kept on clip1 (48 frames when tail_drop=1)
    c2_start = skip_head
    c2_end = 48  # inclusive last index on clip2
    c3_start = skip_head
    c3_end = 48

    # select uses 0-based frame index n
    filter_complex = (
        f"[0:v]select='lte(n\\,{c1_end})',setpts=N/{FPS}/TB[v0];"
        f"[1:v]select='between(n\\,{c2_start}\\,{c2_end})',setpts=N/{FPS}/TB[v1];"
        f"[2:v]select='between(n\\,{c3_start}\\,{c3_end})',setpts=N/{FPS}/TB[v2];"
        f"[v0][v1][v2]concat=n=3:v=1:a=0[outv]"
    )

    subprocess.run(
        [
            ff(),
            "-y",
            "-i",
            str(CLIP1),
            "-i",
            str(CLIP2),
            "-i",
            str(CLIP3),
            "-filter_complex",
            filter_complex,
            "-map",
            "[outv]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )

    out_info = probe(out_path)
    frames_kept = {
        "clip1": c1_end + 1,
        "clip2": c2_end - c2_start + 1,
        "clip3": c3_end - c3_start + 1,
    }
    return {
        "status": "success",
        "inputs": {
            "clip1": str(CLIP1),
            "clip2": str(CLIP2),
            "clip3": str(CLIP3),
        },
        "splice": {
            "tail_drop": tail_drop,
            "skip_head": skip_head,
            "clip1_frames": f"0..{c1_end}",
            "clip2_frames": f"{c2_start}..{c2_end}",
            "clip3_frames": f"{c3_start}..{c3_end}",
            "frames_kept": frames_kept,
            "total_frames": sum(frames_kept.values()),
        },
        "output": str(out_path),
        "duration_sec": out_info["duration_sec"],
        "fps": FPS,
        "audio": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Frame-accurate Rin hero clip splice")
    parser.add_argument(
        "--tail-drop",
        type=int,
        default=1,
        choices=[1, 2],
        help="Drop this many frames from end of clip1/clip2 before join (1=last frame)",
    )
    parser.add_argument(
        "--skip-head",
        type=int,
        default=1,
        help="Skip this many frames at start of clip2/clip3 (1=duplicate chain frame)",
    )
    args = parser.parse_args()

    try:
        out_path = OUT_ALT if args.tail_drop == 2 else OUT_DEFAULT
        payload = splice(tail_drop=args.tail_drop, skip_head=args.skip_head, out_path=out_path)
        LOG.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        import shutil

        (MCP_ROOT / "outputs" / "rin_storyboard_splice.json").write_text(
            LOG.read_text(encoding="utf-8"), encoding="utf-8"
        )
        print(json.dumps(payload, indent=2))
        return 0
    except Exception as exc:
        err = {"status": "failed", "error": str(exc)}
        LOG.write_text(json.dumps(err, indent=2), encoding="utf-8")
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
