"""Saloon SS04_002 — cum drip into open mouth (quality MoE, no action LoRA).

v1/v2 froze with FacialCum 0.40/0.30 (mean frame-diff ~0.22–0.24).
v3: drop FacialCum — one drip verb only; identity from still.
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
from studio import engine as engine_mod  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

STILL = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Saloon\Stills\forge_soften\SS04_002_forge_soften.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Saloon\Work")
OUT_NOTE = OUT_DIR / "logs" / "_ss04_002_drip_mouth_41f_v3_nolor_note.json"

PROMPT = (
    "nsfw, thick cum strand slowly dripping downward into her open mouth, "
    "viscous semen sliding down, continuous drip motion"
)
NEG = (
    "frozen, static, still image, no motion, slideshow, "
    "honey, water, transparent, thin liquid, "
    "closed mouth, shutting mouth, swallowing hard, "
    "turning head, head moving, looking away, "
    "hand movement, waving hands, shifting grip, "
    "thrusting hips, bouncing, fucking, "
    "melting face, morphing face, "
    "camera pan, zoom, pan, "
    "camera, dslr, camcorder, lens"
)


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

    print("=== SS04_002 drip-into-mouth v3 (no LoRA, 41f quality) ===", flush=True)
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
            num_frames=41,
            frame_rate=16,
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
