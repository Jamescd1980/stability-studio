#!/usr/bin/env python3
"""MOSS SFX — Rin stab v2 (new prompt strategies after v1 rejected)."""
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

# Avoid literal stab/knife wording — v1 sounded like weird noise.
VARIANTS = [
    {
        "label": "A",
        "prompt": "short sharp foley impact close to the ear, single sudden hit",
        "seed": 961101,
        "duration": 1.5,
    },
    {
        "label": "B",
        "prompt": "blade slash whoosh followed by a quick soft impact close up",
        "seed": 961202,
        "duration": 2.0,
    },
    {
        "label": "C",
        "prompt": "quick metallic strike impact sudden and close, single hit",
        "seed": 961303,
        "duration": 1.5,
    },
    {
        "label": "D",
        "prompt": "sharp object rushing forward then hitting with a brief wet thud",
        "seed": 961404,
        "duration": 2.0,
    },
]


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
    out_log = MCP_ROOT / "outputs" / "rin_stab_sfx_v2_batch.json"
    try:
        import requests
        from studio.config import load_config, catalog_path
        from studio.catalog import StyleCatalog
        from studio.engine import GenerationEngine

        PROJECT_DIR.mkdir(parents=True, exist_ok=True)
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

        results: list[dict] = []
        for v in VARIANTS:
            label = str(v["label"])
            prompt = str(v["prompt"])
            seed = int(v["seed"])
            duration = float(v["duration"])
            print(f"\n=== stab v2 {label} ===\n{prompt}\n", flush=True)
            result = engine.generate_audio(
                mode="sound_effect",
                prompt=prompt,
                duration_seconds=duration,
                seed=seed,
                filename_prefix=f"audio/rin_stab_v2_{label.lower()}",
            )
            saved = Path(result["saved_files"][0])
            dest = PROJECT_DIR / f"Rin_stab_v2_option_{label}.mp3"
            shutil.copy2(saved, dest)
            metrics = _analyze(saved)
            results.append({
                "label": label,
                "prompt": prompt,
                "seed": seed,
                "metrics": metrics,
                "delivered": str(dest),
            })
            print(f"Saved: {dest} ({metrics['duration_s']:.1f}s)", flush=True)

        payload = {
            "status": "success",
            "note": "v2 — avoided knife/stab keywords; v1 A/B/C rejected",
            "variants": results,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_stab_sfx_v2_batch.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
