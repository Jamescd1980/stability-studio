#!/usr/bin/env python3
"""Low-denoise Pony i2i — kunai + hands without regional mask (eye-cleanup recipe)."""
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
SOURCE = P.HERO_STILL

PROMPT = (
    "score_9, score_8_up, score_7_up, source_anime, high quality, detailed, 1girl, solo, "
    "kitsune fox girl, long white hair, blunt bangs, white fox ears, fluffy white fox tails, "
    "detailed red eyes, sharp pupils, closed mouth, neutral calm expression, "
    "dark blue military uniform, peaked cap, gold buttons, pleated skirt, black boots, "
    "natural hands five fingers, small black triangular kunai in right hand, left hand empty, "
    "walking toward viewer, cherry blossom park stone path, soft daylight, anime illustration"
)

NEGATIVE = (
    "sword, katana, long blade, dual wield, extra fingers, deformed hands, bad hands, "
    "open mouth, different face, different head, wrong angle, blurry eyes"
)

VARIANTS = [
    {"tag": "d022", "denoise": 0.22, "seed": 424247},
    {"tag": "d026", "denoise": 0.26, "seed": 424248},
]


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_kunai_i2i_low.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        requests.get("http://127.0.0.1:8188/system_stats", timeout=30)
        requests.post(
            "http://127.0.0.1:8188/free",
            json={"unload_models": True, "free_memory": True},
            timeout=120,
        )

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 3.0
        engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

        runs = []
        for v in VARIANTS:
            tag = str(v["tag"])
            print(f"=== pony i2i {tag} denoise={v['denoise']} ===", flush=True)
            result = engine.generate_image_i2i(
                image_path=str(SOURCE),
                prompt=PROMPT,
                style="pony",
                negative_prompt=NEGATIVE,
                width=696,
                height=1024,
                steps=28,
                cfg=5.5,
                seed=int(v["seed"]),
                denoising_strength=float(v["denoise"]),
                sampler="euler_ancestral",
                scheduler="normal",
                face_detail=False,
            )
            dest = PROJECT_DIR / f"Rin_kunai_i2i_{tag}.png"
            shutil.copy2(Path(result["saved_files"][0]), dest)
            runs.append({**v, "delivered": str(dest)})

        payload = {"status": "success", "approach": "full-frame low denoise i2i", "runs": runs}
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_kunai_i2i_low.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
