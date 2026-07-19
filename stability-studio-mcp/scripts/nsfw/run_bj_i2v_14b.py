# -*- coding: utf-8 -*-
"""Run two identity-locked Wan 14B I2V clips from User Import BJ stills."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog
from studio.config import catalog_path, load_config
from studio.engine import GenerationEngine

JOBS = [
    {
        "name": "close_up",
        "image_path": r"D:\ComfyBox Images and Videos\User Import\close_up_bj.png",
        "prompt": (
            "Slow withdraw until the tip nearly leaves her lips, then smooth reinsert; "
            "hold face, purple hair, and anime style; no camera cut."
        ),
        "negative_prompt": (
            "photoreal, real person, identity change, different hair color, "
            "morphing face, hose, metal object, warped anatomy, flicker"
        ),
    },
    {
        "name": "wide_angle",
        "image_path": r"D:\ComfyBox Images and Videos\User Import\wide_angle_bj.png",
        "prompt": (
            "Gentle head bob with slow insert and withdraw; "
            "hold full-body pose, purple ponytail, room, and anime style; no camera cut."
        ),
        "negative_prompt": (
            "photoreal, real person, identity change, different hair color, "
            "morphing face, hose, metal object, warped anatomy, flicker"
        ),
    },
]


def main() -> None:
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    # 14B can take a long time on comfybox
    engine.comfy.timeout = max(engine.comfy.timeout, 3600)

    results = []
    for job in JOBS:
        print("=" * 60, flush=True)
        print(f"START {job['name']} → workflow_id=i2v", flush=True)
        try:
            result = engine.generate_video(
                prompt=job["prompt"],
                mode="i2v",
                workflow_id="i2v",
                image_path=job["image_path"],
                negative_prompt=job["negative_prompt"],
                use_painter_i2v=False,
                smooth_motion=False,
                lora_bundle="",
                lora_ids=None,
            )
        except Exception as exc:
            result = {"ok": False, "name": job["name"], "error": str(exc)}
            print(f"FAIL {job['name']}: {exc}", flush=True)
        else:
            result = {**result, "ok": True, "name": job["name"]}
            print(
                f"OK {job['name']} saved={result.get('saved_files')}",
                flush=True,
            )
        results.append(result)
        out = ROOT / "outputs" / f"bj_i2v_14b_{job['name']}.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    summary = ROOT / "outputs" / "bj_i2v_14b_summary.json"
    summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("SUMMARY", summary, flush=True)
    failed = [r for r in results if not r.get("ok") or not r.get("saved_files")]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
