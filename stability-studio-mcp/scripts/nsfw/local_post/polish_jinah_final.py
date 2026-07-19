# -*- coding: utf-8 -*-
"""Polish Jinah Sung Collection final: 16→24fps + AnimeSharp 2x on 5060 Ti."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.video_post import polish_wan_video
from studio.video_upscale import check_local_post

SRC = Path(
    r"D:\ComfyBox Images and Videos\Video\Jinah Sung Collection"
    r"\studio_agent_wan22_sq_oralcream_facial_final.mp4"
)


def main() -> None:
    cfg = load_config()
    status = check_local_post(cfg)
    print("LOCAL_POST", json.dumps(status, indent=2), flush=True)
    if not status.get("ok"):
        raise SystemExit("local_post not ready")
    if not SRC.is_file():
        raise SystemExit(f"missing source: {SRC}")

    print(f"START polish {SRC}", flush=True)
    result = polish_wan_video(
        cfg,
        SRC,
        target_fps=24.0,
        upscale_model="anime_sharp_2x",
        crf=17,
    )
    print("RESULT", json.dumps(result, indent=2), flush=True)
    out = ROOT / "outputs" / "polish_jinah_final.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"WROTE {out}", flush=True)


if __name__ == "__main__":
    main()
