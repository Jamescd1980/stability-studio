"""Saloon BJ02 FLF2V same-still bob — return-to-start (not frozen 17f)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "general"))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

try:
    from recycle_path import recycle  # noqa: E402
except Exception:  # pragma: no cover
    def recycle(p: Path) -> None:
        p = Path(p)
        if p.is_file():
            p.unlink()

STILL = Path(
    r"D:\ComfyBox Images and Videos\User Import\Saloon_BJ02_forge_soften.png"
)
OUT_DIR = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Saloon\Work"
)
OUT_NOTE = OUT_DIR / "_bj02_flf_bob_note.json"
DEST = OUT_DIR / "BJ02_flf_bob_33f.mp4"

# Explicit out-and-back so same-still FLF cannot freeze (17f subtle = dead plate).
PROMPT = (
    "nsfw blowjob, one slow head bob down the shaft then back up to the start pose, "
    "lips stay sealed on the cock, return to the same pose, hips locked, loopable"
)
NEG = (
    "static pose, frozen, no motion, still image, "
    "full penis exit, cock leaving mouth, empty mouth, pulling away, "
    "deflating penis, disappearing shaft, camera move, zoom, pan, "
    "morphing face, melted face, talking, chewing, biting"
)

LORAS = [
    {
        "id": "oral_high",
        "file": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "weight": 0.7,
        "branch": "high",
    },
    {
        "id": "oral_low",
        "file": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "weight": 0.7,
        "branch": "low",
    },
]


def main() -> int:
    if not STILL.is_file():
        print("MISSING", STILL, flush=True)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    cfg.setdefault("gpu_backend", {})["block_comfyui_when_wan2gp_ui"] = False
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

    # 33f @ 16fps ≈ 2.06s — room for one down/up return (same-still FLF)
    print("=== BJ02 FLF2V bob return-to-start (33f quality) ===", flush=True)
    print("still", STILL, flush=True)
    r = eng.generate_video(
        prompt=PROMPT,
        mode="i2v",
        workflow_id="flf2v",
        content_rating="open",
        image_path=str(STILL),
        end_image_path=str(STILL),
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
    promoted = None
    for p in saved:
        src = Path(str(p))
        if src.is_file() and src.suffix.lower() == ".mp4":
            if DEST.is_file():
                recycle(DEST)
            shutil.copy2(src, DEST)
            promoted = DEST
            break
    print("promoted", promoted, flush=True)
    print(json.dumps({k: r.get(k) for k in ("prompt_id", "num_frames", "width", "height", "moe")}, indent=2, default=str), flush=True)
    ok = promoted is not None and promoted.is_file()
    print("OK" if ok else "FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
