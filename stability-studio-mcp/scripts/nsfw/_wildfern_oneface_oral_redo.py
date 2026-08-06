"""Redo oral stills that missed one-face / back-of-head brief."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\one_face"
)
IMPORT = Path(r"D:\ComfyBox Images and Videos\User Import\WildFern_oneface")

NEG = (
    "bad quality, worst quality, worst detail, sketch, photorealistic, "
    "2girls faces, two faces, second face, extra face, couple portrait, "
    "looking at each other, blonde face, blue eyes on second person, "
    "cowgirl, straddling face toward viewer, man, male, penis, cock, "
    "camera, dslr, camcorder, lens, bad anatomy, bad hands, blurry"
)
EYES = {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.8}
FERN = [{"file": "Fern/Fern_id_v1.safetensors", "weight": 0.8}, EYES]

JOBS = [
    # Fern face only, between blonde thighs, licking — tight crop
    dict(
        name="01_fern_licks_s42501",
        seed=42501,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            "extreme close-up, between her thighs POV looking down, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "face filling frame between pale thighs, tongue out licking pussy, "
            "cunnilingus, wet pussy lips at top of frame, blonde pubic hair only, "
            "no blonde face, no second person face, fern sexy lingerie straps visible, "
            "flushed cheeks, pleasure eyes looking up"
        ),
    ),
    dict(
        name="01_fern_licks_s42502",
        seed=42502,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom ceiling soft bokeh, "
            "POV looking down between spread thighs, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "head between thighs, licking clit, open mouth, saliva, cunnilingus, "
            "only thighs and pussy of blonde partner, face cropped out of blonde, "
            "fern sexy lingerie, front"
        ),
    ),
    # Fern face + ONLY back of blonde head (Darkness licking her)
    dict(
        name="02_facesit_fernface_darkback_s42601",
        seed=42601,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, warm night, "
            "POV from above looking at Fern face, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "lying on back, pleasure face, mouth open, looking at viewer, fern sexy lingerie, front, "
            "back of blonde head and ponytail at bottom of frame between her legs, "
            "back of head only, no blonde face, no blue eyes, hair covering face completely, "
            "cunnilingus, getting licked"
        ),
    ),
    dict(
        name="02_facesit_fernface_darkback_s42602",
        seed=42602,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            "top-down POV, Fern face upper half of image, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, flushed, moaning face, "
            "fern sexy lingerie, front, legs spread, "
            "blonde ponytail crown of head only at crotch, facing into pussy, "
            "occiput only, zero blonde face pixels, cunnilingus"
        ),
    ),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    IMPORT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    results = []
    for j in JOBS:
        print("===", j["name"], flush=True)
        r = eng.generate_image(
            prompt=j["prompt"],
            style="waijfu",
            negative_prompt=NEG,
            loras=FERN,
            width=1024,
            height=1024,
            seed=j["seed"],
            face_detail=True,
            content_rating="open",
        )
        saved = r.get("saved_files") or []
        src = Path(saved[0]) if saved else None
        if not src or not src.is_file():
            results.append({"name": j["name"], "ok": False})
            continue
        dest = OUT / f"{j['name']}.png"
        shutil.copy2(src, dest)
        shutil.copy2(src, IMPORT / dest.name)
        print("OK", dest, flush=True)
        results.append({"name": j["name"], "ok": True, "path": str(dest)})
    (OUT / "_oral_redo.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
