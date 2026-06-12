#!/usr/bin/env python3
"""Second pass: character right hand only (viewer-left), higher denoise, lower sleeve zone."""
from __future__ import annotations

import json
import shutil
import struct
import sys
import traceback
import zlib
from pathlib import Path

#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

_LEGACY = Path(__file__).resolve().parent
sys.path.insert(0, str(_LEGACY))
from _bootstrap import setup_paths

setup_paths()
MCP_ROOT = setup_paths()
import rin_project_paths as P

P.ensure_layout()
PROJECT_DIR = P.ROOT
SOURCE = P.HERO_STILL

PROMPT = (
    "score_9, score_8_up, masterpiece, anime illustration, "
    "anatomically correct right hand, five fingers, gripping "
    "small black metal ninja throwing kunai, short triangular blade, ring pommel, palm-sized dagger"
)

NEGATIVE = (
    "sword, katana, long blade, empty hand, extra fingers, deformed hand, "
    "face, head, different character"
)

SEEDS = [424245, 424246]
DENOISE = 0.78
IP_WEIGHT = 0.62


def write_right_hand_mask(path: Path, width: int, height: int) -> Path:
    """Viewer-left zone = character's right hand; covers sleeve opening area."""
    path.parent.mkdir(parents=True, exist_ok=True)
    x0, x1 = int(width * 0.02), int(width * 0.38)
    y0, y1 = int(height * 0.44), int(height * 0.78)

    def row_bytes(y: int) -> bytes:
        row = bytearray([0])
        for x in range(width):
            row.append(255 if x0 <= x <= x1 and y0 <= y <= y1 else 0)
        return bytes(row)

    raw = b"".join(row_bytes(y) for y in range(height))
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    path.write_bytes(png)
    return path


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_kunai_right_hand.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine
        from studio.ip_adapter_assets import image_dimensions

        requests.get("http://127.0.0.1:8188/system_stats", timeout=30)
        requests.post(
            "http://127.0.0.1:8188/free",
            json={"unload_models": True, "free_memory": True},
            timeout=120,
        )

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 3.0
        engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

        w, h = image_dimensions(SOURCE)
        mask = engine.output_dir / "_rin_right_hand_mask.png"
        write_right_hand_mask(mask, w, h)
        mask_copy = PROJECT_DIR / "Rin_kunai_right_hand_mask.png"
        shutil.copy2(mask, mask_copy)

        runs = []
        for seed in SEEDS:
            tag = f"seed{seed}"
            print(f"=== right-hand inpaint {tag} ===", flush=True)
            result = engine.inpaint_advanced(
                image_path=str(SOURCE),
                prompt=PROMPT,
                mask_path=str(mask),
                mask_region="none",
                style="pony",
                negative_prompt=NEGATIVE,
                seed=seed,
                denoising_strength=DENOISE,
                ipadapter_weight=IP_WEIGHT,
            )
            saved = result.get("saved_files") or []
            dest = PROJECT_DIR / f"Rin_kunai_right_hand_{tag}.png"
            shutil.copy2(Path(saved[-1]), dest)
            runs.append({"tag": tag, "seed": seed, "delivered": str(dest)})

        payload = {
            "status": "success",
            "mask": str(mask_copy),
            "denoise": DENOISE,
            "runs": runs,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_kunai_right_hand.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
