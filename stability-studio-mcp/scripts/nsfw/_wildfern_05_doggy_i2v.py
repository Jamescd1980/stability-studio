"""Wild Fern 05 — Fern strap doggy on Darkness.

v1 OK hips / FAIL shaft: plain i2v doggy 0.75 + hips thrust in prompt.
v2 FAIL: FLF same-still — crap (end-lock / no readable travel). Recycled.
v3 FAIL: deformed hand slaps Darkness back of head. Recycled.
v4 FAIL: glitchy breast bounce at top of frame (Fern torso cropped). Recycled.
v5: shaft-only micro-thrust; doggy 0.85 (less body invent); chest/breast
    stay-put + edge-melt negatives. Keep hands-on-hips lock from v4.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio import engine as engine_mod  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

STILL = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften"
    r"\Movie_WildFern_05_fern_doggy_forge_soften.png"
)
OUT_DIR = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs"
    r"\Where the Wild Fern Moans\Work"
)
OUT_NOTE = OUT_DIR / "logs" / "_wf05_doggy_i2v_21f_v5_note.json"

# One motion verb = shaft. Chest/hands = stay-put (cropped torso at top edge).
PROMPT = (
    "they are having doggy style sex, nsfw, doggystyle, "
    "thick purple dildo thrusting in and out of her pussy, "
    "shaft drives in and out, stays purple, strap-on toy, "
    "partial withdraw only, vaginal penetration, "
    "hands stay on her hips, chest still, steady rear view"
)
NEG = (
    "breast bounce, bouncing breasts, breast jiggle, boob bounce, "
    "morphing breasts, melting chest, glitchy breasts, wobbling torso, "
    "warping chest, stretching breasts, chest smear, "
    "hand on head, hand on back of head, grabbing hair, pulling hair, "
    "slap, slapping, arm reaching to head, hand on neck, "
    "deformed hand, extra hand, extra arm, floating hand, "
    "hips bounce but dildo frozen, butt jiggle only, static shaft, "
    "frozen penetration depth, no shaft travel, grinding only, "
    "flesh colored dildo, skin colored cock, pink penis, beige shaft, "
    "changing color, color morph, purple turns pink, "
    "full dildo exit, empty pussy, disappearing shaft, melting ass, "
    "morphing body, extra face, looking back, camera pan, zoom, camera, dslr"
)

LORAS = [
    {
        "id": "doggy_sex_high",
        "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "weight": 0.85,
        "branch": "high",
    },
    {
        "id": "doggy_sex_low",
        "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "weight": 0.85,
        "branch": "low",
    },
]


def main() -> int:
    if not STILL.is_file():
        print("MISSING", STILL, flush=True)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "logs").mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    cfg.setdefault("gpu_backend", {})["block_comfyui_when_wan2gp_ui"] = False
    cfg.setdefault("comfyui", {})["timeout_seconds"] = 7200
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

    print(
        "=== WF05 doggy i2v v5 (21f, shaft thrust, chest still, doggy 0.85) ===",
        flush=True,
    )
    print("still", STILL, flush=True)
    print("prompt", PROMPT, flush=True)

    prev = engine_mod.ANATOMY_NEGATIVE_HINT
    engine_mod.ANATOMY_NEGATIVE_HINT = ""
    try:
        r = eng.generate_video(
            prompt=PROMPT,
            mode="i2v",
            workflow_id="i2v",
            content_rating="open",
            image_path=str(STILL),
            num_frames=21,
            frame_rate=16,
            loras=LORAS,
            moe_preset="quality",
            draft=False,
            negative_prompt=NEG,
        )
    finally:
        engine_mod.ANATOMY_NEGATIVE_HINT = prev

    OUT_NOTE.write_text(json.dumps(r, indent=2, default=str), encoding="utf-8")
    saved = r.get("saved_files") or []
    if isinstance(saved, str):
        saved = [saved]
    print("saved_files", saved, flush=True)
    print("NOTE: not promoting - gate first (v1 provisional in game)", flush=True)
    print(
        json.dumps(
            {
                k: r.get(k)
                for k in (
                    "ok",
                    "prompt_id",
                    "num_frames",
                    "width",
                    "height",
                    "moe",
                    "error",
                    "workflow",
                )
            },
            indent=2,
            default=str,
        ),
        flush=True,
    )
    ok = bool(r.get("ok", True)) and bool(saved) and not r.get("error")
    print("OK" if ok else "FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
