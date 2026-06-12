#!/usr/bin/env python3
"""Pony V6 t2i + i2i — Rin kitsune eye cleanup."""
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
STEPS = 32

PROMPT = (
    "1girl, solo, kitsune fox girl, long straight white hair, blunt bangs, "
    "white fox ears with black tips, multiple large fluffy white fox tails with black tips, "
    "beautiful highly detailed red eyes, sharp pupils, crisp iris, bright eye highlights, "
    "catchlights, symmetrical eyes, fine eye shading, expressive gaze, "
    "dark blue military peaked cap, dark blue uniform jacket, gold buttons, gold aiguillettes, "
    "short pleated navy skirt with cherry blossom pattern, wide sleeves, black dress boots, "
    "walking toward viewer on stone path, cherry blossom trees, pink petals, soft daylight, "
    "full body, centered composition"
)

NEG_EXTRA = (
    "cross-eyed, lazy eye, mismatched eyes, flat eyes, solid color eyes, blurry eyes, "
    "dead eyes, no pupils, white eyes, asymmetrical eyes, bad eyes"
)


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_eye_cleanup_pony.json"
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

        neg = f"{NEG_EXTRA}"

        print("=== i2i (eye cleanup, denoise 0.40) ===", flush=True)
        i2i = engine.generate_image_i2i(
            image_path=str(SOURCE),
            prompt=PROMPT,
            style=STYLE,
            negative_prompt=neg,
            width=WIDTH,
            height=HEIGHT,
            steps=STEPS,
            seed=SEED,
            denoising_strength=0.40,
            face_detail=True,
        )
        i2i_src = Path(i2i["saved_files"][0])
        i2i_dest = PROJECT_DIR / "Rin_eyes_i2i_pony.png"
        shutil.copy2(i2i_src, i2i_dest)

        print("=== t2i (fresh Pony V6, same hero prompt) ===", flush=True)
        t2i = engine.generate_image(
            prompt=PROMPT,
            style=STYLE,
            negative_prompt=neg,
            width=WIDTH,
            height=HEIGHT,
            steps=STEPS,
            seed=SEED,
            face_detail=True,
        )
        t2i_src = Path(t2i["saved_files"][0])
        t2i_dest = PROJECT_DIR / "Rin_eyes_t2i_pony.png"
        shutil.copy2(t2i_src, t2i_dest)

        payload = {
            "status": "success",
            "style": STYLE,
            "checkpoint": "ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
            "source": str(SOURCE),
            "seed": SEED,
            "size": [WIDTH, HEIGHT],
            "prompt": PROMPT,
            "negative_extra": NEG_EXTRA,
            "i2i": {
                "denoising_strength": 0.40,
                "face_detail": True,
                "delivered": str(i2i_dest),
                "mcp_copy": str(i2i_src),
                "full_prompt": i2i.get("prompt"),
            },
            "t2i": {
                "face_detail": True,
                "delivered": str(t2i_dest),
                "mcp_copy": str(t2i_src),
                "full_prompt": t2i.get("prompt"),
            },
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_eye_cleanup_pony.json")
        print(json.dumps(payload, indent=2))
        print(f"\nI2I: {i2i_dest}\nT2I: {t2i_dest}", flush=True)
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
