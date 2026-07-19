# -*- coding: utf-8 -*-
"""Batch T2I: recreate Test 001–007 style with canvas character mapping + style LoRAs."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog
from studio.character_loras import resolve_character_loras
from studio.config import catalog_path, load_config
from studio.engine import GenerationEngine

OUT = Path(r"D:\Test Images and Videos\_recreations")
DELIVERY = Path(r"D:\ComfyBox Images and Videos\Video\Jinah Sung Collection\style_recreations")

NEG = (
    "lowres, bad anatomy, bad hands, text, watermark, blurry, worst quality, "
    "photorealistic, 3d render, plastic skin, extra fingers"
)

# Canvas mapping + style LoRAs. First pass T2I; I2I refine later if needed.
JOBS = [
    {
        "id": "001",
        "chars": ["esil_radiru"],
        "style": "waijfu",
        "width": 896,
        "height": 1344,
        "cfg": 7.0,
        "extra_loras": [
            {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.35},
            {"file": "ILDetailerV2.safetensors", "weight": 0.65},
        ],
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, blonde hair, red eyes, "
            "dramaticcolor_style, dramaticcolor_vivid, spot_color, monochrome, "
            "muted_color, chiaroscuro, limited_palette, red theme, "
            "gothic vampire close-up, pale skin, fangs, holding a red rose, "
            "glowing red eyes, crimson rim light, crushed blacks, void background, "
            "lace details, sharp iris, eye bloom, light streak, digital_painting, "
            "concept_art, highly detailed, intricate, sharp focus, absurdres, highres, "
            "perfect eyes, eye_focus"
        ),
    },
    {
        "id": "002",
        "chars": ["esil_radiru"],
        "style": "waijfu",
        "width": 832,
        "height": 1472,
        "cfg": 6.5,
        "extra_loras": [
            {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.35},
            {"file": "ILDetailerV2.safetensors", "weight": 0.65},
        ],
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, blonde hair, red eyes, "
            "dramaticcolor_style, dramaticcolor_vivid, dramaticcolor_crown, "
            "neon_lighting, glowing, dark_background, rim_lighting, colorful, "
            "cyber gothic, from below, worm's eye view, neon red backlight, "
            "face slightly underexposed, red roses in foreground, fishnets, "
            "buckles, gothic lolita, bokeh background, digital_painting, concept_art, "
            "highly detailed, sharp focus, absurdres, highres, perfect eyes"
        ),
    },
    {
        "id": "003",
        "chars": ["park_heejin"],
        "style": "waijfu",
        "width": 832,
        "height": 1472,
        "cfg": 6.0,
        "extra_loras": [
            {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.55},
            {"file": "ILDetailerV2.safetensors", "weight": 0.65},
        ],
        "prompt": (
            "nb_park_heejin, 1girl, solo, blonde hair, long hair, yellow eyes, "
            "prism light, shadows, summer suncore close-up, sun hat, dappled sunlight, "
            "harsh sun, extreme bloom, prism flares, light leaks, golden hour, "
            "warm skin, sparkling eyes, micro hair detail, soft smile, outdoors, "
            "looking at viewer, masterpiece, best quality, perfect eyes, eye_focus"
        ),
    },
    {
        "id": "004",
        "chars": ["fern", "frieren"],
        "style": "waijfu",
        "width": 848,
        "height": 1424,
        "cfg": 6.5,
        "char_weight": 0.7,
        "extra_loras": [
            {"file": "AquaInk_Watercolor_IL.safetensors", "weight": 0.9},
        ],
        "prompt": (
            "nb_fern, nb_frieren, 2girls, fern and frieren, "
            "wc_painting, watercolor, traditional media, watercolor (medium), "
            "paper texture, soft edges, color bleeding, loose brushwork, painterly, "
            "streetwear fashion, back to back, full body, urban sidewalk, "
            "soft high-key daylight, cool shadow tint, sketchy line weight, "
            "fashion illustration, masterpiece, best quality"
        ),
        "negative_extra": "ink stains, ink drips, color stains on clothes, messy, dirty clothes",
    },
    {
        "id": "005",
        "chars": ["esil_radiru"],
        "style": "n4mik4",
        "width": 896,
        "height": 1344,
        "cfg": 7.0,
        "extra_loras": [
            {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.35},
            {"file": "ILDetailerV2.safetensors", "weight": 0.7},
        ],
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, "
            "white hair, silver hair, glowing cyan eyes, "
            "dramaticcolor_style, dramaticcolor_vivid, dramaticcolor_crown, "
            "neon_lighting, glowing, dark_background, rim_lighting, colorful, "
            "cyber dutch angle extreme close-up, cyan key light, magenta rim light, "
            "self-glow eyes, ultra sharp center, futuristic makeup, digital_painting, "
            "concept_art, highly detailed, sharp focus, absurdres, highres, perfect eyes"
        ),
    },
    {
        "id": "006",
        "chars": ["fern"],
        "style": "waijfu",
        "width": 1152,
        "height": 1536,
        "cfg": 6.0,
        "extra_loras": [
            {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.45},
            {"file": "ILDetailerV2.safetensors", "weight": 0.6},
        ],
        "prompt": (
            "nb_fern, 1girl, solo, purple hair, long hair, purple eyes, "
            "prism light, shadows, wearing bikini, standing in shallow river, "
            "looking up at the sun, sunlight on face, sparkling water, "
            "summer afternoon, warm glow, detailed wet skin, natural pose, "
            "masterpiece, best quality, perfect eyes"
        ),
    },
    {
        "id": "007",
        "chars": ["frieren"],
        "style": "waijfu",
        "width": 1152,
        "height": 1536,
        "cfg": 6.0,
        "extra_loras": [
            {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.45},
            {"file": "ILDetailerV2.safetensors", "weight": 0.6},
        ],
        "prompt": (
            "nb_frieren, 1girl, solo, white hair, long hair, green eyes, elf, "
            "prism light, shadows, wearing bikini, sunbathing by a lake, "
            "eyes closed, peaceful expression, sunlight, sparkling water, "
            "summer afternoon, warm glow, masterpiece, best quality, perfect eyes"
        ),
    },
]


def build_loras(catalog, job: dict) -> list[dict]:
    char_w = float(job.get("char_weight", 0.8))
    eye_w = 0.75
    out: list[dict] = []
    for cid in job["chars"]:
        resolved = resolve_character_loras(catalog, cid, include_eye_lora=True)
        if not resolved.get("ok"):
            raise RuntimeError(resolved)
        for i, row in enumerate(resolved["loras"]):
            w = eye_w if "Eyes" in str(row.get("file", "")) else char_w
            # only add eyes once
            if "Eyes" in str(row.get("file", "")) and any(
                "Eyes" in str(x.get("file", "")) for x in out
            ):
                continue
            out.append({"file": row["file"], "weight": w})
    for row in job.get("extra_loras") or []:
        out.append(dict(row))
    return out


def main() -> None:
    cfg = load_config()
    catalog_obj = StyleCatalog(catalog_path(cfg), cfg)
    engine = GenerationEngine(cfg, catalog_obj)
    catalog = catalog_obj._data  # noqa: SLF001
    OUT.mkdir(parents=True, exist_ok=True)
    DELIVERY.mkdir(parents=True, exist_ok=True)

    results = []
    for job in JOBS:
        sid = job["id"]
        print(f"\n===== STILL {sid} =====", flush=True)
        loras = build_loras(catalog, job)
        print("loras", json.dumps(loras), flush=True)
        neg = NEG
        if job.get("negative_extra"):
            neg = NEG + ", " + job["negative_extra"]
        try:
            result = engine.generate_image(
                prompt=job["prompt"],
                style=job["style"],
                negative_prompt=neg,
                loras=loras,
                width=int(job["width"]),
                height=int(job["height"]),
                cfg=float(job["cfg"]),
                steps=28,
                face_detail=True,
                backend="comfyui",
                content_rating="open",
            )
        except Exception as exc:
            print(f"FAIL {sid}: {exc}", flush=True)
            results.append({"id": sid, "ok": False, "error": str(exc)})
            continue

        saved = result.get("saved_files") or result.get("images") or []
        copied = []
        for p in saved:
            src = Path(str(p))
            if not src.is_file():
                continue
            name = f"recreate_{sid}_{src.name}"
            for dest_dir in (OUT, DELIVERY):
                dest = dest_dir / name
                shutil.copy2(src, dest)
                copied.append(str(dest))
        entry = {
            "id": sid,
            "ok": True,
            "style": job["style"],
            "chars": job["chars"],
            "loras": loras,
            "saved": saved,
            "copied": copied,
            "seed": result.get("seed"),
            "checkpoint": result.get("checkpoint"),
        }
        results.append(entry)
        print("OK", json.dumps(entry, indent=2)[:1200], flush=True)

    summary = {"ok": all(r.get("ok") for r in results), "results": results}
    out_json = ROOT / "outputs" / "style_recreation_stills_batch.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nDONE", out_json, flush=True)
    print(json.dumps(summary, indent=2)[:4000], flush=True)


if __name__ == "__main__":
    main()
