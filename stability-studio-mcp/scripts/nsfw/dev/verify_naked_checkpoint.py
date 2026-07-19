#!/usr/bin/env python3
"""A/B checkpoint comparison — local dev only."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
from _bootstrap import default_delivery_dir, load_engine  # noqa: E402
from studio.face_detail_assets import check_face_detail_dependencies
from studio.ip_adapter_assets import image_dimensions

PROMPT = (
    "stylized 3D CGI Pixar Disney animation still, kitsune fox girl, cinematic lighting, "
    "white silver hair, red eyes, fluffy fox tails with blue tips, cherry blossom park, "
    "same pose and framing as reference, nude, natural anatomy, masterpiece"
)
EXTRA_NEG = (
    ", red orbs, censorship dots, random jewelry on chest, bikini, panties, "
    "asymmetrical eyes, fused fingers, mitten hands"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    out = args.output_dir or (default_delivery_dir() / "_staging" / "_verify")
    cfg, catalog, engine = load_engine()
    face = check_face_detail_dependencies(cfg, cfg["comfyui"]["url"]).get("ready", False)
    out.mkdir(parents=True, exist_ok=True)
    w, h = image_dimensions(args.ref)

    for style in ("dynavision_3d", "juggernaut", "ilustmix"):
        sid = catalog._find_style_key(style)
        sc = catalog.styles[sid]
        neg = (sc.get("negative_prompt") or "") + EXTRA_NEG
        steps = int(sc.get("defaults", {}).get("steps", 30))
        cfg_scale = float(sc.get("defaults", {}).get("cfg", 7.0))
        print(f"\n=== {style} ===", flush=True)
        result = engine.generate_image_guided(
            guide_image_path=str(args.ref),
            prompt=PROMPT,
            style=style,
            negative_prompt=neg,
            width=w,
            height=h,
            steps=steps,
            cfg=cfg_scale,
            seed=424243,
            ipadapter_weight=0.7,
            face_detail=face,
        )
        dest = out / f"ab_{style}.png"
        shutil.copy2(result["saved_files"][0], dest)
        print(f"  -> {dest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
