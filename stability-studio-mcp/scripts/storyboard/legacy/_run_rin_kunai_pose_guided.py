#!/usr/bin/env python3
"""Clip2 chain frame + OpenPose skeleton → kunai in hand (pose-guided Pony i2i)."""
from __future__ import annotations

import json
import shutil
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
import rin_project_paths as P

P.ensure_layout()
PROJECT_DIR = P.ROOT
SOURCE = P.CLIP1_LAST
POSE_CANDIDATES = [
    PROJECT_DIR / "Rin_kunai_pose_openpose.png",
    PROJECT_DIR / "Rin_bow_kunai_pose.png",
    PROJECT_DIR / "kunai_pose.png",
]

LORA_FILE = "concept_povholding-pony-v2.safetensors"
LORA_VERSION = 492190

PROMPT = (
    "score_9, score_8_up, score_7_up, source_anime, rating_explicit, high_quality, detailed, "
    "1girl, solo, kitsune, fox_girl, white_hair, fox_ears, fox_tail, red_eyes, "
    "military_uniform, peaked_cap, cherry_blossoms, outdoors, "
    "holding_kunai, kunai, holding_weapon, reverse_grip, arm_at_side, "
    "anatomically_correct_hands, five_fingers, looking_at_viewer, upper_body"
)

NEGATIVE = (
    "holding_sword, sword, katana, holding_katana, greatsword, dual_wielding, scabbard, "
    "briefcase, bag, satchel, bad_hands, extra_fingers, missing_fingers, blurry, lowres"
)

VARIANTS = [
    {
        "tag": "pose_d036",
        "denoise": 0.36,
        "openpose": 0.84,
        "seed": 424271,
        "lora_weight": 0.0,
    },
    {
        "tag": "pose_lora_d034",
        "denoise": 0.34,
        "openpose": 0.82,
        "seed": 424272,
        "lora_weight": 0.65,
    },
]


def resolve_pose() -> Path:
    for p in POSE_CANDIDATES:
        if p.is_file() and p.stat().st_size > 500:
            return p
    extra = sorted(PROJECT_DIR.glob("*pose*.png"))
    for p in extra:
        if p.stat().st_size > 500:
            return p
    raise FileNotFoundError(
        "No pose PNG found. Export from https://openpose-editor.vercel.app/ at 832×480 "
        f"and save as: {POSE_CANDIDATES[0]}"
    )


def ensure_lora(cfg) -> None:
    from studio.civitai_download import download_civitai_lora

    download_civitai_lora(
        cfg,
        filename=LORA_FILE,
        version_id=LORA_VERSION,
        force=False,
    )


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_kunai_pose_guided.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine
        from studio.pose_control import check_pose_control_readiness

        if not SOURCE.is_file():
            raise FileNotFoundError(SOURCE)

        cfg = load_config()
        comfy_url = cfg.get("comfyui_url", "http://127.0.0.1:8188")
        readiness = check_pose_control_readiness(cfg, comfy_url)
        if not readiness.get("ready_for_pose_i2i"):
            raise RuntimeError(f"Pose control not ready: {json.dumps(readiness, indent=2)}")

        pose_path = resolve_pose()
        print(f"Pose skeleton: {pose_path}", flush=True)

        requests.get(f"{comfy_url}/system_stats", timeout=60)
        requests.post(
            f"{comfy_url}/free",
            json={"unload_models": True, "free_memory": True},
            timeout=120,
        )

        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 3.0
        ensure_lora(cfg)

        engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
        runs = []
        for v in VARIANTS:
            tag = str(v["tag"])
            loras = None
            if float(v["lora_weight"]) > 0:
                loras = [{"name": LORA_FILE, "weight": float(v["lora_weight"])}]
            print(
                f"=== {tag} denoise={v['denoise']} openpose={v['openpose']} "
                f"lora={v['lora_weight']} ===",
                flush=True,
            )
            result = engine.generate_image_pose_guided(
                image_path=str(SOURCE),
                pose_image_path=str(pose_path),
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
                openpose_strength=float(v["openpose"]),
                preprocess_pose=False,
                sampler="euler_ancestral",
                scheduler="normal",
            )
            dest = PROJECT_DIR / f"Rin_kunai_{tag}.png"
            shutil.copy2(Path(result["saved_files"][0]), dest)
            runs.append({**v, "delivered": str(dest), "pose": str(pose_path)})

        payload = {
            "status": "success",
            "source": str(SOURCE),
            "pose": str(pose_path),
            "readiness": readiness,
            "prompt": PROMPT,
            "runs": runs,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_kunai_pose_guided.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
