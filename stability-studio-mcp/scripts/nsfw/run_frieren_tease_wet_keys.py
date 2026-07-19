"""Forge wet / collapse / squirt end-keys from Stage1 master (eyes-only ADetailer)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import forge_is_reachable, refine_image_forge, switch_stills_backend  # noqa: E402

from frieren_tease_i2v_kit import (  # noqa: E402
    COLLAPSE_STILL_PROMPT,
    KEYS_DIR,
    STAGE1,
    SQUIRT_STILL_PROMPT,
    WET_STILL_PROMPT,
)

NEG = (
    "cum, semen, lowres, bad anatomy, bad hands, shirt, clothing, "
    "blurry, watermark, text, star pupils"
)

JOBS = [
    ("stage1_wet_key.png", WET_STILL_PROMPT, 0.28),
    ("stage1_collapse_key.png", COLLAPSE_STILL_PROMPT, 0.40),
    ("stage1_squirt_key.png", SQUIRT_STILL_PROMPT, 0.35),
]


def main() -> int:
    cfg = load_config()
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if not STAGE1.is_file():
        print(f"missing {STAGE1}", flush=True)
        return 1

    if not forge_is_reachable(cfg):
        print("SWITCH forge…", flush=True)
        sw = switch_stills_backend(cfg, backend="forge", wait=True)
        print(json.dumps({k: sw.get(k) for k in ("ok", "error", "comfyui_running")}, indent=2), flush=True)
    if not forge_is_reachable(cfg):
        print("Forge not reachable", flush=True)
        return 1

    results = []
    for name, prompt, denoise in JOBS:
        dest = KEYS_DIR / name
        # collapse/squirt need more pose change — start from Stage1 still
        print(f"KEY {name} denoise={denoise}", flush=True)
        r = refine_image_forge(
            cfg,
            image_path=str(STAGE1),
            prompt=prompt,
            negative_prompt=NEG,
            checkpoint="waijfu_alpha.safetensors",
            denoising_strength=denoise,
            steps=28,
            cfg_scale=5.5,
            seed=-1,
            adetailer=True,
            ad_model="mediapipe_face_mesh_eyes_only",
            ad_prompt="detailed eyes, sharp iris, clear catchlights, nb_frieren",
            ad_denoising_strength=0.35,
        )
        if not r.get("ok") or not r.get("saved_files"):
            results.append({"ok": False, "name": name, "result": r})
            print(json.dumps(results[-1], indent=2)[:2000], flush=True)
            continue
        shutil.copy2(r["saved_files"][0], dest)
        results.append({"ok": True, "name": name, "path": str(dest)})
        print("OK", dest, flush=True)

    out = ROOT / "outputs" / "frieren_tease_wet_keys.json"
    out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    ok = all(x.get("ok") for x in results)
    print("DONE", out, flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
