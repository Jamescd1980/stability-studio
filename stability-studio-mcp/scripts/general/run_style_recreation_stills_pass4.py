# -*- coding: utf-8 -*-
"""Pass 4: 001/002/006/007 with ZH Glow Eyes + Dlang Detailed Eyes + Wet Skin."""
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

CONV = Path(r"D:\Test Images and Videos\_conv")
OUT = Path(r"D:\Test Images and Videos\_recreations\pass4")
DELIVERY = Path(
    r"D:\ComfyBox Images and Videos\Video\Jinah Sung Collection\style_recreations\pass4"
)

BASE_NEG = (
    "lowres, bad anatomy, bad hands, text, watermark, blurry, worst quality, "
    "photorealistic, 3d render, plastic skin, extra fingers, logo, signature, "
    "NEURAL ANIME, overexposed, washed out"
)

GLOW = {"file": "ZH_GlowEyes_IL.safetensors", "weight": 0.85}
DLANG = {"file": "Dlang_DetailedEyes_IL.safetensors", "weight": 0.75}
WET = {"file": "SweatyStyle_WetSkin_IL.safetensors", "weight": 0.9}
DRAMATIC = {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.38}
FLARE = {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.50}
DETAIL = {"file": "ILDetailerV2.safetensors", "weight": 0.45}

JOBS = [
    {
        "id": "001",
        "guide": "Test_001.jpg",
        "chars": ["esil_radiru"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.50,
        "canny": 0.58,
        "ipa": 0.76,
        "extra_loras": [GLOW, DLANG, DRAMATIC, DETAIL],
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, dark hair, "
            "ZH_Glow3y3s, glowing, glowing eyes, "
            "detailed eyes, magic eyes, iris and pupil, soft shimmer on the iris, "
            "dramaticcolor_style, dramaticcolor_vivid, "
            "neon_lighting, glowing, dark_background, rim_lighting, "
            "chiaroscuro, limited_palette, red theme, "
            "gothic lolita close-up, head tilt, mischievous smile, fangs, full lips, "
            "large glowing scarlet crystalline eyes, "
            "sharp horizontal white-yellow light streak across both eyes, "
            "perfect eyes, eye_focus, eye focus, "
            "pale skin red speculars, low-key lighting, crushed blacks, underexposed face, "
            "red rose hair ornament, black lace, ornate heart red gem choker, "
            "holding glowing red rose, floating red petals, void black background, "
            "highly detailed, sharp focus"
        ),
        "neg_extra": ", bright daylight, orange fire wash, yellow background, high key, pink neon, dull eyes",
    },
    {
        "id": "002",
        "guide": "Test_002.jpg",
        "chars": ["esil_radiru"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.52,
        "canny": 0.60,
        "ipa": 0.78,
        "extra_loras": [GLOW, DLANG, DRAMATIC, DETAIL],
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, dark hair, twin tails, bangs, "
            "ZH_Glow3y3s, glowing, glowing eyes, "
            "detailed eyes, magic eyes, soft shimmer on the iris, "
            "dramaticcolor_style, dramaticcolor_vivid, dramaticcolor_crown, "
            "neon_lighting, dark_background, rim_lighting, "
            "from below, sitting on ledge, legs crossed, looking down at viewer, "
            "solid glowing red eyes, perfect eyes, eye_focus, "
            "pale skin tinted by red neon, face underexposed, low-key night, "
            "gothic crop top, fishnets, glossy black platform boots reflecting neon red, "
            "vertical neon red tubes, dark red rose vines, night city skyline, "
            "black and neon-red palette, crushed blacks, highly detailed"
        ),
        "neg_extra": ", pink hair, purple hair, blue neon, bright daylight, high key, dull eyes, orange",
    },
    {
        "id": "006",
        "guide": "Test_006.jpg",
        "chars": ["fern"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.52,
        "canny": 0.60,
        "ipa": 0.74,
        "extra_loras": [WET, DLANG, FLARE, DETAIL],
        "prompt": (
            "nb_fern, 1girl, solo, purple hair, long hair, bangs, purple eyes, "
            "SweatyStyle, wet, shiny skin, glistening skin, "
            "detailed eyes, soft shimmer on the iris, perfect eyes, eye_focus, "
            "standing waist-deep in crystal clear river, looking up at sun, slight smile, "
            "shiny metallic purple bikini with gold ring, purple crystal earrings, gold bangles, "
            "wet glossy sun-kissed skin, bright white specular highlights on shoulders chest stomach, "
            "water droplets on skin, sparkling water surface, sharp caustics on pebble riverbed, "
            "palm trees left, pine trees right, distant blue mountain, "
            "blue sky, bright sun lens flare top right, warm sunlight, highly detailed"
        ),
        "neg_extra": ", dry matte skin, cool purple sludge shadows, murky water, dull eyes",
    },
    {
        "id": "007",
        "guide": "Test_007.jpg",
        "chars": ["frieren"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.52,
        "canny": 0.60,
        "ipa": 0.74,
        "extra_loras": [WET, DLANG, FLARE, DETAIL],
        "prompt": (
            "nb_frieren, 1girl, solo, silver-white hair, long hair in high ponytail, "
            "elf, pointed ears, red teardrop earrings, "
            "SweatyStyle, wet, shiny skin, glistening skin, "
            "white string bikini, eyes closed, blissful smile, head tilted back to sun, "
            "leaning back against dark sunlit lakeside rocks, arms supporting, "
            "mid-thigh in crystal clear turquoise lake, "
            "pale wet glossy skin, visible water droplets on shoulders chest and face, "
            "bright specular highlights, warm direct sunlight, sun lens flare, "
            "pine forest shoreline, deep blue sky fluffy clouds, highly detailed"
        ),
        "neg_extra": ", blue bikini, lilac hair, purple hair, dry matte skin, busy mountains",
    },
]


def build_loras(catalog, job: dict) -> list[dict]:
    out: list[dict] = []
    for cid in job["chars"]:
        resolved = resolve_character_loras(catalog, cid, include_eye_lora=True)
        if not resolved.get("ok"):
            raise RuntimeError(resolved)
        for row in resolved["loras"]:
            f = str(row.get("file", ""))
            if "Eyes" in f:
                # keep base eyes LoRA but slightly lower — ZH/Dlang carry the design
                if any("Eyes_for_Illustrious" in str(x.get("file", "")) for x in out):
                    continue
                out.append({"file": f, "weight": 0.70})
            else:
                out.append({"file": f, "weight": 0.78})
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
        guide = CONV / job["guide"]
        print(f"\n===== PASS4 {sid} =====", flush=True)
        loras = build_loras(catalog, job)
        neg = BASE_NEG + (job.get("neg_extra") or "")
        print("loras", json.dumps(loras), flush=True)
        try:
            result = engine.generate_image_controlnet(
                guide_image_path=str(guide),
                prompt=job["prompt"],
                style=job["style"],
                negative_prompt=neg,
                loras=loras,
                cfg=float(job["cfg"]),
                steps=30,
                depth_strength=float(job["depth"]),
                canny_strength=float(job["canny"]),
                reference_image_path=str(guide),
                ipadapter_weight=float(job["ipa"]),
                ipadapter_weight_type="style and composition",
                face_detail=False,
                backend="comfyui",
                content_rating="open",
            )
        except Exception as exc:
            print(f"FAIL {sid}: {exc}", flush=True)
            results.append({"id": sid, "ok": False, "error": str(exc)})
            continue

        saved = result.get("saved_files") or []
        copied = []
        for p in saved:
            src = Path(str(p))
            if not src.is_file():
                continue
            name = f"pass4_{sid}_{src.name}"
            for dest_dir in (OUT, DELIVERY):
                dest = dest_dir / name
                shutil.copy2(src, dest)
                copied.append(str(dest))
        entry = {"id": sid, "ok": True, "copied": copied, "checkpoint": result.get("checkpoint")}
        results.append(entry)
        print("OK", json.dumps(entry, indent=2), flush=True)

    summary = {"ok": all(r.get("ok") for r in results), "results": results}
    out = ROOT / "outputs" / "style_recreation_stills_pass4.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nDONE", out, flush=True)


if __name__ == "__main__":
    main()
