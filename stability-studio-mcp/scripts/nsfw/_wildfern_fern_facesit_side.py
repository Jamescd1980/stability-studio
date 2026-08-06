"""Fern facesitting side view — two bodies, one face (Fern)."""
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
    "Darkness face, man, male, penis, cock, daytime, bright daylight, "
    "clothes, lingerie, camera, dslr, bad anatomy, blurry, pubic hair"
)
EYES = {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.8}
FERN = [{"file": "Fern/Fern_id_v1.safetensors", "weight": 0.85}, EYES]

JOBS = [
    dict(
        ver=1,
        seed=45601,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "side view, facesitting, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "sitting on a face, straddling someone's head, "
            "blonde body lying on the bed under her, pale breasts and torso visible, "
            "only top of blonde head and hair under her pussy, no blonde face, "
            "pleasure face looking down, cunnilingus, getting licked"
        ),
    ),
    dict(
        ver=2,
        seed=45611,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "clear side profile view, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "facesitting, kneeling over a blonde woman, "
            "blonde woman body on her back under Fern, thighs and breasts visible, "
            "blonde face completely buried under Fern's pussy, hidden, "
            "only blonde hair sticking out, Fern moaning in profile, cunnilingus"
        ),
    ),
    dict(
        ver=3,
        seed=45621,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "side view, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "facesitting, squatting on a face, "
            "second body blonde under her on the sheets, bare breasts and belly visible, "
            "head hidden between Fern's thighs, no second face, "
            "Fern looking down flushed, wet pussy, cunnilingus"
        ),
    ),
    dict(
        ver=4,
        seed=45631,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "side view from the left, cinematic framing, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "riding a face, facesitting, "
            "blonde partner body stretched on bed beneath her, "
            "only blonde hair and forehead edge under her crotch, face obscured, "
            "Fern arched back pleasure face, tongue on pussy implied"
        ),
    ),
]


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    for j in JOBS:
        out = REVIEW / f"fern_facesit_v{j['ver']}.png"
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
