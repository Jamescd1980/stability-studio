#!/usr/bin/env python3
"""Batch IP-Adapter guided T2I from kitsune reference images (fresh generation)."""

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
from studio.face_detail_assets import check_face_detail_dependencies
from studio.ip_adapter_assets import image_dimensions

STYLE_PROMPTS: dict[str, str] = {
    "3d_cgi": (
        "stylized 3D CGI Pixar Disney animation still, kitsune fox girl, cinematic rim "
        "lighting, soft volumetric glow, detailed fabric fur and hair strands, "
        "white silver hair, sharp red eyes with pupils and highlights, fluffy fox tails, "
        "same outfit and pose as reference, cherry blossom park, masterpiece, ultra detailed"
    ),
    "semireal": (
        "cinematic semi-realistic illustration, kitsune fox girl, natural soft lighting, "
        "white silver hair, red eyes, fox tails, same outfit and pose as reference"
    ),
}

SKIP_SUFFIXES = (
    "_upscaled",
    "_cyberpunk",
    "_semireal",
    "_3d_cgi",
    "_style",
)


def is_original_source(path: Path) -> bool:
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return False
    stem = path.stem.lower()
    return not any(stem.endswith(s) or s in stem for s in SKIP_SUFFIXES)


def reference_image(input_dir: Path, source: Path, prefer_upscaled: bool) -> Path:
    upscaled = input_dir / f"{source.stem}_upscaled.png"
    if prefer_upscaled and upscaled.is_file():
        return upscaled
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=default_delivery_dir())
    parser.add_argument("--style", default="dynavision_3d")
    parser.add_argument("--food-group", default="3d_cgi")
    parser.add_argument("--ip-weight", type=float, default=0.7)
    parser.add_argument(
        "--ip-type",
        default="style and composition",
        help="IP-Adapter weight_type",
    )
    parser.add_argument("--ip-ref-size", type=int, default=512)
    parser.add_argument("--prefer-upscaled-ref", action="store_true", default=True)
    parser.add_argument("--no-prefer-upscaled-ref", action="store_false", dest="prefer_upscaled_ref")
    parser.add_argument("--seed", type=int, default=424242)
    parser.add_argument("--suffix", default="_3d_cgi")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-face-detail", action="store_true")
    args = parser.parse_args()

    cfg, catalog, engine = load_engine()
    comfy_url = cfg.get("comfyui", {}).get("url", "http://127.0.0.1:8188")
    face_ready = check_face_detail_dependencies(cfg, comfy_url).get("ready", False)
    use_face_detail = face_ready and not args.no_face_detail
    if not use_face_detail and not args.no_face_detail:
        print("FaceDetailer not ready — continuing without face pass.", flush=True)

    fg = args.food_group.lower()
    sid = catalog._find_style_key(args.style)
    style_cfg = catalog.styles.get(sid, {})
    prompt = STYLE_PROMPTS.get(fg, STYLE_PROMPTS["3d_cgi"])
    neg = style_cfg.get("negative_prompt") or (
        "lowres, bad anatomy, bad hands, text, watermark, blurry, deformed"
    )
    neg = (
        f"{neg}, dark skin, changed face, wrong eye color, asymmetrical eyes, "
        "cross-eyed, blurry eyes, extra fingers, fused fingers, mitten hands"
    )
    steps = int(style_cfg.get("defaults", {}).get("steps", 30))
    cfg_scale = float(style_cfg.get("defaults", {}).get("cfg", 7.5))

    out_dir = args.output_dir or (args.input / "_staging" / args.suffix.strip("_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(p for p in args.input.iterdir() if p.is_file() and is_original_source(p))
    if not sources:
        print(f"No original sources in {args.input}", file=sys.stderr)
        return 1

    log: list[dict] = []
    for src in sources:
        ref = reference_image(args.input, src, args.prefer_upscaled_ref)
        w, h = image_dimensions(ref)
        dest = out_dir / f"{src.stem}{args.suffix}.png"
        print(
            f"\n=== {src.stem} -> {dest.name} ({w}x{h}) "
            f"[guided T2I ref={ref.name}] ===",
            flush=True,
        )
        try:
            result = engine.generate_image_guided(
                guide_image_path=str(ref),
                prompt=prompt,
                style=args.style,
                negative_prompt=neg,
                width=w,
                height=h,
                steps=steps,
                cfg=cfg_scale,
                seed=args.seed,
                ipadapter_weight=args.ip_weight,
                ipadapter_weight_type=args.ip_type,
                ipadapter_ref_size=args.ip_ref_size,
                face_detail=use_face_detail,
            )
            out = Path((result.get("saved_files") or [""])[0])
            shutil.copy2(out, dest)
            log.append({
                "source": str(src),
                "reference": str(ref),
                "output": str(dest),
                "ok": True,
                "size": [w, h],
                "face_detail": result.get("face_detail"),
            })
            print(f"  -> {dest}", flush=True)
        except Exception as exc:
            log.append({"source": str(src), "reference": str(ref), "ok": False, "error": str(exc)})
            print(f"  FAILED: {exc}", flush=True)

    meta = {
        "run": datetime.now(timezone.utc).isoformat(),
        "pipeline": "guided_txt2img_ipadapter",
        "style": args.style,
        "food_group": args.food_group,
        "ipadapter_weight": args.ip_weight,
        "ipadapter_weight_type": args.ip_type,
        "face_detail": use_face_detail,
        "steps": steps,
        "cfg": cfg_scale,
        "seed": args.seed,
        "results": log,
        "staging_dir": str(out_dir),
        "approved_to_source": False,
    }
    (out_dir / "batch_result.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    ok = sum(1 for e in log if e.get("ok"))
    print(f"\nDone {ok}/{len(sources)} -> staging: {out_dir}")
    print("(Not copied to source folder — review staging outputs before approving.)")
    return 0 if ok == len(sources) else 1


if __name__ == "__main__":
    raise SystemExit(main())
