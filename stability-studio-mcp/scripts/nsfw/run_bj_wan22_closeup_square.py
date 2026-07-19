# -*- coding: utf-8 -*-
"""Re-run close-up BJ at square 720x720 so the man/depth stay in frame."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

from studio.config import load_config, catalog_path
from studio.engine import GenerationEngine
from studio.catalog import StyleCatalog

_spec = importlib.util.spec_from_file_location(
    "run_bj_wan22_loras", ROOT / "scripts" / "run_bj_wan22_loras.py"
)
_wan22 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_wan22)

IMAGE = Path(r"D:\ComfyBox Images and Videos\User Import\close_up_bj.png")
JOB = next(j for j in _wan22.JOBS if j["name"] == "close_up")


def main() -> None:
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)

    print(
        f"START close_up square {JOB['width']}x{JOB['height']}",
        flush=True,
    )
    uploaded = eng.comfy.upload_image(IMAGE)
    api = _wan22.build_api(
        image_name=uploaded,
        prompt=JOB["prompt"],
        negative=_wan22.NEG,
        width=JOB["width"],
        height=JOB["height"],
        seed=43,
    )
    api["70"]["inputs"]["filename_prefix"] = "studio_agent_wan22_sq"
    prompt_id = eng.comfy.queue_prompt(api)
    history = eng.comfy.wait_for_completion(prompt_id)
    outputs = eng.comfy.collect_outputs(history)
    saved = eng._save_comfy_outputs(outputs, extensions=(".mp4", ".webm", ".gif", ".png"))
    result = {
        "ok": bool(saved),
        "prompt_id": prompt_id,
        "saved_files": saved,
        "size": f"{JOB['width']}x{JOB['height']}",
        "note": "square to match 1024 source; avoid portrait side crop",
    }
    out = ROOT / "outputs" / "bj_wan22_close_up_square.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("OK" if saved else "FAIL", result, flush=True)
    sys.exit(0 if saved else 1)


if __name__ == "__main__":
    main()
