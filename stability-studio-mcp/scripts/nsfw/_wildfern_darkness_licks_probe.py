"""Probe several Darkness-licks-Fern compositions → review/darkness_licks_vN.png"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

REVIEW = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\review"
)
NIGHT = (
    "loft bedroom at night, dark wood panel walls, warm bedside lamp light, "
    "dark window night sky, purple sheets, dim warm lighting, "
)
NEG = (
    "bad quality, worst quality, two faces, second face, extra face, "
    "man, male, penis, cock, daytime, bright daylight, "
    "clothes, lingerie, bra, panties, camera, dslr, bad anatomy, blurry, pubic hair"
)
EYES = {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.8}
FERN = [{"file": "Fern/Fern_id_v1.safetensors", "weight": 0.85}, EYES]
DARK = [{"file": "Darkness/Darkness_id_v1.safetensors", "weight": 0.85}, EYES]

JOBS = [
    # v4 — mirror of kept fern_licks: Darkness face between thighs
    dict(
        ver=4,
        seed=45301,
        face=True,
        loras=DARK,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "View from above looking down between pale thighs, "
            "solo focus, 1girl, nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "face buried in a pussy, tongue licking pussy, cunnilingus, "
            "smooth bald pussy, looking up, flushed, saliva"
        ),
    ),
    # v5 — Fern face looking down; Darkness crown only, kneeling oral
    dict(
        ver=5,
        seed=45311,
        face=True,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "high angle looking down, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "sitting on the edge of the bed, legs spread, looking down with pleasure face, "
            "blonde head between her thighs licking her pussy, "
            "only top of blonde head and ponytail, no blonde face, cunnilingus, wet pussy"
        ),
    ),
    # v6 — Fern on back, knees up; close on face + torso; blonde head at bottom
    dict(
        ver=6,
        seed=45321,
        face=True,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "from above, medium close-up, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "lying on her back, knees raised, moaning face looking at viewer, "
            "blonde hair and top of head visible between her legs at bottom of frame, "
            "getting licked, cunnilingus, no blonde face"
        ),
    ),
    # v7 — Fern on side / propped; Darkness licking from front of frame
    dict(
        ver=7,
        seed=45331,
        face=True,
        loras=FERN,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "three-quarter view, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "lying on her side on the bed, one leg raised, pleasure face, "
            "blonde head at her crotch licking pussy, only blonde hair crown visible, "
            "no blonde face, cunnilingus, wet pussy"
        ),
    ),
]


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    for j in JOBS:
        out = REVIEW / f"darkness_licks_v{j['ver']}.png"
        print("===", out.name, flush=True)
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
        if not saved:
            print("FAIL", out.name, flush=True)
            continue
        shutil.copy2(saved[0], out)
        print("OK", out, flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
