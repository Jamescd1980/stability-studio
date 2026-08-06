"""Side-view: Fern on back, Darkness between legs, hide Darkness face."""
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
    "dark window night sky, purple sheets, "
)
NEG = (
    "bad quality, worst quality, two faces, second face, blonde face, blue eyes second, "
    "Darkness face visible, looking at viewer blonde, "
    "man, male, penis, cock, daytime, bright daylight, "
    "clothes, lingerie, facesitting, camera, dslr, bad anatomy, blurry, pubic hair"
)
EYES = {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.8}
FERN = [{"file": "Fern/Fern_id_v1.safetensors", "weight": 0.85}, EYES]

BASE = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
    "bold outline, cel-shaded coloring, perfect eyes, "
    + NIGHT
    + "side view, "
    "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
    "completely nude, fully naked, bare breasts, no clothes, "
    "lying on her back on the bed, legs open, knees bent, "
)

JOBS = [
    dict(
        ver=10,
        seed=45501,
        prompt=BASE
        + "pleasure face in profile, looking down toward her crotch, "
        "blonde head between her thighs licking her pussy, "
        "face hidden, only blonde hair and top of head, back of head toward viewer, "
        "no blonde face, cunnilingus, wet pussy",
    ),
    dict(
        ver=11,
        seed=45511,
        prompt=BASE
        + "three-quarter face toward viewer, moaning, "
        "blonde woman between her legs eating her out, "
        "Darkness face buried and obscured by thighs and hair, "
        "only blonde ponytail and scalp visible, cunnilingus from the side",
    ),
    dict(
        ver=12,
        seed=45521,
        prompt=BASE
        + "head on pillow, soft smile looking down, "
        "cunnilingus, blonde hair cascading over her pussy hiding the licking face, "
        "only blonde hair mound between thighs, no second face",
    ),
    dict(
        ver=13,
        seed=45531,
        prompt=BASE
        + "profile view of Fern face left side of frame, "
        "body stretching right, "
        "blonde head at her crotch right side, face turned away into her pussy, "
        "occiput and ponytail only, tongue implied, cunnilingus side angle",
    ),
    dict(
        ver=14,
        seed=45541,
        prompt=BASE
        + "arched back, open mouth pleasure, "
        "someone licking her pussy from between her legs, "
        "blonde hair top of head only, face completely hidden by her thigh, "
        "cunnilingus, side lighting",
    ),
]


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    for j in JOBS:
        out = REVIEW / f"darkness_licks_v{j['ver']}.png"
        if out.is_file() and out.stat().st_size > 50_000:
            print("SKIP", out.name, flush=True)
            continue
        print("===", out.name, flush=True)
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
        if not saved:
            print("FAIL", flush=True)
            continue
        shutil.copy2(saved[0], out)
        print("OK", out, flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
