# -*- coding: utf-8 -*-
"""Oral-creampie-only final; archive keepers; recycle rejects + temp trash."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.video_utils import concat_videos, probe_video

DELIVERY = Path(r"D:\ComfyBox Images and Videos")
VIDEO = DELIVERY / "Video"
TEMP = DELIVERY / "temp"
COMPARE = VIDEO / "compare"
WS_COMPARE = Path(r"D:\Bad boy\_compare_bj_close")
ARCHIVE = DELIVERY / "final" / "bj_closeup_oral_creampie"

BOBBING = VIDEO / "studio_agent_wan22_sq_bobbing19.mp4"
CREAM = VIDEO / "studio_agent_wan22_sq25_oralcream_00001.mp4"
FINAL_NAME = "studio_agent_wan22_sq_oralcream_final.mp4"

ARCHIVE_FROM_VIDEO = [
    "studio_agent_wan22_sq_00001.mp4",  # perfect square seed
    "studio_agent_wan22_sq_12s.mp4",
    "studio_agent_wan22_sq_bobbing19.mp4",
    "studio_agent_wan22_sq25_oralcream_00001.mp4",
    "studio_agent_wan22_widefix_00001.mp4",
]

# Everything else matching these prefixes/names in Video/ → recycle
REJECT_NAMES = {
    "studio_agent_00005.mp4",
    "studio_agent_wan22_00001.mp4",
    "studio_agent_wan22_00002.mp4",
    "studio_agent_wan22_sq25_build_1.mp4",
    "studio_agent_wan22_sq25_build_2.mp4",
    "studio_agent_wan22_sq25_cream_00001.mp4",
    "studio_agent_wan22_sq25_facial_00001.mp4",
    "studio_agent_wan22_sq25_facial_fid_00001.mp4",
    "studio_agent_wan22_sq25_facial_penis_00001.mp4",
    "studio_agent_wan22_sq25_money_00001.mp4",
    "studio_agent_wan22_sq_25s.mp4",
    "studio_agent_wan22_sq_25s_cum.mp4",
    "studio_agent_wan22_sq_25s_cum_build.mp4",
    "studio_agent_wan22_sq_25s_cum_fid.mp4",
    "studio_agent_wan22_sq_25s_cum_penis.mp4",
    "studio_agent_wan22_sq_build_1.mp4",
    "studio_agent_wan22_sq_build_2.mp4",
    "studio_agent_wan22_sq_build_3.mp4",
    "studio_agent_wan22_sq_ext1_00001.mp4",
    "studio_agent_wan22_sq_ext2_00001.mp4",
    "studio_agent_wan22_sq_ext3_00001.mp4",
}


def recycle(path: Path) -> None:
    """Send file or directory to Windows Recycle Bin."""
    path = path.resolve()
    if not path.exists():
        return
    # Microsoft.VisualBasic FileIO — Recycle Bin (not permanent delete)
    kind = "DeleteDirectory" if path.is_dir() else "DeleteFile"
    # Escape single quotes for PowerShell
    p = str(path).replace("'", "''")
    ps = (
        "Add-Type -AssemblyName Microsoft.VisualBasic; "
        f"[Microsoft.VisualBasic.FileIO.FileSystem]::{kind}("
        f"'{p}', "
        "'OnlyErrorDialogs', "
        "'SendToRecycleBin')"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=True,
        capture_output=True,
        text=True,
    )
    print(f"RECYCLE {path}", flush=True)


def main() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)

    # 1) Oral-creampie-only final (~23.4s)
    if not BOBBING.is_file() or not CREAM.is_file():
        raise FileNotFoundError("Missing bobbing or oralcream keeper")
    final_path = ARCHIVE / FINAL_NAME
    concat_videos([BOBBING, CREAM], final_path)
    # also leave a copy in Video/ for easy find
    video_final = VIDEO / FINAL_NAME
    shutil.copy2(final_path, video_final)
    info = probe_video(final_path)
    print(f"FINAL {final_path} ({info['duration_sec']:.2f}s)", flush=True)

    # 2) Archive keepers (copy then recycle originals from Video if not needed there)
    archived = [str(final_path)]
    for name in ARCHIVE_FROM_VIDEO:
        src = VIDEO / name
        if not src.is_file():
            print(f"MISSING keeper {name}", flush=True)
            continue
        dest = ARCHIVE / name
        shutil.copy2(src, dest)
        archived.append(str(dest))
        print(f"ARCHIVE {name}", flush=True)

    # Copy useful compare D reference into archive
    d2 = COMPARE / "D2_pose_matched_bobbing19.mp4"
    if d2.is_file():
        shutil.copy2(d2, ARCHIVE / d2.name)
        archived.append(str(ARCHIVE / d2.name))

    # README
    readme = {
        "title": "BJ close-up — oral creampie ending (no facial)",
        "final": str(final_path),
        "duration_sec": info["duration_sec"],
        "composition": [
            "studio_agent_wan22_sq_bobbing19.mp4 (~20.4s pose-matched)",
            "studio_agent_wan22_sq25_oralcream_00001.mp4 (~3.1s oral creampie)",
        ],
        "note": "Facial / money-shot attempts rejected (glans loss, jump, no facial). Moved on.",
        "archived": archived,
    }
    (ARCHIVE / "README.json").write_text(json.dumps(readme, indent=2), encoding="utf-8")

    # 3) Recycle rejects from Video/
    recycled = []
    for name in sorted(REJECT_NAMES):
        p = VIDEO / name
        if p.is_file():
            recycle(p)
            recycled.append(str(p))

    # After archive copy, recycle the Video copies of keepers EXCEPT leave oralcream final in Video
    # Keep bobbing/cream/seed/12s/wide in archive only — recycle Video duplicates of archived keepers
    # User said archive the rest — leave final in Video, recycle other Video keepers that are now in archive
    for name in ARCHIVE_FROM_VIDEO:
        p = VIDEO / name
        if p.is_file():
            recycle(p)
            recycled.append(str(p))

    # Recycle Video/compare work + demos
    if COMPARE.is_dir():
        recycle(COMPARE)
        recycled.append(str(COMPARE))

    # Recycle workspace compare pack
    if WS_COMPARE.is_dir():
        recycle(WS_COMPARE)
        recycled.append(str(WS_COMPARE))

    # 4) Temp trash → recycle
    temp_recycle_globs = [
        "polish_test_*",
        "*_upscale_2x.mp4",
        "_mcp_frame_preview.jpg",
    ]
    if TEMP.is_dir():
        for pattern in temp_recycle_globs:
            for p in TEMP.glob(pattern):
                recycle(p)
                recycled.append(str(p))
        for sub in ("bj_review", "bj_review_14b", "bj_review_shaftlock"):
            d = TEMP / sub
            if d.is_dir():
                recycle(d)
                recycled.append(str(d))

    # User Import leftover facial/cream chain frames (optional cleanup)
    imp = DELIVERY / "User Import"
    for pattern in (
        "close_up_sq25_*",
        "close_up_sq_chain_*",
        "close_up_sq_finish_*",
        "close_up_bj_00005_last.png",
    ):
        for p in imp.glob(pattern):
            if p.is_file():
                recycle(p)
                recycled.append(str(p))

    summary = {
        "ok": True,
        "final": str(final_path),
        "video_copy": str(video_final),
        "duration_sec": info["duration_sec"],
        "archive_dir": str(ARCHIVE),
        "archived": archived,
        "recycled_count": len(recycled),
        "recycled": recycled,
    }
    (ROOT / "outputs" / "bj_archive_oral_ending.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("DONE", json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
