#!/usr/bin/env python3
"""Probe: fresh Pony t2i with holding_kunai (proves tags work without locked i2i source)."""
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
    "multiple_tails, red_eyes, looking_at_viewer, military_uniform, peaked_cap, pleated_skirt, "
    "full_body, walking, cherry_blossoms, outdoors, holding_kunai, kunai, holding_weapon, reverse_grip"
)

NEGATIVE = "holding_sword, sword, katana, bad_hands, blurry, lowres"


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_kunai_t2i_probe.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        requests.get("http://127.0.0.1:8188/system_stats", timeout=60)

        cfg = load_config()
        engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

        result = engine.generate_image(
            prompt=PROMPT,
            style="pony",
            negative_prompt=NEGATIVE,
            width=696,
            height=1024,
            seed=424260,
            steps=28,
            cfg=5.5,
            sampler="euler_ancestral",
            scheduler="normal",
        )
        dest = PROJECT_DIR / "Rin_kunai_t2i_probe.png"
        shutil.copy2(Path(result["saved_files"][0]), dest)
        payload = {"status": "success", "delivered": str(dest), "note": "fresh t2i — not chained to approved still"}
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
