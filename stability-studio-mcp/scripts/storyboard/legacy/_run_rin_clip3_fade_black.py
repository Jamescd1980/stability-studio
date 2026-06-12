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

"""Post: fade clip 3 to black on final frames (I2V rarely hits 'screen goes dark')."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import comfy_python, imageio_ffmpeg

import rin_project_paths as P

P.ensure_layout()
PROJECT_DIR = P.ROOT
SOURCE = P.CLIPS / "Rin_clip3_stab.mp4"
BACKUP = P.CLIPS / "Rin_clip3_stab_nofade.mp4"
OUT = P.CLIP3_STAB_FADE
LOG = P.LOGS / "rin_clip3_fade_black.json"

FFMPEG = imageio_ffmpeg()
FADE_START_S = 2.35
FADE_DURATION_S = 0.71


def probe_duration(path: Path) -> float:
    ff = str(FFMPEG) if FFMPEG.is_file() else "ffmpeg"
    proc = subprocess.run([ff, "-i", str(path)], capture_output=True, text=True)
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            part = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = part.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not probe duration: {path}")


def main() -> int:
    if not SOURCE.is_file():
        print(f"Missing {SOURCE}", file=sys.stderr)
        return 1

    duration = probe_duration(SOURCE)
    fade_start = max(0.0, duration - FADE_DURATION_S)
    if fade_start < 0.5:
        fade_start = max(0.0, duration * 0.65)
        fade_dur = duration - fade_start
    else:
        fade_dur = FADE_DURATION_S

    src = BACKUP if BACKUP.is_file() else SOURCE
    if not BACKUP.is_file():
        shutil.copy2(SOURCE, BACKUP)

    ff = str(FFMPEG) if FFMPEG.is_file() else "ffmpeg"
    vf = f"fade=t=out:st={fade_start:.3f}:d={fade_dur:.3f}:color=black"
    subprocess.run(
        [ff, "-y", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-an", str(OUT)],
        check=True,
        capture_output=True,
    )

    payload = {
        "status": "success",
        "source_duration_s": duration,
        "fade_start_s": fade_start,
        "fade_duration_s": fade_dur,
        "backup": str(BACKUP),
        "delivered": str(OUT),
    }
    LOG.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (MCP_ROOT / "outputs" / "rin_clip3_fade_black.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
