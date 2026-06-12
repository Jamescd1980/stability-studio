#!/usr/bin/env python3
"""Split Rin dialogue into 3 MOSS voice_design clips for Infinitetalk lip-sync."""
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

INSTRUCTION = (
    "young woman, early twenties, softer breathy voice, gentle and delicate, "
    "noticeable soft Japanese accent, polite respectful, intimate close-mic"
)
SEED = 551122

CHUNKS = [
    {
        "id": "01_greetings",
        "text": "Greetings.",
        "duration_seconds": 2.5,
        "filename": "Rin_dialogue_01_greetings.mp3",
        "prefix": "audio/rin_dialogue_01_greetings",
    },
    {
        "id": "02_rin_father",
        "text": "My name is Rin, you killed my father.",
        "duration_seconds": 4.0,
        "filename": "Rin_dialogue_02_rin_father.mp3",
        "prefix": "audio/rin_dialogue_02_rin_father",
    },
    {
        "id": "03_prepare_die",
        "text": "Now prepare to die.",
        "duration_seconds": 2.5,
        "filename": "Rin_dialogue_03_prepare_die.mp3",
        "prefix": "audio/rin_dialogue_03_prepare_die",
    },
]


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
    out_log = MCP_ROOT / "outputs" / "rin_dialogue_chunks.json"
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

        runs: list[dict] = []
        for chunk in CHUNKS:
            print(f"\n=== {chunk['id']}: {chunk['text']!r} ===", flush=True)
            result = engine.generate_audio(
                mode="voice_design",
                text=str(chunk["text"]),
                instruction=INSTRUCTION,
                language="en",
                duration_seconds=float(chunk["duration_seconds"]),
                seed=SEED,
                filename_prefix=str(chunk["prefix"]),
            )
            saved = [Path(p) for p in (result.get("saved_files") or [])]
            if not saved:
                raise RuntimeError(f"No audio for {chunk['id']}")
            dest = P.AUDIO / str(chunk["filename"])
            shutil.copy2(saved[0], dest)
            runs.append(
                {
                    **chunk,
                    "delivered": str(dest),
                    "metrics": _analyze(dest),
                    "mcp_copy": str(saved[0]),
                }
            )

        payload = {"status": "success", "instruction": INSTRUCTION, "seed": SEED, "chunks": runs}
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, P.LOGS / "rin_dialogue_chunks.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
