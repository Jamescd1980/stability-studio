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

"""Generate Rin scene background ambient (breeze + leaves) via MOSS sound_effect."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROMPT = (
    "very light breeze, soft leaves gently rustling in tree canopy above, "
    "quiet outdoor Japanese garden, subtle airy ambience, calm and still, "
    "delicate foliage whisper, no strong wind, no gust, no whoosh, no voices, no music"
)
DURATION_SECONDS = 6.0
SEED = 882901
PREFIX = "audio/rin_ambient_breeze_v2"


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
    out_log = MCP_ROOT / "outputs" / "rin_ambient_breeze_sfx_v2.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        requests.post(
            "http://127.0.0.1:8188/free",
            json={"unload_models": True, "free_memory": True},
            timeout=60,
        )

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 0.05
        cat = StyleCatalog(catalog_path(cfg), cfg)
        engine = GenerationEngine(cfg, cat)
        if not engine.comfy.is_running():
            raise RuntimeError("ComfyUI must be running for MOSS sound_effect")

        print("Generating ambient SFX...", flush=True)
        result = engine.generate_audio(
            mode="sound_effect",
            prompt=PROMPT,
            duration_seconds=DURATION_SECONDS,
            seed=SEED,
            filename_prefix=PREFIX,
        )
        saved = [Path(p) for p in (result.get("saved_files") or [])]
        if not saved or not saved[0].is_file():
            raise RuntimeError(f"MOSS finished but no audio on disk: {saved}")

        delivery_name = "Rin_ambient_breeze_6s.mp3"
        delivery_dir = Path(cfg.get("outputs", {}).get("delivery") or MCP_ROOT / "outputs")
        delivery_dir.mkdir(parents=True, exist_ok=True)
        delivery_path = delivery_dir / delivery_name
        shutil.copy2(saved[0], delivery_path)

        metrics = _analyze(saved[0])
        payload = {
            "status": "success",
            "prompt": PROMPT,
            "duration_seconds": DURATION_SECONDS,
            "seed": SEED,
            "vram_note": "6s length is fine on 16GB; MOSS-SoundEffect ~18GB model load is the constraint",
            "metrics": metrics,
            "mcp_copy": str(saved[0]),
            "delivered": str(delivery_path),
            "result": result,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        print(f"\nPLAY THIS FILE: {delivery_path}", flush=True)
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
