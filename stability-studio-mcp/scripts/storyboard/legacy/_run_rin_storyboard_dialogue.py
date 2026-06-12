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

"""Generate Rin storyboard dialogue with approved v4 voice."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEXT = (
    "Greetings, my name is Rin, you killed my father, now prepare to die."
)
INSTRUCTION = (
    "young woman, early twenties, softer breathy voice, gentle and delicate, "
    "noticeable soft Japanese accent, polite respectful, intimate close-mic"
)
SEED = 551122
DURATION_SECONDS = 9.0
PREFIX = "audio/rin_storyboard_dialogue_ja"


def _analyze(path: Path) -> dict:
    py = comfy_python()
    script = r"""
import json, sys
from pathlib import Path
import librosa, numpy as np
p = Path(sys.argv[1])
y, sr = librosa.load(p, sr=None, mono=True)
rms = float(np.sqrt(np.mean(y**2))) if len(y) else 0.0
print(json.dumps({"duration_s": len(y)/sr if sr else 0, "rms": rms, "size": p.stat().st_size}))
"""
    out = subprocess.run([str(py), "-c", script, str(path)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip())


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_storyboard_dialogue.json"
    try:
        import studio.audio_post as audio_post
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        audio_post.trim_leading_trailing_silence = lambda path, cfg, **kw: path  # type: ignore[assignment]

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 3.0
        cat = StyleCatalog(catalog_path(cfg), cfg)
        engine = GenerationEngine(cfg, cat)
        if not engine.comfy.is_running():
            raise RuntimeError("ComfyUI must be running for MOSS voice_design")

        print("Generating Rin dialogue...", flush=True)
        result = engine.generate_audio(
            mode="voice_design",
            text=TEXT,
            instruction=INSTRUCTION,
            language="en",
            duration_seconds=DURATION_SECONDS,
            seed=SEED,
            filename_prefix=PREFIX,
        )
        saved = [Path(p) for p in (result.get("saved_files") or [])]
        if not saved or not saved[0].is_file():
            raise RuntimeError(f"MOSS finished but no audio on disk: {saved}")

        delivery_name = "Rin_dialogue_line.mp3"
        delivery_dir = Path(cfg.get("outputs", {}).get("delivery") or MCP_ROOT / "outputs")
        delivery_dir.mkdir(parents=True, exist_ok=True)
        delivery_path = delivery_dir / delivery_name
        shutil.copy2(saved[0], delivery_path)
        if not delivery_path.is_file() or delivery_path.stat().st_size < 1000:
            raise RuntimeError(f"Delivery copy failed or too small: {delivery_path}")

        metrics = _analyze(saved[0])
        payload = {
            "status": "success",
            "character": "Rin",
            "storyboard": "kitsune_kuni_stab",
            "text": TEXT,
            "instruction": INSTRUCTION,
            "seed": SEED,
            "duration_seconds": DURATION_SECONDS,
            "voice_reference": "kitsune_bow_greeting_v4 + soft Japanese accent",
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
