#!/usr/bin/env python3
"""For fun — Realisian v60 t2i + i2i (SD 1.5 photoreal on kitsune Rin)."""
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
FUN_DIR = PROJECT_DIR / "fun"
SOURCE = P.HERO_STILL
STYLE = "realisian"
SEED = 666061

# Euler ancestral + normal (same pair that worked on Pony i2i v3_fd)
SAMPLER = "euler_ancestral"
SCHEDULER = "normal"

# SD 1.5 Realisian — catalog steps/cfg; euler for this retry
WIDTH = 512
HEIGHT = 768
STEPS = 12
CFG = 3.0

PROMPT = (
    "RAW photo, portrait, young woman with white hair, fox ears headband, "
    "military style blue uniform, cherry blossom park background, "
    "natural skin texture, soft cinematic lighting, highly detailed"
)


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_fun_realisian.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        FUN_DIR.mkdir(parents=True, exist_ok=True)
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

        print("=== fun t2i realisian_v60 ===", flush=True)
        t2i = engine.generate_image(
            prompt=PROMPT,
            style=STYLE,
            width=WIDTH,
            height=HEIGHT,
            steps=STEPS,
            cfg=CFG,
            seed=SEED,
            sampler=SAMPLER,
            scheduler=SCHEDULER,
            face_detail=False,
        )
        t2i_dest = FUN_DIR / "Rin_fun_realisian_t2i_euler.png"
        shutil.copy2(t2i["saved_files"][0], t2i_dest)

        print("=== fun i2i realisian_v60 ===", flush=True)
        i2i = engine.generate_image_i2i(
            image_path=str(SOURCE),
            prompt=PROMPT,
            style=STYLE,
            width=WIDTH,
            height=HEIGHT,
            steps=STEPS,
            cfg=CFG,
            seed=SEED,
            denoising_strength=0.55,
            sampler=SAMPLER,
            scheduler=SCHEDULER,
            face_detail=False,
        )
        i2i_dest = FUN_DIR / "Rin_fun_realisian_i2i_euler.png"
        shutil.copy2(i2i["saved_files"][0], i2i_dest)

        payload = {
            "status": "success",
            "note": "for fun — realisian v60, euler_ancestral + normal",
            "style": STYLE,
            "checkpoint": "realisian_v60.safetensors",
            "sampler": SAMPLER,
            "scheduler": SCHEDULER,
            "t2i": str(t2i_dest),
            "i2i": str(i2i_dest),
            "i2i_denoise": 0.55,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, FUN_DIR / "rin_fun_realisian.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
