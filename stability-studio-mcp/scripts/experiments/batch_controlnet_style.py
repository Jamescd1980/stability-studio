#!/usr/bin/env python3
"""Batch ControlNet + IP-Adapter T2I style conversion from original sources."""

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
    "semireal": (
        "cinematic semi-realistic illustration, kitsune fox girl cosplay portrait, "
        "natural soft lighting, detailed skin texture, sharp symmetrical red eyes with "
        "clear pupils and highlights, white silver hair, fluffy white fox tails, "
        "cherry blossom park, same pose and framing, highly detailed face and hands"
    ),
    "photoreal": (
        "photorealistic cosplay portrait, kitsune fox girl, natural lighting, "
        "white silver hair, red eyes, fox tails, same pose and composition"
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


def identity_reference(input_dir: Path, source: Path, global_ref: Path | None) -> Path:
    if global_ref and global_ref.is_file():
        return global_ref
    upscaled = input_dir / f"{source.stem}_upscaled.png"
    if upscaled.is_file():
        return upscaled
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=default_delivery_dir())
    parser.add_argument("--style", default="juggernaut", help="Catalog style id")
    parser.add_argument("--food-group", default="semireal")
    parser.add_argument("--depth", type=float, default=0.55)
    parser.add_argument("--canny", type=float, default=0.4)
    parser.add_argument("--ip-weight", type=float, default=0.72)
    parser.add_argument(
        "--identity-ref",
        type=Path,
        default=None,
        help="Global IP-Adapter identity ref (default: per-image *_upscaled.png or source)",
    )
    parser.add_argument("--seed", type=int, default=424242)
    parser.add_argument("--suffix", default="_semireal")
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
    prompt = STYLE_PROMPTS.get(fg, STYLE_PROMPTS["semireal"])
    neg = style_cfg.get("negative_prompt") or (
        "lowres, bad anatomy, bad hands, text, watermark, blurry, deformed"
    )
    neg = (
        f"{neg}, asymmetrical eyes, cross-eyed, blurry eyes, dead eyes, "
        "extra fingers, fused fingers, missing fingers, mitten hands, wrong eye color"
    )
    steps = int(style_cfg.get("defaults", {}).get("steps", 30))
    cfg_scale = float(style_cfg.get("defaults", {}).get("cfg", 6.0))

    out_dir = args.output_dir or (args.input / "_staging" / args.suffix.strip("_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(p for p in args.input.iterdir() if p.is_file() and is_original_source(p))
    if not sources:
        print(f"No original sources in {args.input}", file=sys.stderr)
        return 1

    log: list[dict] = []
    for src in sources:
        w, h = image_dimensions(src)
        dest = out_dir / f"{src.stem}{args.suffix}.png"
        ip_ref = identity_reference(args.input, src, args.identity_ref)
        print(
            f"\n=== {src.name} -> {dest.name} ({w}x{h}) "
            f"[controlnet+ip ref={ip_ref.name}] ===",
            flush=True,
        )
        try:
            result = engine.generate_image_controlnet(
                guide_image_path=str(src),
                reference_image_path=str(ip_ref),
                prompt=prompt,
                style=args.style,
                negative_prompt=neg,
                width=w,
                height=h,
                steps=steps,
                cfg=cfg_scale,
                seed=args.seed,
                depth_strength=args.depth,
                canny_strength=args.canny,
                ipadapter_weight=args.ip_weight,
                face_detail=use_face_detail,
            )
            out = Path((result.get("saved_files") or [""])[0])
            shutil.copy2(out, dest)
            log.append({
                "source": str(src),
                "identity_ref": str(ip_ref),
                "output": str(dest),
                "ok": True,
                "size": [w, h],
                "face_detail": result.get("face_detail"),
            })
            print(f"  -> {dest}", flush=True)
        except Exception as exc:
            log.append({"source": str(src), "ok": False, "error": str(exc)})
            print(f"  FAILED: {exc}", flush=True)

    meta = {
        "run": datetime.now(timezone.utc).isoformat(),
        "pipeline": "controlnet_ipadapter",
        "style": args.style,
        "food_group": args.food_group,
        "depth_strength": args.depth,
        "canny_strength": args.canny,
        "ipadapter_weight": args.ip_weight,
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
