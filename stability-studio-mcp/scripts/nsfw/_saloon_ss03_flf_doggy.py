"""Saloon SS03-1 — 3 keeper-stack iterations after almost-keeper 00174.

Stack: Doggy Sex 1.0/1.0, 41f quality, short vulgar hip-thrust (SS03_1_v2_T1 family).
One job at a time; leave all outputs for human gate (do not auto-promote).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "general"))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

STILL = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Saloon\Stills\forge_soften\SS03-1_forge_soften.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Saloon\Work")
OUT_NOTE = OUT_DIR / "logs" / "_ss03_i2v_keeper_3iter_v9_note.json"

NEG = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, shifting grip, extra hands, four hands, "
    "side to side, lateral sway, swinging sideways, left right wobble, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

LORAS = [
    {
        "id": "doggy_sex_high",
        "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "high",
    },
    {
        "id": "doggy_sex_low",
        "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "low",
    },
]

# Same stack; prompt micro-variations only (one hip-thrust verb each)
ITERS = [
    {
        "id": "v9a",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "he fucks her pussy from behind, thrusting his hips forward and back, "
            "partial withdraw only, vaginal penetration, steady side view"
        ),
    },
    {
        "id": "v9b",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "his cock thrusting in and out of her pussy, "
            "hip thrust driving the shaft, partial withdraw only, "
            "vaginal penetration, hand stays on her ass, steady side view"
        ),
    },
    {
        "id": "v9c",
        "prompt": (
            "nsfw, side view, doggystyle, "
            "he fucks her pussy from behind with strong hip thrusts, "
            "hips pumping forward and back, partial withdraw only, "
            "vaginal penetration, steady side view"
        ),
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

    results: list[dict] = []
    for i, beat in enumerate(ITERS, start=1):
        print(f"\n=== SS03-1 keeper iter {i}/3 ({beat['id']}) ===", flush=True)
        print("still", STILL, flush=True)
        print("prompt", beat["prompt"], flush=True)
        r = eng.generate_video(
            prompt=beat["prompt"],
            mode="i2v",
            workflow_id="i2v",
            content_rating="open",
            image_path=str(STILL),
            num_frames=41,
            frame_rate=16,
            loras=LORAS,
            moe_preset="quality",
            draft=False,
            negative_prompt=NEG,
            motion_amplitude=0.45,
        )
        saved = r.get("saved_files") or []
        if isinstance(saved, str):
            saved = [saved]
        entry = {
            "iter": i,
            "id": beat["id"],
            "prompt": beat["prompt"],
            "saved_files": saved,
            "prompt_id": r.get("prompt_id"),
            "error": r.get("error"),
            "moe_loras": (r.get("moe") or {}).get("high_loras"),
        }
        results.append(entry)
        print("saved_files", saved, flush=True)
        if not saved or r.get("error"):
            print("FAIL iter", i, flush=True)
            OUT_NOTE.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
            return 1

    OUT_NOTE.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("\nNOTE: not promoting — gate all three (+ keep 00174 if still wanted)", flush=True)
    print(json.dumps(results, indent=2, default=str), flush=True)
    print("OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
