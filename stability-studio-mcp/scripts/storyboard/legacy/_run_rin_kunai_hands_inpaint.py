#!/usr/bin/env python3
"""Tight hands-only inpaint for kunai — never use edit_image regional fallbacks."""
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
    "score_9, score_8_up, masterpiece, best quality, anime illustration, "
    "natural hands, five fingers, anatomically correct hands, "
    "small black metal ninja throwing knife in right hand, short triangular blade, ring pommel, "
    "left hand empty at side, dark blue military uniform sleeves"
)

NEGATIVE = (
    "sword, katana, long blade, greatsword, dual wield, extra fingers, missing fingers, "
    "deformed hands, mutated hands, bad anatomy, blurry, face change, different face, "
    "different head, wrong angle, cropped head"
)

SEGMENT_PROMPTS = ("hands", "hand . arm")
SEEDS = [424243, 424244]
DENOISE = 0.58
IP_WEIGHT = 0.72


def write_hands_waist_mask(path: Path, width: int, height: int) -> Path:
    """Small bilateral hand zones only — avoids face/torso/head entirely."""
    path.parent.mkdir(parents=True, exist_ok=True)
    zones = (
        (int(width * 0.06), int(width * 0.30), int(height * 0.50), int(height * 0.74)),
        (int(width * 0.70), int(width * 0.94), int(height * 0.50), int(height * 0.74)),
    )

    def row_bytes(y: int) -> bytes:
        row = bytearray([0])
        for x in range(width):
            val = 0
            for x0, x1, y0, y1 in zones:
                if x0 <= x <= x1 and y0 <= y <= y1:
                    val = 255
                    break
            row.append(val)
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


def resolve_mask(engine, image_path: Path, out_dir: Path) -> tuple[Path, str]:
    from studio.ip_adapter_assets import image_dimensions
    from studio.segmentation import segment_image_to_mask

    for seg_prompt in SEGMENT_PROMPTS:
        mask, _fallback = segment_image_to_mask(
            engine.comfy,
            out_dir,
            image_path=image_path,
            segment_prompt=seg_prompt,
            threshold=0.28,
        )
        if mask and mask.is_file() and mask.stat().st_size > 500:
            return mask, f"sam:{seg_prompt}"

    w, h = image_dimensions(image_path)
    manual = out_dir / "_rin_hands_waist_mask.png"
    write_hands_waist_mask(manual, w, h)
    return manual, "manual_hands_waist_zones"


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_kunai_hands_inpaint.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        if not SOURCE.is_file():
            raise FileNotFoundError(f"Missing source still: {SOURCE}")

        requests.get("http://127.0.0.1:8188/system_stats", timeout=30)

        requests.post(
            "http://127.0.0.1:8188/free",
            json={"unload_models": True, "free_memory": True},
            timeout=120,
        )

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 3.0
        cat = StyleCatalog(catalog_path(cfg), cfg)
        engine = GenerationEngine(cfg, cat)
        if not engine.comfy.is_running():
            raise RuntimeError("ComfyUI not running")

        mask_path, mask_source = resolve_mask(engine, SOURCE, engine.output_dir)
        mask_copy = PROJECT_DIR / f"Rin_kunai_hands_mask_{mask_source.replace(':', '_')}.png"
        shutil.copy2(mask_path, mask_copy)
        print(f"Mask: {mask_source} -> {mask_copy}", flush=True)

        runs: list[dict] = []
        for seed in SEEDS:
            tag = f"seed{seed}"
            print(f"\n=== inpaint_advanced {tag} (denoise={DENOISE}) ===", flush=True)
            result = engine.inpaint_advanced(
                image_path=str(SOURCE),
                prompt=PROMPT,
                mask_path=str(mask_path),
                mask_region="none",
                style="pony",
                negative_prompt=NEGATIVE,
                seed=seed,
                denoising_strength=DENOISE,
                ipadapter_weight=IP_WEIGHT,
            )
            saved = result.get("saved_files") or []
            if not saved:
                raise RuntimeError(f"No output for seed {seed}")
            src = Path(saved[-1])
            dest = PROJECT_DIR / f"Rin_kunai_hands_inpaint_{tag}.png"
            shutil.copy2(src, dest)
            runs.append(
                {
                    "tag": tag,
                    "seed": seed,
                    "delivered": str(dest),
                    "mask_source": mask_source,
                    "mask_preview": str(mask_copy),
                    "denoising_strength": DENOISE,
                }
            )

        payload = {
            "status": "success",
            "source": str(SOURCE),
            "approach": "inpaint_advanced tight hands mask only — no edit_image regional fallback",
            "mask_source": mask_source,
            "runs": runs,
            "note": "Face/head untouched outside mask. Pick best; rename to Rin_kitsune_approved.png.",
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_kunai_hands_inpaint.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
