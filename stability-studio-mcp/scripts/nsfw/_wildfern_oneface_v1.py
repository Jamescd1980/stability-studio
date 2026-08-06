"""Wild Fern one-face v1 — night loft, toys/leather strap, no clothes, no men."""
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

REVIEW = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\review"
)
AFTERCARE_SRC = REVIEW / "aftercare_v0.png"

NIGHT = (
    "loft bedroom at night, dark wood panel walls, warm bedside lamp light, "
    "dark window night sky, dim warm lighting, purple sheets, "
)
NEG = (
    "bad quality, worst quality, worst detail, sketch, photorealistic, "
    "2girls faces, two faces, second face, extra face, couple portrait, "
    "man, male, penis, cock, balls, testicles, realistic penis, "
    "daytime, bright daylight, sunny window, white void background, "
    "clothes, clothing, lingerie, bra, panties, thong, underwear, dress, shirt, "
    "stockings, gloves, boots, bodysuit, "
    "camera, dslr, camcorder, lens, bad anatomy, bad hands, blurry"
)
EYES = {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.8}
FERN = [{"file": "Fern/Fern_id_v1.safetensors", "weight": 0.8}, EYES]
DARK = [{"file": "Darkness/Darkness_id_v1.safetensors", "weight": 0.85}, EYES]

# name = primary_sexact → review/{name}_v1.png
JOBS = [
    dict(
        name="fern_licks",
        seed=45001,
        face=True,
        loras=FERN,
        i2i=None,
        denoise=None,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "View from above looking down between pale thighs, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, bare shoulders, no clothes, "
            "face buried in a pussy, tongue licking pussy, cunnilingus, wet pussy, "
            "blonde pubic hair only at top of frame, no blonde face, "
            "flushed cheeks, looking up, saliva"
        ),
    ),
    dict(
        name="fern_facesit",
        seed=45011,
        face=True,
        loras=FERN,
        i2i=None,
        denoise=None,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "View from below looking up, facesitting, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "sitting on a face, thighs around a blonde head, "
            "only the back of a blonde head and ponytail at her pussy, occiput only, no blonde face, "
            "moaning face looking down, getting licked, cunnilingus, wet pussy"
        ),
    ),
    dict(
        name="darkness_doggy",
        seed=45021,
        face=False,
        loras=FERN,
        i2i=None,
        denoise=None,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, "
            + NIGHT
            + "View from behind, doggystyle, doggy style, "
            "solo focus, 1girl, nb_fern, Fern, long purple hair, "
            "on all fours, face pressed into the pillow, head down into the sheets, "
            "back of purple head only, no face visible, "
            "completely nude, fully naked, bare ass, bare back, bare skin, no clothes, "
            "pale female hands on her hips, "
            "thick purple strap-on dildo in her pussy, leather strap-on harness on the partner only, "
            "doggystyle, vaginal penetration, only the dildo and female hands from behind, "
            "no second face, no man, no penis"
        ),
    ),
    dict(
        name="darkness_revcowgirl",
        seed=45031,
        face=False,
        loras=DARK,
        i2i=None,
        denoise=None,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, "
            + NIGHT
            + "View from below looking up, Fern POV lying on her back, "
            "solo focus, 1girl, nbk_darkness, Darkness, long blonde hair, blonde ponytail, "
            "reverse cowgirl, reverse cowgirl position, "
            "completely nude, fully naked, bare ass, bare back, no clothes, "
            "straddling, riding a thick purple strap-on dildo, "
            "leather strap-on harness on the hips below only, "
            "pussy stretched on the dildo, asshole visible toward viewer, "
            "hips raised mid-ride, no face or back of head only, no second face, "
            "no man, no penis, vaginal penetration"
        ),
    ),
    dict(
        name="fern_aftercare",
        seed=45041,
        face=True,
        loras=FERN,
        i2i=str(AFTERCARE_SRC) if AFTERCARE_SRC.is_file() else None,
        denoise=0.42,
        prompt=(
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, anime++, "
            "bold outline, cel-shaded coloring, perfect eyes, "
            + NIGHT
            + "soft afterglow, solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "lying on rumpled purple sheets, soft tired smile, intimate aftercare, "
            "no sex act, sleepy, sweaty skin sheen"
        ),
    ),
]


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    results = []
    for j in JOBS:
        out = REVIEW / f"{j['name']}_v1.png"
        if out.is_file() and out.stat().st_size > 50_000:
            print("SKIP", out.name, flush=True)
            results.append({"name": j["name"], "ok": True, "path": str(out), "skipped": True})
            continue
        print("===", j["name"], "->", out.name, flush=True)
        kwargs = dict(
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
        if j.get("i2i"):
            r = eng.generate_image_i2i(
                image_path=j["i2i"],
                denoising_strength=j.get("denoise") or 0.45,
                **kwargs,
            )
        else:
            r = eng.generate_image(**kwargs)
        saved = r.get("saved_files") or []
        src = Path(saved[0]) if saved else None
        if not src or not src.is_file():
            print("FAIL", j["name"], flush=True)
            results.append({"name": j["name"], "ok": False})
            continue
        shutil.copy2(src, out)
        print("OK", out, flush=True)
        results.append({"name": j["name"], "ok": True, "path": str(out)})
    (REVIEW / "_v1_batch.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
