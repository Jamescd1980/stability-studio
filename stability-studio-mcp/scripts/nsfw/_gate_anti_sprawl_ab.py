"""A/B gate for anti_sprawl_IL LoRA on fixed seeds."""
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

OUT = Path(r"D:\ComfyBox Images and Videos\assets\Darkness\anti_sprawl_dataset\ab_gate")
OUT.mkdir(parents=True, exist_ok=True)

NEG = (
    "lowres, bad quality, worst quality, bad anatomy, bad hands, camera, dslr"
)

CASES = [
    (
        "night_indoor",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "night bedroom, closed indoor room, 1girl, solo, standing, full body, "
        "casual clothes, looking at viewer",
        930001,
    ),
    (
        "outdoor_night",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "outdoor night street, dark sky, 1girl, solo, standing, full body, "
        "casual clothes, looking at viewer",
        930002,
    ),
    (
        "casting_couch",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "casting couch audition room, brown leather couch, blue rug, "
        "closed indoor room, 1girl, nbk_darkness, Darkness, blonde hair, blue eyes, "
        "large breasts, white holter top, necktie, blue micro shorts, "
        "standing in front of the couch, full body, looking at viewer",
        930003,
    ),
    (
        "control_window_lamp",
        "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
        "night bedroom, large window with night city view, desk lamp on, "
        "1girl, solo, standing, full body, casual clothes, looking at viewer",
        930004,
    ),
]


def run(eng: GenerationEngine, stem: str, prompt: str, seed: int, *, with_anti: bool) -> str:
    tag = "with_anti" if with_anti else "baseline"
    loras: list[dict] = [
        {"file": "S1_Dramatic_Lighting_Illustrious_V2.safetensors", "weight": 0.65},
    ]
    if with_anti:
        loras.append({"file": "anti_sprawl_IL.safetensors", "weight": 0.75})
        prompt = "asprawl, empty wall, plain wall, muted dim indoor lighting, " + prompt
        if stem == "control_window_lamp":
            # control case: still ask for window/lamp; keep asprawl for lighting calm
            prompt = (
                "asprawl, muted dim indoor lighting, masterpiece, best quality, anime++, "
                "bold outline, cel-shaded coloring, night bedroom, large window with night "
                "city view, desk lamp on, 1girl, solo, standing, full body, casual clothes, "
                "looking at viewer"
            )
    if stem == "casting_couch":
        loras.append({"file": "Darkness/Darkness_id_v1.safetensors", "weight": 0.8})

    print(f"[{tag}] {stem}", flush=True)
    r = eng.generate_image(
        prompt=prompt,
        style="waijfu",
        negative_prompt=NEG,
        width=1024,
        height=1024,
        seed=seed,
        face_detail=False,
        loras=loras,
    )
    saved = (r.get("saved_files") or [None])[0]
    if not saved:
        raise RuntimeError(str(r))
    dst = OUT / f"{stem}_{tag}.png"
    shutil.copy2(saved, dst)
    return str(dst)


def main() -> None:
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    paths = []
    for stem, prompt, seed in CASES:
        paths.append(run(eng, stem, prompt, seed, with_anti=False))
        paths.append(run(eng, stem, prompt, seed, with_anti=True))
    (OUT / "manifest.json").write_text(json.dumps(paths, indent=2), encoding="utf-8")
    print("GATE DONE", OUT, flush=True)


if __name__ == "__main__":
    main()
