#!/usr/bin/env python3
"""Chain I2V clips from last frames and concat to ~16s.

Prefer generate_video(mode='v2v', video_path=..., concat_source=True) now that v2v_5b
is in catalog.yaml — this script remains as a multi-clip reference.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
from _bootstrap import ROOT, load_engine  # noqa: E402

OUT = ROOT / "outputs" / "kitsune_park"
CLIPS = [
    {
        "id": "02_twirl",
        "source": OUT / "frame_end_01.png",
        "prompt": (
            "anime kitsune fox girl twirling spin on park path, cherry blossom trees, "
            "close-up camera, graceful rotation, white fox tails flowing, spring daylight, smooth motion"
        ),
    },
    {
        "id": "03_face_camera",
        "source": OUT / "frame_end_02.png",
        "prompt": (
            "anime kitsune fox girl finishing twirl facing the camera on sakura park path, "
            "close-up, playful pose, white fox tails, smooth natural movement"
        ),
    },
    {
        "id": "04_wink",
        "source": OUT / "frame_end_03.png",
        "prompt": (
            "anime kitsune fox girl smiling and winking at camera, cute playful expression, "
            "cherry blossom park background blurred, close-up portrait, subtle head tilt, smooth motion"
        ),
    },
]

NEG = "static, frozen, still image, blurry, deformed, bad anatomy, jittery, morphing face"


def extract_last_frame(video: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-sseof",
        "-0.05",
        "-i",
        str(video),
        "-update",
        "1",
        "-q:v",
        "1",
        str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not dest.is_file() or dest.stat().st_size < 1000:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video),
                "-vf",
                "select='eq(n\\,0)'",
                "-vframes",
                "1",
                str(dest),
            ],
            check=True,
        )


def concat_clips(paths: list[Path], dest: Path) -> None:
    list_file = OUT / "concat_list.txt"
    lines = [f"file '{p.resolve().as_posix()}'" for p in paths]
    list_file.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(dest),
        ],
        check=True,
    )


def main() -> int:
    _, _, eng = load_engine()
    OUT.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = [OUT / "clip01_skip.mp4"]
    if not generated[0].is_file():
        print(f"Missing {generated[0]} — place clip 1 there or generate it first.", file=sys.stderr)
        return 1

    for spec in CLIPS:
        src = spec["source"]
        if not src.is_file():
            print(f"Missing source frame {src}", file=sys.stderr)
            return 1
        print(f"Generating {spec['id']} from {src.name}...", flush=True)
        result = eng.generate_video(
            prompt=spec["prompt"],
            mode="i2v",
            workflow_id="i2v_5b_painter",
            style="ilustmix",
            image_path=str(src),
            num_frames=65,
            frame_rate=16,
            use_painter_i2v=True,
            motion_amplitude=1.15,
            negative_prompt=NEG,
        )
        saved = result.get("saved_files") or []
        if not saved:
            print(json.dumps(result, indent=2), file=sys.stderr)
            return 1
        clip_path = Path(saved[0])
        dest = OUT / f"clip{spec['id']}.mp4"
        shutil.copy2(clip_path, dest)
        generated.append(dest)
        frame_out = OUT / f"frame_end_{spec['id'].split('_')[0]}.png"
        extract_last_frame(dest, frame_out)
        print(f"  -> {dest}", flush=True)

    final = OUT / "kitsune_park_16s.mp4"
    concat_clips(generated, final)
    meta = {
        "clips": [str(p) for p in generated],
        "final": str(final),
        "duration_target_sec": 16,
        "note": "Chained I2V from last frames (no catalog V2V workflow); 4x ~4s @ 65 frames / 16fps",
    }
    (OUT / "pipeline_result.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
