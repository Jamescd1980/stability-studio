# -*- coding: utf-8 -*-
"""Pass 3: only 001, 002, 006, 007 — fix dark lighting (1–2) and wet/gloss sun skin (6–7)."""
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
OUT = Path(r"D:\Test Images and Videos\_recreations\pass3")
DELIVERY = Path(
    r"D:\ComfyBox Images and Videos\Video\Jinah Sung Collection\style_recreations\pass3"
)

BASE_NEG = (
    "lowres, bad anatomy, bad hands, text, watermark, blurry, worst quality, "
    "photorealistic, 3d render, plastic skin, extra fingers, logo, signature, "
    "NEURAL ANIME, overexposed, washed out, flat lighting"
)

# Keep pose/BG via ControlNet+IPA; steer grade hard in prompt + DramaticColor.
JOBS = [
    {
        "id": "001",
        "guide": "Test_001.jpg",
        "chars": ["esil_radiru"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.50,
        "canny": 0.58,
        "ipa": 0.78,  # lock dark grade from original
        "extra_loras": [
            {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.40},
            {"file": "ILDetailerV2.safetensors", "weight": 0.50},
        ],
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, dark hair, "
            "dramaticcolor_style, dramaticcolor_vivid, "
            "neon_lighting, glowing, dark_background, rim_lighting, "
            "spot_color, monochrome, muted_color, chiaroscuro, limited_palette, red theme, "
            "gothic lolita close-up, head tilt, mischievous smile, fangs, full lips, defined nose, "
            "specialty eye design: large glowing scarlet crystalline eyes, "
            "sharp horizontal white-yellow light streak across both eyes, perfect eyes, eye_focus, "
            "pale skin with subtle red speculars, low-key lighting, crushed blacks, underexposed face, "
            "red rose hair ornament, black lace, ornate heart red gem choker, "
            "holding glowing red rose with tiny candle flame, floating red petals, "
            "void black background, jewel bloom only, digital_painting, highly detailed"
        ),
        "neg_extra": ", bright daylight, orange fire background, yellow wash, high key, overexposed face, pink neon",
    },
    {
        "id": "002",
        "guide": "Test_002.jpg",
        "chars": ["esil_radiru"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.52,
        "canny": 0.60,
        "ipa": 0.80,
        "extra_loras": [
            {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.42},
            {"file": "ILDetailerV2.safetensors", "weight": 0.50},
        ],
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, dark hair, twin tails, bangs, "
            "dramaticcolor_style, dramaticcolor_vivid, dramaticcolor_crown, "
            "neon_lighting, glowing, dark_background, rim_lighting, colorful, "
            "from below, sitting on ledge, legs crossed, looking down at viewer, "
            "solid glowing red eyes, no pupils visible, perfect eyes, eye_focus, "
            "pale skin tinted by red neon, face underexposed, low-key night scene, "
            "gothic crop top, fishnets, chunky glossy black platform boots reflecting neon red, "
            "vertical neon red tubes, dark red rose vines, night city skyline, "
            "foreground roses bokeh, black and neon-red only palette, crushed blacks, "
            "digital_painting, highly detailed, sharp focus"
        ),
        "neg_extra": (
            ", pink hair, purple hair, blue neon, bright daylight, high key, "
            "overexposed, pastel, orange, yellow background, glowing orbs clutter"
        ),
    },
    {
        "id": "006",
        "guide": "Test_006.jpg",
        "chars": ["fern"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.52,
        "canny": 0.60,
        "ipa": 0.76,
        "extra_loras": [
            {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.55},
            {"file": "ILDetailerV2.safetensors", "weight": 0.55},
        ],
        "prompt": (
            "nb_fern, 1girl, solo, purple hair, long hair, bangs, purple eyes, "
            "standing waist-deep in crystal clear river, looking up at sun, slight smile, "
            "shiny metallic purple bikini with gold ring, purple crystal earrings, gold bangles, "
            "hands near water surface on river stones, "
            "wet glossy sun-kissed skin, bright white specular highlights on shoulders chest and stomach, "
            "water droplets on skin, clear water with sparkling surface glitter, "
            "sharp caustics on pebble riverbed, palm trees left, pine trees right, "
            "distant blue mountain, blue sky cumulus clouds, bright sun lens flare top right, "
            "warm sunlight, high contrast summer glamour, perfect eyes, eye_focus, highly detailed"
        ),
        "neg_extra": ", cool purple shadows, flat matte skin, murky water, oversaturated turquoise sludge, dry skin",
    },
    {
        "id": "007",
        "guide": "Test_007.jpg",
        "chars": ["frieren"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.52,
        "canny": 0.60,
        "ipa": 0.76,
        "extra_loras": [
            {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.55},
            {"file": "ILDetailerV2.safetensors", "weight": 0.55},
        ],
        "prompt": (
            "nb_frieren, 1girl, solo, silver-white hair, long hair in high ponytail, "
            "elf, pointed ears, red teardrop earrings, "
            "white string bikini, eyes closed, blissful smile, head tilted back to sun, "
            "leaning back against dark sunlit lakeside rocks, arms supporting, "
            "mid-thigh in crystal clear turquoise lake, water ripples, "
            "pale wet glossy skin, visible water droplets on shoulders chest and face, "
            "bright specular highlights, warm direct sunlight from upper right, sun lens flare, "
            "pine forest shoreline, deep blue sky with fluffy clouds, "
            "no mountains close behind, summer glamour lighting, highly detailed"
        ),
        "neg_extra": (
            ", blue bikini, light blue swimsuit, lilac hair, purple hair, "
            "matte dry skin, cool shadows, overexposed white blowout, busy mountain backdrop"
        ),
    },
]


def build_loras(catalog, job: dict) -> list[dict]:
    char_w = 0.78
    eye_w = 0.90
    out: list[dict] = []
    for cid in job["chars"]:
        resolved = resolve_character_loras(catalog, cid, include_eye_lora=True)
        if not resolved.get("ok"):
            raise RuntimeError(resolved)
        for row in resolved["loras"]:
            f = str(row.get("file", ""))
            if "Eyes" in f:
                if any("Eyes" in str(x.get("file", "")) for x in out):
                    continue
                out.append({"file": f, "weight": eye_w})
            else:
                out.append({"file": f, "weight": char_w})
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
        print(f"\n===== PASS3 {sid} =====", flush=True)
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
            name = f"pass3_{sid}_{src.name}"
            for dest_dir in (OUT, DELIVERY):
                dest = dest_dir / name
                shutil.copy2(src, dest)
                copied.append(str(dest))
        entry = {"id": sid, "ok": True, "copied": copied, "checkpoint": result.get("checkpoint")}
        results.append(entry)
        print("OK", json.dumps(entry, indent=2), flush=True)

    summary = {"ok": all(r.get("ok") for r in results), "results": results}
    out = ROOT / "outputs" / "style_recreation_stills_pass3.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nDONE", out, flush=True)


if __name__ == "__main__":
    main()
