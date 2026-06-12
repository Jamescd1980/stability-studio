#!/usr/bin/env python3
"""Clip1 frame0 + POV Holding Pony LoRA i2i for kunai."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import traceback
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
from _env import comfy_python, imageio_ffmpeg

import rin_project_paths as P

P.ensure_layout()
PROJECT_DIR = P.ROOT
CLIP1 = P.CLIP1_WALK
FRAME0 = P.CLIP1_FIRST

LORA_FILE = "concept_povholding-pony-v2.safetensors"
LORA_VERSION = 492190
LORA_WEIGHT = 0.72

PROMPT = (
    "score_9, score_8_up, score_7_up, source_anime, rating_explicit, high_quality, detailed, "
    "povhldg, pov holding, holding_kunai, kunai, holding_weapon, reverse_grip, "
    "1girl, solo, kitsune, fox_girl, white_hair, fox_ears, fox_tail, red_eyes, "
    "military_uniform, peaked_cap, cherry_blossoms, outdoors, walking, looking_at_viewer"
)

NEGATIVE = (
    "holding_sword, sword, katana, briefcase, bag, satchel, bad_hands, extra_fingers, "
    "open_mouth, blurry, lowres"
)

FFMPEG = imageio_ffmpeg()

VARIANTS = [
    {"tag": "lora_d030", "denoise": 0.30, "seed": 424261},
    {"tag": "lora_d034", "denoise": 0.34, "seed": 424262},
]


def extract_first_frame(video: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    ff = str(FFMPEG) if FFMPEG.is_file() else "ffmpeg"
    subprocess.run(
        [ff, "-y", "-i", str(video), "-vf", "select=eq(n\\,0)", "-vframes", "1", str(dest)],
        check=True,
        capture_output=True,
    )
    if not dest.is_file() or dest.stat().st_size < 500:
        raise RuntimeError(f"Failed to extract first frame: {dest}")


def ensure_lora(cfg) -> Path:
    from studio.civitai_download import download_civitai_lora

    dest = download_civitai_lora(
        cfg,
        filename=LORA_FILE,
        version_id=LORA_VERSION,
        force=False,
    )
    if not dest.is_file():
        raise FileNotFoundError(dest)
    return dest


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_clip1_kunai_lora_i2i.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        if not CLIP1.is_file():
            raise FileNotFoundError(CLIP1)

        requests.get("http://127.0.0.1:8188/system_stats", timeout=60)
        requests.post(
            "http://127.0.0.1:8188/free",
            json={"unload_models": True, "free_memory": True},
            timeout=120,
        )

        print("Extracting clip1 frame 0...", flush=True)
        extract_first_frame(CLIP1, FRAME0)

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 3.0
        lora_path = ensure_lora(cfg)
        print(f"LoRA ready: {lora_path}", flush=True)

        engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
        loras = [{"name": LORA_FILE, "weight": LORA_WEIGHT}]

        runs = []
        for v in VARIANTS:
            tag = str(v["tag"])
            print(f"=== {tag} denoise={v['denoise']} ===", flush=True)
            result = engine.generate_image_i2i(
                image_path=str(FRAME0),
                prompt=PROMPT,
                style="pony",
                negative_prompt=NEGATIVE,
                loras=loras,
                width=832,
                height=480,
                steps=28,
                cfg=6.0,
                seed=int(v["seed"]),
                denoising_strength=float(v["denoise"]),
                sampler="euler_ancestral",
                scheduler="normal",
                face_detail=False,
            )
            dest = PROJECT_DIR / f"Rin_clip1_kunai_{tag}.png"
            shutil.copy2(Path(result["saved_files"][0]), dest)
            runs.append({**v, "delivered": str(dest), "lora": LORA_FILE, "lora_weight": LORA_WEIGHT})

        payload = {
            "status": "success",
            "source_frame": str(FRAME0),
            "lora": {"file": LORA_FILE, "version_id": LORA_VERSION, "weight": LORA_WEIGHT},
            "prompt": PROMPT,
            "runs": runs,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_clip1_kunai_lora_i2i.json")
        shutil.copy2(MCP_ROOT / "outputs" / "tools_needed.json", P.LOGS / "tools_needed.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
