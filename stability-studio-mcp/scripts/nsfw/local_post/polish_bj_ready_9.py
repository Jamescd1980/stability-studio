# -*- coding: utf-8 -*-
"""Polish all 9 Ready BJ masters: heavy minterpolate + AnimeSharp/RealESRGAN upscale."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.video_post import polish_wan_video
from studio.video_upscale import check_local_post

READY = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Ready for Post production")
MASTERS = READY / "01_Masters"
POLISHED = READY / "02_Polished"
WORK = READY / "_polish_work"

# Max smooth: 16→48fps MCI + AnimeSharp 2x (4x available as retry if 2x ok)
TARGET_FPS = 48.0
UPSCALE = "anime_sharp_2x"
UPSCALE_FALLBACK = "anime_sharp_2x"
CRF = 16


def main() -> int:
    cfg = load_config()
    status = check_local_post(cfg)
    print("LOCAL_POST", json.dumps(status, indent=2), flush=True)
    # Continue even if CUDA probe timed out — upscale may still work

    MASTERS.mkdir(parents=True, exist_ok=True)
    POLISHED.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    clips = [READY / f"BJ{i:02d}.mp4" for i in range(1, 10)]
    missing = [p for p in clips if not p.is_file()]
    if missing:
        print("MISSING", [p.name for p in missing], flush=True)
        return 2

    # Freeze masters (don't polish in-place clutter)
    for src in clips:
        dest = MASTERS / src.name
        if not dest.is_file() or dest.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dest)
            print(f"master <- {src.name}", flush=True)

    results = []
    for i, master in enumerate([MASTERS / f"BJ{n:02d}.mp4" for n in range(1, 10)], 1):
        work_src = WORK / master.name
        shutil.copy2(master, work_src)
        print(f"\n===== POLISH {i}/9 {master.name} =====", flush=True)
        model = UPSCALE
        try:
            result = polish_wan_video(
                cfg,
                work_src,
                target_fps=TARGET_FPS,
                upscale_model=model,
                crf=CRF,
            )
        except Exception as exc:
            print(f"4x failed ({exc}); falling back to {UPSCALE_FALLBACK}", flush=True)
            model = UPSCALE_FALLBACK
            result = polish_wan_video(
                cfg,
                work_src,
                target_fps=TARGET_FPS,
                upscale_model=model,
                crf=CRF,
            )

        final = Path(result["final"])
        out = POLISHED / f"BJ{i:02d}.mp4"
        shutil.copy2(final, out)
        probe = result.get("probe") or {}
        entry = {
            "id": f"BJ{i:02d}",
            "ok": bool(result.get("ok")),
            "model": model,
            "final": str(out),
            "probe": probe,
        }
        results.append(entry)
        print(json.dumps(entry, indent=2), flush=True)

    summary = {
        "ok": all(r["ok"] for r in results),
        "target_fps": TARGET_FPS,
        "upscale": UPSCALE,
        "masters": str(MASTERS),
        "polished": str(POLISHED),
        "clips": results,
    }
    out_json = ROOT / "outputs" / "polish_bj_ready_9.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print(f"WROTE {out_json}", flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
