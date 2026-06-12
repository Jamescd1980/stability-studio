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

"""Batch MOSS SFX — simple OpenMOSS-style prompts for breeze/leaves."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Short, concrete, positive-only (OpenMOSS model card examples).
VARIANTS: list[dict[str, str | int | float]] = [
    {
        "label": "A",
        "prompt": "early morning park with light birds chirping and a gentle breeze",
        "seed": 120401,
    },
    {
        "label": "B",
        "prompt": "gentle breeze rustling through dry leaves in trees",
        "seed": 220502,
    },
    {
        "label": "C",
        "prompt": "soft wind blowing through tree leaves in a quiet garden",
        "seed": 320603,
    },
]
DURATION_SECONDS = 8.0


def _analyze(path: Path) -> dict:
    py = comfy_python()
    script = r"""
import json, sys
from pathlib import Path
import librosa
p = Path(sys.argv[1])
y, sr = librosa.load(p, sr=None, mono=True)
rms = float((y**2).mean()**0.5) if len(y) else 0.0
print(json.dumps({"duration_s": len(y)/sr if sr else 0, "rms": rms, "size": p.stat().st_size}))
"""
    out = subprocess.run([str(py), "-c", script, str(path)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip())


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_ambient_breeze_sfx_batch.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        requests.post(
            "http://127.0.0.1:8188/free",
            json={"unload_models": True, "free_memory": True},
            timeout=120,
        )

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 0.05
        cat = StyleCatalog(catalog_path(cfg), cfg)
        engine = GenerationEngine(cfg, cat)
        if not engine.comfy.is_running():
            raise RuntimeError("ComfyUI must be running for MOSS sound_effect")

        delivery_dir = Path(cfg.get("outputs", {}).get("delivery") or MCP_ROOT / "outputs")
        delivery_dir.mkdir(parents=True, exist_ok=True)

        results: list[dict] = []
        for v in VARIANTS:
            label = str(v["label"])
            prompt = str(v["prompt"])
            seed = int(v["seed"])
            print(f"\n=== Variant {label} ===\n{prompt}\n", flush=True)
            result = engine.generate_audio(
                mode="sound_effect",
                prompt=prompt,
                duration_seconds=DURATION_SECONDS,
                seed=seed,
                filename_prefix=f"audio/rin_ambient_{label.lower()}",
            )
            saved = Path(result["saved_files"][0])
            dest = delivery_dir / f"Rin_ambient_option_{label}.mp3"
            shutil.copy2(saved, dest)
            metrics = _analyze(saved)
            entry = {
                "label": label,
                "prompt": prompt,
                "seed": seed,
                "metrics": metrics,
                "delivered": str(dest),
                "mcp_copy": str(saved),
            }
            results.append(entry)
            print(f"Saved: {dest} ({metrics['duration_s']:.1f}s)", flush=True)

        payload = {
            "status": "success",
            "duration_requested": DURATION_SECONDS,
            "note": "OpenMOSS-style short prompts; pick best option A/B/C",
            "variants": results,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
