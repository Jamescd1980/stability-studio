#!/usr/bin/env python3
"""Pony V6 i2i — euler_ancestral + normal (user request)."""
from __future__ import annotations

import json
import shutil
import sys
import traceback
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
import rin_project_paths as P

P.ensure_layout()
PROJECT_DIR = P.ROOT
SOURCE = P.KITSUNE_SOURCE
STYLE = "pony"
WIDTH = 700
HEIGHT = 1024
SEED = 424242
SAMPLER = "euler_ancestral"
SCHEDULER = "normal"
CFG = 5.5
STEPS = 28

PROMPT = (
    "1girl, solo, kitsune fox girl, long white hair, blunt bangs, white fox ears, "
    "fluffy white fox tails, detailed red eyes, sharp pupils, eye highlights, "
    "closed mouth, neutral calm expression, small lips, "
    "dark blue military uniform, peaked cap, gold buttons, pleated skirt, black boots, "
    "walking toward viewer, cherry blossom park stone path, soft daylight, "
    "high fantasy anime illustration"
)

NEG_EXTRA = (
    "bad mouth, distorted lips, open mouth, teeth, weird smile, lip deformity, "
    "cross-eyed, flat eyes, blurry eyes, bad eyes, asymmetrical eyes"
)

VARIANTS = [
    {"tag": "v3_euler", "denoise": 0.30, "face_detail": False},
    {"tag": "v3_euler_fd", "denoise": 0.26, "face_detail": True},
]


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_eye_cleanup_pony_v3_euler.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        if not SOURCE.is_file():
            raise FileNotFoundError(f"Missing base image: {SOURCE}")

        requests.post(
            "http://127.0.0.1:8188/free",
            json={"unload_models": True, "free_memory": True},
            timeout=120,
        )

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 3.0
        cat = StyleCatalog(catalog_path(cfg), cfg)
        engine = GenerationEngine(cfg, cat)
        if not engine.comfy.is_running():
            raise RuntimeError("ComfyUI must be running")

        runs: list[dict] = []
        for v in VARIANTS:
            tag = str(v["tag"])
            print(
                f"\n=== {tag} {SAMPLER}/{SCHEDULER} denoise={v['denoise']} "
                f"face_detail={v['face_detail']} ===",
                flush=True,
            )
            result = engine.generate_image_i2i(
                image_path=str(SOURCE),
                prompt=PROMPT,
                style=STYLE,
                negative_prompt=NEG_EXTRA,
                width=WIDTH,
                height=HEIGHT,
                steps=STEPS,
                cfg=CFG,
                seed=SEED,
                denoising_strength=float(v["denoise"]),
                sampler=SAMPLER,
                scheduler=SCHEDULER,
                face_detail=bool(v["face_detail"]),
            )
            src = Path(result["saved_files"][0])
            dest = PROJECT_DIR / f"Rin_eyes_i2i_pony_{tag}.png"
            shutil.copy2(src, dest)
            runs.append({
                **v,
                "sampler": SAMPLER,
                "scheduler": SCHEDULER,
                "cfg": CFG,
                "steps": STEPS,
                "delivered": str(dest),
                "full_prompt": result.get("prompt"),
                "face_detail_info": result.get("face_detail"),
            })

        payload = {
            "status": "success",
            "source": str(SOURCE),
            "sampler": SAMPLER,
            "scheduler": SCHEDULER,
            "runs": runs,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_eye_cleanup_pony_v3_euler.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
