"""Wild Fern 04 — reverse cowgirl strap ride.

v1–v6 FAIL: doggy_sex + prompt hope — no shaft travel.
v7 KEEP motion / FAIL color: r3v3rs3_c0wg1rl @0.85 — purple dildo drifted to flesh.
v8: same LoRA pair, lower weight, purple color lock (toy not penis language).
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
    r"\Movie_WildFern_04_fern_revcowgirl_forge_soften.png"
)
OUT_DIR = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs"
    r"\Where the Wild Fern Moans\Work"
)
OUT_NOTE = OUT_DIR / "logs" / "_wf04_revcowgirl_i2v_33f_v8_note.json"

# Keep ride motion from v7; lock toy color (LoRA was trained on flesh penises).
PROMPT = (
    "r3v3rs3_c0wg1rl, nsfw, reverse cowgirl, "
    "she rides a thick purple dildo, hips bounce up and down, "
    "purple dildo slides in and out of her pussy, stays purple, "
    "strap-on toy, vaginal penetration, partial withdraw only, steady rear view"
)
NEG = (
    "flesh colored dildo, skin colored cock, pink penis, beige shaft, "
    "realistic penis, human cock, changing color, color morph, "
    "purple turns pink, purple turns skin tone, "
    "hips move but dildo stays still, static shaft, frozen penetration depth, "
    "full dildo exit, disappearing shaft, melting ass, morphing body, "
    "face appearing, looking back, camera pan, zoom, camera, dslr"
)

LORAS = [
    {
        "id": "rev_cowgirl_high",
        "file": "wan22.r3v3rs3_c0wg1rl-14b-High-i2v_e70.safetensors",
        "weight": 0.7,
        "branch": "high",
    },
    {
        "id": "rev_cowgirl_low",
        "file": "wan22.r3v3rs3_c0wg1rl-14b-Low-i2v_e70.safetensors",
        "weight": 0.7,
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

    print("=== WF04 revcowgirl i2v v8 (purple lock, LoRA 0.7, 33f quality) ===", flush=True)
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
            num_frames=33,
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
    print("NOTE: not promoting - gate first", flush=True)
    print(
        json.dumps(
            {
                k: r.get(k)
                for k in ("ok", "prompt_id", "num_frames", "width", "height", "moe", "error", "workflow")
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
