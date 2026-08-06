"""Saloon SS02 plain MoE i2v — Missionary Sex + playtime_ai trigger (stronger thrust).

v6 FLF same-still: thrust too minor (end lock). v7: i2v only, no end image.
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
    r"\Saloon\Stills\forge_soften\SS02_forge_soften.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Saloon\Work")
OUT_NOTE = OUT_DIR / "logs" / "_ss02_i2v_thrust_33f_v7_note.json"

# playtime_ai trigger + clearer axial thrust (partial withdraw only)
PROMPT = (
    "A naked man and a naked woman having sex. "
    "He thrusts his penis in and out of her vagina. "
    "a pov shot. "
    "strong front-to-back hip thrusts, "
    "cock slides partially out then thrusts deep back in, "
    "visible shaft travel, partial withdraw only, cock stays inside"
)
NEG = (
    "huge eyes, oversized eyes, giant eyes, eye enlargement, "
    "morphing face, melted face, "
    "shrinking penis, penis getting smaller, scaling penis, fake thrust, "
    "hips move but cock stays still, static shaft, frozen penetration depth, "
    "deflating penis, disappearing shaft, morphing penis, "
    "full penis exit, cock leaving pussy, empty pussy, pulling out completely, "
    "subtle motion, tiny thrust, barely moving, "
    "camera move, zoom, pan, extra limbs"
)

LORAS = [
    {
        "id": "missionary_sex_high",
        "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "weight": 0.9,
        "branch": "high",
    },
    {
        "id": "missionary_sex_low",
        "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "weight": 0.9,
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
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

    print("=== SS02 MoE i2v v7 Missionary + author trigger (33f quality, NO FLF) ===", flush=True)
    print("still", STILL, flush=True)
    print("prompt", PROMPT, flush=True)
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
    OUT_NOTE.write_text(json.dumps(r, indent=2, default=str), encoding="utf-8")
    saved = r.get("saved_files") or []
    if isinstance(saved, str):
        saved = [saved]
    print("saved_files", saved, flush=True)
    print("NOTE: not promoting — gate first", flush=True)
    print(
        json.dumps(
            {k: r.get(k) for k in ("ok", "prompt_id", "num_frames", "width", "height", "moe", "error")},
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
