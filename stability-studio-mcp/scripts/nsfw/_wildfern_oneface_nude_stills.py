"""Wild Fern one-face NUDE stills — variety poses, no clothes."""
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
    "looking at each other, clothes, clothing, lingerie, bra, panties, dress, "
    "shirt, underwear, stockings, gloves, boots, latex, man, male, penis, cock, "
    "camera, dslr, camcorder, lens, bad anatomy, bad hands, blurry"
)
EYES = {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.8}
FERN = [{"file": "Fern/Fern_id_v1.safetensors", "weight": 0.8}, EYES]
DARK = [{"file": "Darkness/Darkness_id_v1.safetensors", "weight": 0.8}, EYES]

JOBS = [
    # 01 Fern face between thighs licking — nude
    dict(
        name="01_fern_licks",
        seed=43001,
        face=True,
        loras=FERN,
        game="Movie_WildFern_01_fern_licks.png",
        wan="WF01_fern_licks_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            "extreme close-up, between her thighs POV looking down, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, naked, bare breasts, no clothes, "
            "face filling frame between pale thighs, tongue out licking pussy, "
            "cunnilingus, wet pussy lips at top of frame, blonde pubic hair only, "
            "no blonde face, no second person face, flushed cheeks, pleasure eyes looking up"
        ),
    ),
    # 02 Fern face + back of Darkness head only — nude
    dict(
        name="02_facesit",
        seed=43011,
        face=True,
        loras=FERN,
        game="Movie_WildFern_02_facesit.png",
        wan="WF02_facesit_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, warm night, "
            "top-down POV, Fern face upper half of image, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, flushed, moaning face, "
            "completely nude, naked, bare breasts, no clothes, lying on back, legs spread, "
            "blonde ponytail crown of head only at crotch, facing into pussy, "
            "back of head only, zero blonde face, cunnilingus, getting licked"
        ),
    ),
    # 03 Fern doggy face into sheets — nude + strap
    dict(
        name="03_darkness_strap_sheets",
        seed=43021,
        face=False,
        loras=FERN,
        game="Movie_WildFern_03_darkness_strap.png",
        wan="WF03_sheets_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, loft bedroom, warm night, POV from behind, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, on all fours, doggystyle, "
            "completely nude, naked, bare ass, no clothes, "
            "face pressed into the pillow, cheek smashed into the sheets, head down into the mattress, "
            "mouth open in bedding, hands on her hips from behind, "
            "thick strap-on dildo in her pussy, strap-on harness on partner, blonde arms only, no second face"
        ),
    ),
    # 03b lookback alt (also install as alt file, primary is sheets)
    dict(
        name="03b_darkness_strap_lookback",
        seed=43022,
        face=True,
        loras=FERN,
        game=None,
        wan="WF03_lookback_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, POV from behind, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, on all fours, doggystyle, "
            "completely nude, naked, bare breasts, bare ass, no clothes, "
            "looking back over her shoulder at viewer, flushed pleasure face, "
            "hands gripping her hips, thick purple strap-on dildo in her pussy, strap-on, "
            "no second face, no blonde face"
        ),
    ),
    # 04 Darkness missionary — nude
    dict(
        name="04_fern_strap_missionary",
        seed=43031,
        face=True,
        loras=DARK,
        game="Movie_WildFern_04_fern_strap.png",
        wan="WF04_missionary_wanstart.png",
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, warm night lighting, "
            "missionary POV looking down, solo focus, 1girl, nbk_darkness, Darkness, blonde hair, "
            "ponytail, blue eyes, flushed cheeks, "
            "completely nude, naked, bare breasts, no clothes, "
            "lying on her back, legs spread, knees up, "
            "thick strap-on dildo in her pussy, vaginal penetration, strap-on, "
            "purple-haired hips and hands only at bottom of frame, no second face, look of pleasure, mouth open"
        ),
    ),
    # 05 aftercare nude soft
    dict(
        name="05_aftercare",
        seed=43041,
        face=True,
        loras=FERN,
        game="Movie_WildFern_05_aftercare.png",
        wan=None,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, loft bedroom, soft warm afterglow lighting, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, soft smile, sleepy satisfied expression, "
            "completely nude, naked, bare breasts, no clothes, "
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
        shutil.copy2(src, IMPORT / dest.name)
        if j.get("game"):
            shutil.copy2(src, GAME / j["game"])
            print("game", j["game"], flush=True)
        if j.get("wan"):
            shutil.copy2(src, IMPORT / j["wan"])
            print("wan", j["wan"], flush=True)
        print("OK", dest, flush=True)
        results.append({"name": j["name"], "ok": True, "path": str(dest)})
    (OUT / "_batch.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0 if all(x.get("ok") for x in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
