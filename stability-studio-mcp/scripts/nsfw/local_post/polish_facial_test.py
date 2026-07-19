# -*- coding: utf-8 -*-
"""Test main-rig polish on facial_00001 (interp + AnimeSharp 2x)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.video_post import polish_wan_video
from studio.video_upscale import check_local_post

SRC = Path(r"D:\ComfyBox Images and Videos\Video\studio_agent_wan22_sq25_facial_00001.mp4")
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\temp")


def main() -> None:
    cfg = load_config()
    status = check_local_post(cfg)
    print("LOCAL_POST", json.dumps(status, indent=2), flush=True)
    if not status.get("ok"):
        raise SystemExit("local_post not ready")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    test = OUT_DIR / "polish_test_facial_00001.mp4"
    shutil.copy2(SRC, test)
    print(f"START polish {test}", flush=True)
    result = polish_wan_video(
        cfg,
        test,
        target_fps=24.0,
        upscale_model="anime_sharp_2x",
        crf=17,
    )
    print("RESULT", json.dumps(result, indent=2), flush=True)
    (ROOT / "outputs" / "polish_facial_test.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
