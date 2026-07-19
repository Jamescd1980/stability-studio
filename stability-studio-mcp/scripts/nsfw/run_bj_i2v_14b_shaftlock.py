# -*- coding: utf-8 -*-
"""Re-run BJ I2V with shaft-persistence prompts (no full exit / no deflate)."""
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

NEG = (
    "deflating penis, shrinking penis, disappearing shaft, vanishing tip, "
    "melting genitals, empty mouth, tip missing, hose, metal object, "
    "photoreal, identity change, morphing face, flicker, warped anatomy"
)

JOBS = [
    {
        "name": "close_up",
        "image_path": r"D:\ComfyBox Images and Videos\User Import\close_up_bj.png",
        "prompt": (
            "Subtle head bob only. Partial withdraw — tip stays at her lips, never leaves. "
            "Thick erect penis stays solid with constant girth and remains visible in her mouth "
            "the whole time; hold purple hair, face, and anime style."
        ),
    },
    {
        "name": "wide_angle",
        "image_path": r"D:\ComfyBox Images and Videos\User Import\wide_angle_bj.png",
        "prompt": (
            "Gentle bobbing oral motion. Partial withdraw only — shaft never exits or shrinks. "
            "Thick erect penis stays solid with constant girth and stays in her mouth throughout; "
            "hold purple ponytail, bodies, room, and anime style."
        ),
    },
]


def main() -> None:
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    engine.comfy.timeout = max(engine.comfy.timeout, 3600)

    results = []
    for job in JOBS:
        print("=" * 60, flush=True)
        print(f"START {job['name']} → workflow_id=i2v shaft-lock", flush=True)
        try:
            result = engine.generate_video(
                prompt=job["prompt"],
                mode="i2v",
                workflow_id="i2v",
                image_path=job["image_path"],
                negative_prompt=NEG,
                use_painter_i2v=False,
                smooth_motion=False,
                lora_bundle="",
                lora_ids=None,
                num_frames=49,
            )
        except Exception as exc:
            result = {"ok": False, "name": job["name"], "error": str(exc)}
            print(f"FAIL {job['name']}: {exc}", flush=True)
        else:
            result = {**result, "ok": True, "name": job["name"]}
            print(f"OK {job['name']} saved={result.get('saved_files')}", flush=True)
        results.append(result)
        (ROOT / "outputs" / f"bj_i2v_shaftlock_{job['name']}.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )

    summary = ROOT / "outputs" / "bj_i2v_shaftlock_summary.json"
    summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("SUMMARY", summary, flush=True)
    failed = [r for r in results if not r.get("ok") or not r.get("saved_files")]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
