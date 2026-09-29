"""Generate anti_sprawl_il preferred + reject stills for Kohya training.

Preferred (train): clean rooms / dim night — empty walls, no unprompted windows/lamps/nuke sun.
Reject (eval only): same families with the sprawl failures.

Outputs under delivery Images/ then staged by _stage_anti_sprawl.sh on Linuxbox.
"""
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

OUT = Path(r"D:\ComfyBox Images and Videos\assets\Darkness\anti_sprawl_dataset")
PREF = OUT / "preferred"
REJ = OUT / "reject"

NEG_CLEAN = (
    "window, windows, glass window, skylight, curtain, curtains, blinds, "
    "daylight, sunlight, sunbeam, overexposed, blown highlights, nuke bright, "
    "harsh white light, floor lamp, desk lamp, lantern, neon sign, "
    "cluttered wall, many frames, poster spam, camera, dslr, bad anatomy, bad hands"
)

NEG_BASE = "lowres, bad quality, worst quality, blurry, camera, dslr, bad anatomy, bad hands"

# (stem, prompt, seed) — preferred train set
PREFERRED: list[tuple[str, str, int]] = [
    (
        "night_bedroom_plain_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "night bedroom, closed indoor room, plain empty walls, solid wall, "
        "dim indoor lighting, soft shadow, bedside lamp off, 1girl, solo, standing, "
        "full body, simple brown hair, casual clothes",
        910001,
    ),
    (
        "night_bedroom_plain_b",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "night bedroom, closed room, empty wall behind bed, plain wall, "
        "muted dim indoor lighting, moonlight none, 1girl, sitting on bed, solo",
        910002,
    ),
    (
        "night_office_plain_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "night office, closed indoor room, solid wall, empty wall, plain wall, "
        "dim office lighting, desk, chair, no window, 1girl, standing, solo, full body",
        910003,
    ),
    (
        "night_office_plain_b",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "casting couch audition room at night, brown leather couch, blue rug, "
        "closed indoor room, solid wall behind couch, empty wall, framed nothing, "
        "muted dim indoor lighting, soft shadow, 1girl, standing in front of couch, solo, full body",
        910004,
    ),
    (
        "night_hallway_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "dark hallway at night, plain walls, empty wall, dim ceiling light, "
        "closed indoor corridor, soft shadow, 1girl, walking, solo, full body",
        910005,
    ),
    (
        "night_loft_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "loft apartment at night, wood walls, plain empty wall, dim warm lamp light, "
        "closed indoor room, soft shadow, 1girl, standing, solo, full body",
        910006,
    ),
    (
        "outdoor_night_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "outdoor night street, dark sky, dim street, no neon flood, "
        "muted night lighting, soft shadow, 1girl, standing, solo, full body",
        910007,
    ),
    (
        "outdoor_night_b",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "outdoor night park path, dark trees, dim ambient night light, "
        "no streetlamp glare, soft shadow, 1girl, standing, solo, full body",
        910008,
    ),
    (
        "bathroom_plain_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "bathroom, closed room, plain tile wall, empty wall, dim indoor lighting, "
        "no window, soft shadow, 1girl, standing, solo, full body",
        910009,
    ),
    (
        "living_room_night_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "living room at night, couch, plain empty walls, closed indoor room, "
        "muted dim indoor lighting, soft shadow, 1girl, sitting, solo",
        910010,
    ),
    (
        "kitchen_night_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "kitchen at night, plain wall, empty wall, dim under-cabinet light, "
        "closed indoor room, soft shadow, 1girl, standing, solo, full body",
        910011,
    ),
    (
        "theater_lobby_night_a",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "movie theater lobby at night, closed indoor, plain wall panels, empty wall, "
        "muted dim indoor lighting, soft shadow, 1girl, standing, solo, full body",
        910012,
    ),
]

# Expand preferred with seed variants for volume (~36)
for base_i, (stem, prompt, seed) in enumerate(list(PREFERRED)):
    for k in range(1, 3):
        PREFERRED.append((f"{stem}_v{k}", prompt, seed + 100 * k + base_i))

REJECT: list[tuple[str, str, int]] = [
    (
        "night_bedroom_window_sun",
        "masterpiece, best quality, anime++, night bedroom, large bright window, "
        "sunlight streaming in, overexposed, curtains, 1girl, solo, standing",
        920001,
    ),
    (
        "night_office_skylight",
        "masterpiece, best quality, anime++, night office, skylight, bright daylight, "
        "overexposed indoor, floor lamp, cluttered wall with many frames, 1girl, solo",
        920002,
    ),
    (
        "couch_bright_window",
        "masterpiece, best quality, anime++, casting couch room, large bright window "
        "behind couch, daylight, curtains, desk lamp, 1girl standing, solo, full body",
        920003,
    ),
    (
        "outdoor_night_neon_flood",
        "masterpiece, best quality, anime++, outdoor night, neon signs, bright streetlamps, "
        "harsh glare, overexposed, 1girl, solo, full body",
        920004,
    ),
    (
        "living_room_wall_spam",
        "masterpiece, best quality, anime++, living room, walls covered in posters and frames, "
        "bright window, floor lamp, sunlight, 1girl, solo",
        920005,
    ),
    (
        "hallway_sunbeam",
        "masterpiece, best quality, anime++, hallway, bright sunbeam, overexposed, "
        "large window, lantern, 1girl, solo",
        920006,
    ),
]

for stem, prompt, seed in list(REJECT):
    for k in range(1, 4):
        REJECT.append((f"{stem}_v{k}", prompt, seed + 50 * k))


def caption_preferred(stem: str, prompt: str) -> str:
    # Kohya caption: trigger + scene tags; no window/lamp/sun
    return (
        "asprawl, empty wall, plain wall, closed indoor room, muted dim indoor lighting, "
        "soft shadow, anime illustration, "
        + prompt.replace("masterpiece, best quality, anime++, bold outline, cel-shaded coloring, ", "")
    )


def caption_reject(prompt: str) -> str:
    return "sprawl_bad, " + prompt


def main() -> None:
    PREF.mkdir(parents=True, exist_ok=True)
    REJ.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    catalog = StyleCatalog(catalog_path(cfg), cfg)
    eng = GenerationEngine(cfg, catalog)

    manifest: list[dict] = []

    for stem, prompt, seed in PREFERRED:
        print(f"[preferred] {stem} seed={seed}", flush=True)
        r = eng.generate_image(
            prompt=prompt,
            style="waijfu",
            negative_prompt=NEG_CLEAN,
            width=1024,
            height=1024,
            seed=seed,
            face_detail=False,
            loras=[
                {"file": "S1_Dramatic_Lighting_Illustrious_V2.safetensors", "weight": 0.55}
            ],
        )
        saved = (r.get("saved_files") or [None])[0]
        if not saved:
            print("FAIL", r, flush=True)
            continue
        dst = PREF / f"{stem}.png"
        shutil.copy2(saved, dst)
        (PREF / f"{stem}.txt").write_text(caption_preferred(stem, prompt), encoding="utf-8")
        manifest.append({"set": "preferred", "stem": stem, "src": saved, "dst": str(dst)})

    for stem, prompt, seed in REJECT:
        print(f"[reject] {stem} seed={seed}", flush=True)
        r = eng.generate_image(
            prompt=prompt,
            style="waijfu",
            negative_prompt=NEG_BASE,
            width=1024,
            height=1024,
            seed=seed,
            face_detail=False,
        )
        saved = (r.get("saved_files") or [None])[0]
        if not saved:
            print("FAIL", r, flush=True)
            continue
        dst = REJ / f"{stem}.png"
        shutil.copy2(saved, dst)
        (REJ / f"{stem}.txt").write_text(caption_reject(prompt), encoding="utf-8")
        manifest.append({"set": "reject", "stem": stem, "src": saved, "dst": str(dst)})

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"DONE preferred={len(list(PREF.glob('*.png')))} reject={len(list(REJ.glob('*.png')))}",
        flush=True,
    )


if __name__ == "__main__":
    main()
