#!/usr/bin/env python3
"""Batch i2i art-style transfer (e.g. cyberpunk) from upscaled sources."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
from _bootstrap import default_delivery_dir, load_engine  # noqa: E402
from studio.ip_adapter_assets import image_dimensions

STYLE_PROMPTS: dict[str, str] = {
    "semireal": (
        "semi-realistic cosplay photograph, kitsune fox girl portrait, natural skin texture, "
        "soft cinematic lighting, shallow depth of field, 85mm lens, "
        "identical face structure, same pale fair skin tone, same sharp red eyes, "
        "same silver white hair, same outfit and pose, preserve character likeness"
    ),
    "3d_cgi": (
        "subtle 3D CGI polish, soft stylized animation render, kitsune fox girl, "
        "identical face, same eye shape and red eye color, same pale fair skin tone, "
        "same silver white hair, same outfit and pose, preserve likeness, gentle CGI lighting only"
    ),
    "cyberpunk": (
        "cyberpunk kitsune fox girl, neon dystopia, holographic UI accents, chrome and synth-leather, "
        "rain-soaked neon city bokeh, magenta and cyan rim light, sci-fi atmosphere, "
        "same character pose and framing, cinematic illustration"
    ),
    "fantasy": (
        "high fantasy kitsune fox girl, ethereal magical glow, enchanted atmosphere, "
        "same character pose and framing, painterly fantasy illustration"
    ),
    "photoreal": (
        "photorealistic kitsune cosplay portrait, cinematic natural lighting, "
        "same pose and framing, highly detailed"
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=default_delivery_dir())
    parser.add_argument("--glob", default="*_upscaled.png")
    parser.add_argument("--style", default="n4mik4", help="Catalog style id")
    parser.add_argument("--food-group", default="cyberpunk", help="For logging only")
    parser.add_argument("--denoise", type=float, default=0.52)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--cfg", type=float, default=None)
    parser.add_argument("--seed", type=int, default=424242)
    parser.add_argument("--face-detail", action="store_true", help="Run FaceDetailer pass after i2i")
    parser.add_argument("--suffix", default="_cyberpunk")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Staging folder for outputs (default: <input>/_staging/<suffix>)",
    )
    args = parser.parse_args()

    cfg, catalog, engine = load_engine()

    fg = args.food_group.lower()
    sid = catalog._find_style_key(args.style)
    style_cfg = catalog.styles.get(sid, {})
    prompt = STYLE_PROMPTS.get(fg, STYLE_PROMPTS.get(sid, STYLE_PROMPTS["cyberpunk"]))
    neg = style_cfg.get("negative_prompt") or (
        "lowres, bad anatomy, bad hands, bad eyes, text, watermark, blurry, "
        "flat lighting, oversaturated, duplicate face"
    )
    if fg in {"3d_cgi", "semireal"}:
        neg = (
            f"{neg}, dark skin, tan skin, brown skin, different face, changed face, "
            "wrong eye color, asymmetrical eyes, cross-eyed, blurry eyes, heavy shadows on face"
        )
    steps = args.steps or int(style_cfg.get("defaults", {}).get("steps", 28))
    cfg_scale = args.cfg if args.cfg is not None else float(style_cfg.get("defaults", {}).get("cfg", 7.0))

    out_dir = args.output_dir or (args.input / "_staging" / args.suffix.strip("_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(args.input.glob(args.glob))
    if not sources:
        print(f"No files matching {args.glob} in {args.input}", file=sys.stderr)
        return 1

    log: list[dict] = []
    for src in sources:
        w, h = image_dimensions(src)
        stem = src.stem.replace("_upscaled", "")
        dest = out_dir / f"{stem}{args.suffix}.png"
        print(f"\n=== {src.name} -> {dest.name} ({w}x{h}) ===", flush=True)
        try:
            result = engine.generate_image_i2i(
                image_path=str(src),
                prompt=prompt,
                style=args.style,
                negative_prompt=neg,
                width=w,
                height=h,
                steps=steps,
                cfg=cfg_scale,
                denoising_strength=args.denoise,
                seed=args.seed,
                face_detail=args.face_detail,
            )
            out = Path((result.get("saved_files") or [""])[0])
            shutil.copy2(out, dest)
            log.append({"source": str(src), "output": str(dest), "ok": True, "size": [w, h]})
            print(f"  -> {dest}", flush=True)
        except Exception as exc:
            log.append({"source": str(src), "ok": False, "error": str(exc)})
            print(f"  FAILED: {exc}", flush=True)

    meta = {
        "run": datetime.now(timezone.utc).isoformat(),
        "style": args.style,
        "food_group": args.food_group,
        "denoise": args.denoise,
        "steps": steps,
        "cfg": cfg_scale,
        "face_detail": args.face_detail,
        "seed": args.seed,
        "results": log,
    }
    meta_path = out_dir / "batch_result.json"
    meta["staging_dir"] = str(out_dir)
    meta["approved_to_source"] = False
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    ok = sum(1 for e in log if e.get("ok"))
    print(f"\nDone {ok}/{len(sources)} -> staging: {out_dir}")
    print("(Not copied to source folder — review staging outputs before approving.)")
    return 0 if ok == len(sources) else 1


if __name__ == "__main__":
    raise SystemExit(main())
