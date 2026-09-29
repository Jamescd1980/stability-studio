"""Darkness casting-couch b1 paint using waijfu_house checkpoint."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

BEAUTY = Path(r"D:\ComfyBox Images and Videos\assets\Darkness\scenes\b1\beauty_layout_dim.png")
POSE = Path(r"D:\ComfyBox Images and Videos\assets\Darkness\scenes\b1\pose.png")
REVIEW = Path(r"D:\ComfyBox Images and Videos\assets\Darkness\review")
SCENES = Path(r"D:\ComfyBox Images and Videos\assets\Darkness\scenes\b1")


def main() -> None:
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    prompt = (
        "asprawl, empty wall, plain wall, muted dim indoor lighting, soft shadow, "
        "casting couch audition room, closed indoor room, solid wall behind the couch, "
        "brown leather couch, blue rug, two-tone walls, View from front, full body, "
        "feet visible, solo focus, 1girl, nbk_darkness, Darkness, blonde hair, blue eyes, "
        "large breasts, white holter top, necktie, blue micro shorts, standing in front of "
        "the couch, hands raised near her chest, looking at viewer, anime++, bold outline, "
        "cel-shaded coloring, perfect eyes"
    )
    neg = (
        "window, windows, glass window, skylight, curtain, curtains, daylight, sunlight, "
        "sunbeam, overexposed, blown highlights, nuke bright, floor lamp, desk lamp, "
        "cluttered wall, camera, dslr, close-up, portrait, cropped legs, 3d, clay, "
        "mannequin, bad anatomy, bad hands, 1boy, man, male"
    )
    r = eng.generate_image_pose_guided(
        image_path=str(BEAUTY),
        pose_image_path=str(POSE),
        prompt=prompt,
        style="waijfu_house",
        negative_prompt=neg,
        loras=[
            {"file": "Darkness/Darkness_id_v1.safetensors", "weight": 0.8},
            {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.65},
        ],
        width=1216,
        height=832,
        denoising_strength=0.74,
        openpose_strength=0.9,
        preprocess_pose=False,
        seed=821010,
    )
    print("style", r.get("style"), "ckpt hint", r.get("checkpoint"))
    saved = (r.get("saved_files") or [None])[0]
    if not saved:
        raise SystemExit(r)
    REVIEW.mkdir(parents=True, exist_ok=True)
    dst = REVIEW / "b1_scene_paint_house.png"
    shutil.copy2(saved, dst)
    shutil.copy2(saved, SCENES / "paint_house.png")
    print("PARKED", dst, flush=True)


if __name__ == "__main__":
    main()
