#!/usr/bin/env python3
"""Upscale + face/eye cleanup for a folder of anime stills (kitsune batch)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
from _bootstrap import ROOT, default_delivery_dir, load_engine  # noqa: E402
from studio.face_detail_assets import check_face_detail_dependencies
from studio.ip_adapter_assets import image_dimensions

CHAR_LOCK = (
    "same kitsune fox girl character, silver white hair, blunt bangs, sharp red eyes, "
    "multiple fluffy white fox tails, consistent face identity, consistent eye shape and color"
)
FACE_PROMPT = (
    f"{CHAR_LOCK}, perfect eyes, detailed symmetrical anime eyes, clean sharp face, "
    "high detail iris, natural eye highlights, masterpiece, best quality"
)
NEG = (
    "lowres, bad anatomy, bad hands, bad eyes, asymmetric eyes, cross-eyed, "
    "deformed face, blurry face, extra pupils, watermark, text"
)
SEED = 424242


def target_size(w: int, h: int, *, max_w: int = 1024, max_h: int = 1216) -> tuple[int, int]:
    """Scale toward GPU cap (prefer modest upscale when headroom exists)."""
    scale = min(max_w / w, max_h / h, 1.35)
    if scale < 1.02:
        scale = min(max_w / w, max_h / h)
    tw = max(512, int(round(w * scale / 8)) * 8)
    th = max(512, int(round(h * scale / 8)) * 8)
    tw = min(tw, max_w)
    th = min(th, max_h)
    return tw, th


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=default_delivery_dir(),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Default: <input>/upscaled",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="Face identity reference (default: Kitsune_uniform.png in input)",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    inp: Path = args.input
    out: Path = args.output or (inp / "upscaled")
    out.mkdir(parents=True, exist_ok=True)

    ref = args.reference or (inp / "Kitsune_uniform.png")
    if not ref.is_file():
        raise FileNotFoundError(f"Reference image not found: {ref}")

    cfg, catalog, engine = load_engine()
    limits = engine.hardware_context().get("generation_limits", {}).get("image", {})
    max_w = int(limits.get("max_width", 1024))
    max_h = int(limits.get("max_height", 1216))

    face_ready = check_face_detail_dependencies(cfg, cfg["comfyui"]["url"]).get("ready", False)

    images = sorted(
        p for p in inp.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg"} and p.parent == inp
    )
    if not images:
        print(f"No images in {inp}", file=sys.stderr)
        return 1

    log: list[dict] = []
    for src in images:
        w, h = image_dimensions(src)
        tw, th = target_size(w, h, max_w=max_w, max_h=max_h)
        entry: dict = {
            "source": str(src),
            "source_size": [w, h],
            "target_size": [tw, th],
            "stages": [],
        }
        print(f"\n=== {src.name} ({w}x{h} -> {tw}x{th}) ===", flush=True)

        # Stage 1: upscale + refine (i2i)
        try:
            s1 = engine.generate_image_i2i(
                image_path=str(src),
                prompt=FACE_PROMPT,
                style="ilustmix",
                negative_prompt=NEG,
                width=tw,
                height=th,
                steps=28,
                denoising_strength=0.38,
                seed=args.seed,
                face_detail=face_ready,
            )
            up_path = Path((s1.get("saved_files") or [""])[0])
            entry["stages"].append({"stage": "upscale_i2i", "ok": True, "output": str(up_path)})
            print(f"  upscale -> {up_path.name}", flush=True)
        except Exception as exc:
            entry["stages"].append({"stage": "upscale_i2i", "ok": False, "error": str(exc)})
            log.append(entry)
            print(f"  upscale FAILED: {exc}", flush=True)
            continue

        working = str(up_path)

        # Stage 2: face/eye inpaint with IP-Adapter identity lock
        try:
            s2 = engine.inpaint_advanced(
                image_path=working,
                prompt=FACE_PROMPT,
                reference_image_path=str(ref),
                mask_region="top_third",
                style="ilustmix",
                negative_prompt=NEG,
                width=tw,
                height=th,
                steps=26,
                denoising_strength=0.42,
                ipadapter_weight=0.78,
                seed=args.seed,
            )
            final_path = Path((s2.get("saved_files") or [""])[0])
            dest = out / f"{src.stem}_upscaled.png"
            shutil.copy2(final_path, dest)
            entry["stages"].append({"stage": "face_inpaint", "ok": True, "output": str(dest)})
            entry["final"] = str(dest)
            print(f"  face pass -> {dest}", flush=True)
        except Exception as exc:
            dest = out / f"{src.stem}_upscaled.png"
            shutil.copy2(up_path, dest)
            entry["stages"].append({"stage": "face_inpaint", "ok": False, "error": str(exc), "fallback": str(dest)})
            entry["final"] = str(dest)
            print(f"  face pass FAILED (kept upscale): {exc}", flush=True)

        log.append(entry)

    meta = {
        "run": datetime.now(timezone.utc).isoformat(),
        "reference": str(ref),
        "seed": args.seed,
        "face_detail_on_i2i": face_ready,
        "style": "ilustmix",
        "images": log,
    }
    (out / "batch_result.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    ok = len([e for e in log if e.get("final")])
    print(f"\nDone. {ok}/{len(images)} written to {out}")

    setup = ROOT / "outputs" / "batch_upscale_setup.json"
    setup.parent.mkdir(parents=True, exist_ok=True)
    setup.write_text(
        json.dumps(
            {
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "images_processed": ok,
                "input_dir": str(inp),
                "output_dir": str(out),
                "reference": str(ref),
                "seed": args.seed,
                "status": "complete",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
