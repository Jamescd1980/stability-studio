#!/usr/bin/env python3
"""Pony i2i with Danbooru weapon tags (holding_kunai) — no inpaint."""
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

BASE_CHAR = (
    "1girl, solo, kitsune, fox_girl, long_hair, white_hair, blunt_bangs, "
    "fox_ears, fox_tail, multiple_tails, red_eyes, looking_at_viewer, "
    "closed_mouth, neutral_expression, military_uniform, peaked_cap, "
    "pleated_skirt, black_footwear, full_body, walking, cherry_blossoms, outdoors"
)

WEAPON_TAGS = "holding_kunai, kunai, holding_weapon, reverse_grip, arm_at_side"

NEGATIVE = (
    "score_6, score_5, score_4, holding_sword, sword, katana, holding_katana, "
    "greatsword, dual_wielding, scabbard, long_sword, blade, "
    "bad_hands, extra_fingers, missing_fingers, mutated_hands, "
    "open_mouth, bad_eyes, blurry, lowres"
)

VARIANTS = [
    {"tag": "tags_d028", "denoise": 0.28, "seed": 424249},
    {"tag": "tags_d032", "denoise": 0.32, "seed": 424250},
    {"tag": "tags_d035", "denoise": 0.35, "seed": 424252},
]


def build_prompt() -> str:
    return (
        f"score_9, score_8_up, score_7_up, source_anime, rating_explicit, "
        f"high_quality, detailed, {BASE_CHAR}, {WEAPON_TAGS}"
    )


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_kunai_i2i_tags.json"
    research = MCP_ROOT / "outputs" / "rin_weapon_prompt_research.json"
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

        prompt = build_prompt()
        runs = []
        for v in VARIANTS:
            tag = str(v["tag"])
            print(f"=== pony i2i {tag} denoise={v['denoise']} ===", flush=True)
            result = engine.generate_image_i2i(
                image_path=str(SOURCE),
                prompt=prompt,
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
            dest = PROJECT_DIR / f"Rin_kunai_{tag}.png"
            shutil.copy2(Path(result["saved_files"][0]), dest)
            runs.append({**v, "delivered": str(dest), "prompt": prompt})

        payload = {
            "status": "success",
            "approach": "danbooru tags holding_kunai + kunai + holding_weapon",
            "research": str(research),
            "runs": runs,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_kunai_i2i_tags.json")
        shutil.copy2(research, PROJECT_DIR / "rin_weapon_prompt_research.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
