"""Wild Fern one-face FULLY NUDE stills v2 — no lingerie/harness on body."""
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
    r"\Where the Wild Fern Moans\Stills\one_face_nude"
)
IMPORT = Path(r"D:\ComfyBox Images and Videos\User Import\WildFern_oneface")
GAME = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\Movie_WildFern")

NEG = (
    "bad quality, worst quality, worst detail, sketch, photorealistic, "
    "2girls faces, two faces, second face, extra face, couple portrait, "
    "looking at each other, "
    "clothes, clothing, lingerie, bra, panties, thong, underwear, dress, shirt, "
    "stockings, gloves, boots, latex, leather outfit, bodysuit, "
    "harness on her body, straps on her body, belt on her waist, "
    "man, male, penis, cock, camera, dslr, camcorder, lens, bad anatomy, bad hands, blurry"
)
EYES = {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.8}
FERN = [{"file": "Fern/Fern_id_v1.safetensors", "weight": 0.8}, EYES]
DARK = [{"file": "Darkness/Darkness_id_v1.safetensors", "weight": 0.8}, EYES]

JOBS = [
    dict(
        name="01_fern_licks",
        seed=44001,
        face=True,
        loras=FERN,
        game="Movie_WildFern_01_fern_licks.png",
        wan="WF01_fern_licks_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            "extreme close-up, between her thighs POV looking down, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare skin, bare breasts, bare shoulders, "
            "no clothes, no lingerie, no bra, no panties, "
            "face between pale thighs, tongue licking pussy, cunnilingus, wet pussy at top of frame, "
            "blonde pubic hair only, no blonde face, flushed cheeks, looking up"
        ),
    ),
    dict(
        name="02_facesit",
        seed=44011,
        face=True,
        loras=FERN,
        game="Movie_WildFern_02_facesit.png",
        wan="WF02_facesit_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, warm night, "
            "top-down POV, Fern face upper half, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, moaning face, "
            "completely nude, fully naked, bare breasts, no clothes, no lingerie, "
            "lying on back, legs spread, "
            "back of blonde head and ponytail only at her pussy, occiput only, no blonde face, "
            "cunnilingus, getting licked"
        ),
    ),
    dict(
        name="03_darkness_strap_sheets",
        seed=44021,
        face=False,
        loras=FERN,
        game="Movie_WildFern_03_darkness_strap.png",
        wan="WF03_sheets_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, loft bedroom, POV from behind, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, on all fours, doggystyle, "
            "completely nude, fully naked, bare ass, bare back, bare skin, "
            "no clothes, no lingerie, no panties, no straps on her body, "
            "face pressed into the pillow, head down into the sheets, "
            "pale hands on her hips, thick flesh-colored strap-on dildo in her pussy, "
            "only the dildo and hands from behind, no second face"
        ),
    ),
    dict(
        name="03b_lookback",
        seed=44022,
        face=True,
        loras=FERN,
        game=None,
        wan="WF03_lookback_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, POV from behind, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, on all fours, doggystyle, "
            "completely nude, fully naked, bare breasts, bare ass, no clothes, no lingerie, "
            "looking back over her shoulder, pleasure face, "
            "hands on her hips, thick purple strap-on dildo in her pussy, no second face"
        ),
    ),
    dict(
        name="04_missionary",
        seed=44031,
        face=True,
        loras=DARK,
        game="Movie_WildFern_04_fern_strap.png",
        wan="WF04_missionary_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, "
            "missionary POV looking down, solo focus, 1girl, nbk_darkness, Darkness, "
            "blonde hair, ponytail, blue eyes, flushed, "
            "completely nude, fully naked, bare breasts, no clothes, no lingerie, no thong, "
            "lying on her back, legs spread, knees up, "
            "thick strap-on dildo in her pussy, vaginal penetration, "
            "purple-haired hips only at bottom edge, no second face, pleasure face"
        ),
    ),
    dict(
        name="05_aftercare",
        seed=44041,
        face=True,
        loras=FERN,
        game="Movie_WildFern_05_aftercare.png",
        wan=None,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, soft afterglow, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, soft smile, "
            "completely nude, fully naked, bare breasts, no clothes, no lingerie, "
            "lying on rumpled sheets, intimate aftercare, soft, no sex act"
        ),
    ),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    IMPORT.mkdir(parents=True, exist_ok=True)
    GAME.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    results = []
    for j in JOBS:
        print("===", j["name"], flush=True)
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
        if not src or not src.is_file():
            results.append({"name": j["name"], "ok": False})
            continue
        dest = OUT / f"{j['name']}_s{j['seed']}.png"
        shutil.copy2(src, dest)
        if j.get("game"):
            shutil.copy2(src, GAME / j["game"])
            print("game", j["game"], flush=True)
        if j.get("wan"):
            shutil.copy2(src, IMPORT / j["wan"])
            print("wan", j["wan"], flush=True)
        print("OK", dest, flush=True)
        results.append({"name": j["name"], "ok": True, "path": str(dest)})
    (OUT / "_batch_v2.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
