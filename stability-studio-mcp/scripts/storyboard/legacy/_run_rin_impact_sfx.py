#!/usr/bin/env python3
"""MOSS SFX — Rin stab impact + body on stone (A/B/C each)."""
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

STAB_VARIANTS = [
    {
        "label": "A",
        "prompt": "sharp knife thrust impact close up, single sudden stab hit",
        "seed": 751101,
        "duration": 2.0,
    },
    {
        "label": "B",
        "prompt": "metal blade piercing impact, quick close stab sound",
        "seed": 751202,
        "duration": 2.0,
    },
    {
        "label": "C",
        "prompt": "kunai blade stab impact sudden and close, single hit",
        "seed": 751303,
        "duration": 2.5,
    },
]

BODY_VARIANTS = [
    {
        "label": "A",
        "prompt": "body falling and hitting stone pavement, dull heavy thud",
        "seed": 852101,
        "duration": 3.0,
    },
    {
        "label": "B",
        "prompt": "human body collapse onto stone walkway, single impact",
        "seed": 852202,
        "duration": 3.0,
    },
    {
        "label": "C",
        "prompt": "heavy fall onto stone path, body hitting ground once",
        "seed": 852303,
        "duration": 3.5,
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


def _generate_batch(
    engine,
    delivery_dir: Path,
    *,
    kind: str,
    variants: list[dict],
) -> list[dict]:
    results: list[dict] = []
    for v in variants:
        label = str(v["label"])
        prompt = str(v["prompt"])
        seed = int(v["seed"])
        duration = float(v["duration"])
        print(f"\n=== {kind} {label} ===\n{prompt}\n", flush=True)
        result = engine.generate_audio(
            mode="sound_effect",
            prompt=prompt,
            duration_seconds=duration,
            seed=seed,
            filename_prefix=f"audio/rin_{kind}_{label.lower()}",
        )
        saved = Path(result["saved_files"][0])
        dest = delivery_dir / f"Rin_{kind}_option_{label}.mp3"
        shutil.copy2(saved, dest)
        metrics = _analyze(saved)
        results.append({
            "label": label,
            "prompt": prompt,
            "seed": seed,
            "duration_requested": duration,
            "metrics": metrics,
            "delivered": str(dest),
            "mcp_copy": str(saved),
        })
        print(f"Saved: {dest} ({metrics['duration_s']:.1f}s)", flush=True)
    return results


def main() -> int:
    out_log = MCP_ROOT / "outputs" / "rin_impact_sfx_batch.json"
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

        delivery_dir = PROJECT_DIR

        stab = _generate_batch(engine, delivery_dir, kind="stab", variants=STAB_VARIANTS)
        body = _generate_batch(engine, delivery_dir, kind="body_hit", variants=BODY_VARIANTS)

        payload = {
            "status": "success",
            "project_dir": str(PROJECT_DIR),
            "stab": stab,
            "body_hit": body,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, PROJECT_DIR / "rin_impact_sfx_batch.json")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
