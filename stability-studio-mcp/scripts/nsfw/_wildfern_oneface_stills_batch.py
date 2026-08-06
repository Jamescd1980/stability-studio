"""Wild Fern one-face still pack — varied poses (oral / missionary / doggy sheets+lookback)."""
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
    "looking at each other, man, male, penis, cock, camera, dslr, camcorder, lens, "
    "bad anatomy, bad hands, blurry"
)
EYES = {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.8}
FERN = [{"file": "Fern/Fern_id_v1.safetensors", "weight": 0.8}, EYES]
DARK = [{"file": "Darkness/Darkness_id_v1.safetensors", "weight": 0.8}, EYES]

JOBS = [
    dict(
        name="01_fern_licks_s42011",
        seed=42011,
        face=True,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, warm night lighting, "
            "rumpled sheets, between her thighs POV, looking down, solo focus, 1girl, nb_fern, Fern, "
            "purple hair, purple eyes, flushed cheeks, fern sexy lingerie, front, "
            "face between pale blonde thighs, licking pussy, tongue on clit, cunnilingus, wet pussy, pleasure face"
        ),
    ),
    dict(
        name="02_facesit_fernface_darkback_s42101",
        seed=42101,
        face=True,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, warm night lighting, bed, "
            "POV looking down at Fern face, solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "flushed cheeks, fern sexy lingerie, front, lying on her back, legs spread, look of pleasure, "
            "mouth open, back of blonde head between her legs, blonde ponytail from behind, "
            "no face visible on blonde, cunnilingus, getting her pussy licked, tongue on pussy"
        ),
    ),
    dict(
        name="02_facesit_fernface_darkback_s42102",
        seed=42102,
        face=True,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, night lamp, POV from above, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, arched back, pleasure face, "
            "fern sexy lingerie, front, back of a blonde head buried in her pussy, "
            "only blonde hair and ears from behind, no second face, cunnilingus, licking her pussy"
        ),
    ),
    dict(
        name="03_darkness_strap_fern_sheets_s42201",
        seed=42201,
        face=False,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, loft bedroom, warm night, POV from behind, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, on all fours, doggystyle, "
            "face pressed into the pillow, cheek smashed into the sheets, head down into the mattress, "
            "mouth open in bedding, fern sexy lingerie pulled aside, hands on her hips from behind, "
            "thick strap-on dildo in her pussy, strap-on harness, blonde arms only, no second face"
        ),
    ),
    dict(
        name="03_darkness_strap_fern_lookback_s42211",
        seed=42211,
        face=True,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, POV from behind, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, on all fours, doggystyle, "
            "looking back over her shoulder at viewer, flushed pleasure face, fern sexy lingerie, "
            "hands gripping her hips, thick purple strap-on dildo in her pussy, strap-on, "
            "no second face, no blonde face"
        ),
    ),
    dict(
        name="04_fern_strap_darkness_missionary_s42301",
        seed=42301,
        face=True,
        loras=DARK,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, warm night lighting, "
            "missionary POV looking down, solo focus, 1girl, nbk_darkness, Darkness, blonde hair, "
            "ponytail, blue eyes, flushed cheeks, darkness sexy lingerie, front, lying on her back, "
            "legs spread, knees up, thick strap-on dildo in her pussy, vaginal penetration, strap-on, "
            "purple-haired hips and hands only at bottom of frame, no second face, look of pleasure, mouth open"
        ),
    ),
    dict(
        name="04_fern_strap_darkness_lookback_s42311",
        seed=42311,
        face=True,
        loras=DARK,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, POV from behind, "
            "solo focus, 1girl, nbk_darkness, Darkness, blonde hair, ponytail, blue eyes, on all fours, "
            "doggystyle, looking back over her shoulder, pleasure face, darkness sexy lingerie, "
            "thick strap-on dildo in her pussy, hands on her hips, strap-on, no second face"
        ),
    ),
    dict(
        name="05_aftercare_fern_s42401",
        seed=42401,
        face=True,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, soft warm afterglow lighting, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, soft smile, sleepy satisfied expression, "
            "fern sexy lingerie, front, lying on rumpled sheets, one shoulder bare, intimate aftercare, no sex act"
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
        try:
            r = eng.generate_image(
                prompt=j["prompt"],
                style="waijfu",
                negative_prompt=NEG,
                loras=j["loras"],
                width=1024,
                height=1024,
                seed=j["seed"],
                face_detail=j["face"],
                content_rating="open",
            )
            saved = r.get("saved_files") or []
            src = Path(saved[0]) if saved else None
            if src and src.is_file():
                dest = OUT / f"{j['name']}.png"
                shutil.copy2(src, dest)
                shutil.copy2(src, IMPORT / dest.name)
                print("OK", dest, flush=True)
                results.append({"name": j["name"], "ok": True, "path": str(dest)})
            else:
                print("FAIL no file", flush=True)
                results.append({"name": j["name"], "ok": False})
        except Exception as e:
            print("ERR", j["name"], e, flush=True)
            results.append({"name": j["name"], "ok": False, "error": str(e)})
    (OUT / "_batch.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0 if all(x.get("ok") for x in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
