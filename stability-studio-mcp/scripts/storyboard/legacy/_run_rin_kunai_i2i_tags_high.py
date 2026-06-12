#!/usr/bin/env python3
"""Higher-denoise Pony i2i — holding_kunai tags (hands were locked at 0.28-0.35)."""
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

PROMPT = (
    "score_9, score_8_up, score_7_up, source_anime, rating_explicit, high_quality, detailed, "
    "1girl, solo, kitsune, fox_girl, long_hair, white_hair, blunt_bangs, fox_ears, fox_tail, "
    "multiple_tails, red_eyes, looking_at_viewer, closed_mouth, neutral_expression, "
    "military_uniform, peaked_cap, pleated_skirt, black_footwear, full_body, walking, "
    "cherry_blossoms, outdoors, holding_kunai, kunai, holding_weapon, reverse_grip"
)

NEGATIVE = (
    "score_6, score_5, score_4, holding_sword, sword, katana, holding_katana, "
    "greatsword, dual_wielding, scabbard, bad_hands, extra_fingers, open_mouth, blurry"
)

RUNS = [
    {"tag": "tags_d042", "source": "Rin_kitsune_approved.png", "denoise": 0.42, "seed": 424253},
    {"tag": "tags_d048", "source": "Rin_kitsune_approved.png", "denoise": 0.48, "seed": 424254},
    {"tag": "bow_d030", "source": "kitsune_uniform_bow.png", "denoise": 0.30, "seed": 424255},
]


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_kunai_i2i_tags_high.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        requests.get("http://127.0.0.1:8188/system_stats", timeout=60)
        requests.post(
            "http://127.0.0.1:8188/free",
            json={"unload_models": True, "free_memory": True},
            timeout=120,
        )

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 3.0
        engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

        results = []
        for run in RUNS:
            src = PROJECT_DIR / str(run["source"])
            tag = str(run["tag"])
            print(f"=== {tag} from {run['source']} denoise={run['denoise']} ===", flush=True)
            result = engine.generate_image_i2i(
                image_path=str(src),
                prompt=PROMPT,
                style="pony",
                negative_prompt=NEGATIVE,
                width=696,
                height=1024,
                steps=28,
                cfg=5.5,
                seed=int(run["seed"]),
                denoising_strength=float(run["denoise"]),
                sampler="euler_ancestral",
                scheduler="normal",
                face_detail=False,
            )
            dest = PROJECT_DIR / f"Rin_kunai_{tag}.png"
            shutil.copy2(Path(result["saved_files"][0]), dest)
            results.append({**run, "delivered": str(dest)})

        payload = {"status": "success", "runs": results}
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_kunai_i2i_tags_high.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
