# -*- coding: utf-8 -*-
"""Pass 2: lock pose/BG/lighting from Test refs via ControlNet + IP-Adapter; keep strong eyes."""
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
OUT = Path(r"D:\Test Images and Videos\_recreations\pass2")
DELIVERY = Path(
    r"D:\ComfyBox Images and Videos\Video\Jinah Sung Collection\style_recreations\pass2"
)

BASE_NEG = (
    "lowres, bad anatomy, bad hands, text, watermark, blurry, worst quality, "
    "photorealistic, 3d render, plastic skin, extra fingers, logo, signature, "
    "NEURAL ANIME, watermark text"
)
NSFW_NEG = (
    ", penis, cock, dick, genitals, pussy, nude, nsfw, explicit, "
    "exposed genitals, cameltoe, bulging crotch"
)

# Eyes are the win — keep high. ControlNet locks pose/BG; IP-Adapter pulls style/lighting.
JOBS = [
    {
        "id": "001",
        "guide": "Test_001.jpg",
        "chars": ["esil_radiru"],
        "style": "waijfu",
        "cfg": 5.5,
        "depth": 0.48,
        "canny": 0.58,
        "ipa": 0.70,
        "extra_loras": [
            {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.28},
            {"file": "ILDetailerV2.safetensors", "weight": 0.55},
        ],
        # Original Test_001 eyes: crystalline red iris + hard horizontal light streak through both eyes
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, blonde hair, "
            "gothic lolita close-up, head tilt, mischievous smile, fangs, "
            "specialty eye design: large glowing scarlet eyes, complex crystalline iris pattern, "
            "sharp horizontal white-yellow light streak cutting through both eyes, "
            "supernatural eye bloom, detailed pupils, perfect eyes, eye_focus, "
            "red rose hair ornament, black lace, ornate heart gem choker, "
            "holding glowing red rose, floating red petals, dark void background, "
            "crimson bloom lighting, chiaroscuro, highly detailed, sharp focus"
        ),
    },
    {
        "id": "002",
        "guide": "Test_002.jpg",
        "chars": ["esil_radiru"],
        "style": "waijfu",
        "cfg": 5.5,
        "depth": 0.50,
        "canny": 0.60,
        "ipa": 0.72,
        "extra_loras": [
            {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.30},
            {"file": "ILDetailerV2.safetensors", "weight": 0.55},
        ],
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, blonde hair, red eyes, "
            "from below, worm's-eye view, gothic cyber outfit, fishnets, buckles, "
            "neon red rim light, underexposed face, glowing red eyes, perfect eyes, "
            "red roses in foreground, bokeh neon background, dramatic lighting, "
            "highly detailed, sharp focus, eye_focus"
        ),
    },
    {
        "id": "003",
        "guide": "Test_003.jpg",
        "chars": ["park_heejin"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.45,
        "canny": 0.50,
        "ipa": 0.68,
        "extra_loras": [
            {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.65},
            {"file": "ILDetailerV2.safetensors", "weight": 0.55},
        ],
        # Original Test_003 eyes: amber/gold with bright star-shaped catchlights (design, not just sharpness)
        "prompt": (
            "nb_park_heejin, 1girl, solo, blonde hair, long hair, "
            "summer close-up, straw hat casting dappled light on face, "
            "harsh sunlight, extreme bloom, prism light, rainbow lens flare, light leaks, "
            "specialty eye design: large amber-gold eyes, bright star-shaped catchlights in pupils, "
            "glassy sparkling iris, multi-highlight eyes, perfect eyes, eye_focus, "
            "freckles, warm suncore glow, looking at viewer, soft smile, "
            "floating dust motes, highly detailed"
        ),
    },
    {
        "id": "004",
        "guide": "Test_004.jpg",
        "chars": ["fern", "frieren"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.52,
        "canny": 0.62,
        "ipa": 0.74,
        "char_weight": 0.65,
        "extra_loras": [
            {"file": "AquaInk_Watercolor_IL.safetensors", "weight": 1.05},
        ],
        "prompt": (
            "nb_fern, nb_frieren, 2girls, fern and frieren, "
            "wc_painting, watercolor, traditional media, paper texture, "
            "soft edges, color bleeding, loose brushwork, sketchy linework, "
            "back to back pose on green lawn, garden hedges, blue sky, clouds, "
            "fern in oversized striped sweater and white leg warmers leaning forward smiling, "
            "frieren elf white hair green eyes looking over shoulder finger on chin, "
            "crop top and baggy pants, soft daylight, fashion illustration, perfect eyes"
        ),
        "neg_extra": ", ink stains on skin, dirty clothes, photorealistic, hard cel shading, flat vector",
    },
    {
        "id": "005",
        "guide": "Test_005.jpg",
        "chars": ["esil_radiru"],
        "style": "waijfu",  # NOT n4mik4 — avoid cyber NSFW anatomy bleed
        "cfg": 5.5,
        "depth": 0.50,
        "canny": 0.58,
        "ipa": 0.70,
        "extra_loras": [
            {"file": "DramaticColor_IL_v1.safetensors", "weight": 0.32},
            {"file": "ILDetailerV2.safetensors", "weight": 0.60},
        ],
        "nsfw_scrub": True,
        # Original Test_005 eyes: electric cyan with circuit/compass iris, glow bleeding over lids
        "prompt": (
            "nb_esil_radiru, 1girl, solo, demon girl, horns, "
            "white hair, silver hair, messy bangs, "
            "extreme low angle close-up, leaning toward viewer, smirk, "
            "specialty eye design: wide glowing electric-cyan eyes, "
            "intricate circuit-board and compass-rose iris pattern, "
            "eye glow bleeding over eyelids and lashes, neon blue bloom, "
            "perfect eyes, eye_focus, pink digital blush across nose, "
            "layered silver chain necklace, diamond pendant, black choker, "
            "gear hair ornaments, dark jacket, cyan and magenta rim lighting, "
            "glowing particles, chromatic aberration edges, abstract light shards background, "
            "portrait upper body only, clothed, highly detailed, sharp focus"
        ),
    },
    {
        "id": "006",
        "guide": "Test_006.jpg",
        "chars": ["fern"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.50,
        "canny": 0.58,
        "ipa": 0.72,
        "extra_loras": [
            {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.50},
            {"file": "ILDetailerV2.safetensors", "weight": 0.55},
        ],
        "prompt": (
            "nb_fern, 1girl, solo, purple hair, long hair, bangs, purple eyes, "
            "standing waist-deep in clear river, looking up at sun, slight smile, "
            "shiny purple metallic bikini, gold ring detail, crystal earrings, gold bangles, "
            "hands resting on river stones under water, clear water caustics on stones, "
            "visible riverbed pebbles, palm trees and pine trees, distant green mountains, "
            "blue sky with cumulus clouds, bright sun lens flare top right, "
            "wet skin highlights, perfect eyes, eye_focus, highly detailed"
        ),
    },
    {
        "id": "007",
        "guide": "Test_007.jpg",
        "chars": ["frieren"],
        "style": "waijfu",
        "cfg": 5.0,
        "depth": 0.50,
        "canny": 0.58,
        "ipa": 0.72,
        "extra_loras": [
            {"file": "LensFlare_LightLeak_IL.safetensors", "weight": 0.50},
            {"file": "ILDetailerV2.safetensors", "weight": 0.55},
        ],
        "prompt": (
            "nb_frieren, 1girl, solo, white hair, long hair in high ponytail, elf, pointed ears, "
            "red teardrop earrings, white string bikini, eyes closed, blissful smile, "
            "leaning back against sunlit lakeside rocks, arms supporting, "
            "mid-thigh in crystal clear blue lake, water ripples and specular highlights, "
            "pine forest background, blue sky cumulus clouds, bright sun lens flare top right, "
            "water droplets on skin, glamour lighting, highly detailed"
        ),
    },
]


def build_loras(catalog, job: dict) -> list[dict]:
    char_w = float(job.get("char_weight", 0.78))
    eye_w = 0.90  # keep the eye look they liked
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
        if not guide.is_file():
            results.append({"id": sid, "ok": False, "error": f"missing {guide}"})
            continue
        print(f"\n===== PASS2 {sid} =====", flush=True)
        loras = build_loras(catalog, job)
        neg = BASE_NEG + (NSFW_NEG if job.get("nsfw_scrub") else "")
        if job.get("neg_extra"):
            neg += job["neg_extra"]
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
                face_detail=False,  # save VRAM; Eyes LoRA carries the design
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
            name = f"pass2_{sid}_{src.name}"
            for dest_dir in (OUT, DELIVERY):
                dest = dest_dir / name
                shutil.copy2(src, dest)
                copied.append(str(dest))
        entry = {
            "id": sid,
            "ok": True,
            "mode": "controlnet+ipadapter",
            "guide": str(guide),
            "chars": job["chars"],
            "style": job["style"],
            "copied": copied,
            "checkpoint": result.get("checkpoint"),
        }
        results.append(entry)
        print("OK", json.dumps(entry, indent=2)[:900], flush=True)

    summary = {"ok": all(r.get("ok") for r in results), "results": results}
    out_json = ROOT / "outputs" / "style_recreation_stills_pass2.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nDONE", out_json, flush=True)


if __name__ == "__main__":
    main()
