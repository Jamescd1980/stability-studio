#!/usr/bin/env python3
"""Local capability probe — not required for MCP users."""

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
    "completely nude kitsune fox girl, full frontal nudity, no clothing, no armor, "
    "natural anatomy, visible breasts and vagina, white hair, red eyes, fox ears and tails, "
    "cherry blossom background, masterpiece"
)
NEG = (
    "armor, clothing, bikini, panties, covered nipples, covered vagina, censorship, "
    "red orbs, hands covering body, fabric, underwear, deformed, bad anatomy"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", type=Path, required=True, help="Reference image")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Default: <delivery>/_staging/_verify",
    )
    args = parser.parse_args()

    out_dir = args.output_dir or (default_delivery_dir() / "_staging" / "_verify")
    cfg, _, engine = load_engine()
    face_ready = check_face_detail_dependencies(cfg, cfg["comfyui"]["url"]).get("ready", False)

    out_dir.mkdir(parents=True, exist_ok=True)
    w, h = image_dimensions(args.ref)

    result = engine.generate_image_guided(
        guide_image_path=str(args.ref),
        prompt=PROMPT,
        style="dynavision_3d",
        negative_prompt=NEG,
        width=w,
        height=h,
        steps=30,
        cfg=7.5,
        seed=424246,
        ipadapter_weight=0.6,
        face_detail=face_ready,
    )

    dest = out_dir / "nude_test_dynavision.png"
    shutil.copy2(result["saved_files"][0], dest)
    print(f"Saved: {dest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
