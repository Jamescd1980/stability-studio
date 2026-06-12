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

"""Post: fade clip 3 talk, mix SFX, concat Rin storyboard."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from _env import comfy_python, imageio_ffmpeg

import rin_project_paths as P

P.ensure_layout()
PROJECT = P.ROOT
LOG = P.LOGS / "rin_storyboard_mux.json"

FFMPEG = imageio_ffmpeg()

CLIP1 = P.CLIPS / "Rin_clip1_walk_talk.mp4"
CLIP2 = P.CLIPS / "Rin_clip2_bow_talk.mp4"
CLIP3 = P.CLIPS / "Rin_clip3_stab_talk.mp4"
CLIP3_FADE = P.CLIPS / "Rin_clip3_stab_talk_fade.mp4"
CLIP1_MIX = P.FINAL / "Rin_clip1_walk_final.mp4"
CLIP3_MIX = P.FINAL / "Rin_clip3_stab_final.mp4"
FINAL = P.FINAL / "Rin_storyboard_full.mp4"

AMBIENT = P.AMBIENT
FOOTSTEPS = P.FOOTSTEPS
STAB = P.STAB_SFX
BODY = P.BODY_HIT


def ff() -> str:
    return str(FFMPEG) if FFMPEG.is_file() else "ffmpeg"


def probe_duration(path: Path) -> float:
    proc = subprocess.run([ff(), "-i", str(path)], capture_output=True, text=True)
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            part = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = part.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not probe: {path}")


def fade_clip3() -> dict:
    duration = probe_duration(CLIP3)
    fade_dur = min(0.71, max(0.45, duration * 0.28))
    fade_start = max(0.0, duration - fade_dur)
    vf = f"fade=t=out:st={fade_start:.3f}:d={fade_dur:.3f}:color=black"
    subprocess.run(
        [ff(), "-y", "-i", str(CLIP3), "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "copy", str(CLIP3_FADE)],
        check=True,
        capture_output=True,
    )
    return {"source": str(CLIP3), "duration_s": duration, "fade_start_s": fade_start, "fade_duration_s": fade_dur, "out": str(CLIP3_FADE)}


def mix_clip1() -> dict:
    dur = probe_duration(CLIP1)
    # Ambient bed + footsteps under dialogue (clip already has voice from Infinitetalk).
    filter_complex = (
        f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{dur:.3f},volume=0.35[amb];"
        f"[2:a]atrim=0:{dur:.3f},volume=0.55[steps];"
        f"[0:a][amb][steps]amix=inputs=3:duration=first:dropout_transition=0[aout]"
    )
    subprocess.run(
        [
            ff(), "-y",
            "-i", str(CLIP1),
            "-i", str(AMBIENT),
            "-i", str(FOOTSTEPS),
            "-filter_complex", filter_complex,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(CLIP1_MIX),
        ],
        check=True,
        capture_output=True,
    )
    return {"duration_s": dur, "out": str(CLIP1_MIX)}


def mix_clip3() -> dict:
    dur = probe_duration(CLIP3_FADE)
    stab_at = max(0.0, dur * 0.42)
    body_at = max(0.0, dur * 0.62)
    filter_complex = (
        f"[1:a]adelay={int(stab_at * 1000)}|{int(stab_at * 1000)},volume=1.1[stab];"
        f"[2:a]adelay={int(body_at * 1000)}|{int(body_at * 1000)},volume=0.95[body];"
        f"[0:a][stab][body]amix=inputs=3:duration=first:dropout_transition=0[aout]"
    )
    subprocess.run(
        [
            ff(), "-y",
            "-i", str(CLIP3_FADE),
            "-i", str(STAB),
            "-i", str(BODY),
            "-filter_complex", filter_complex,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(CLIP3_MIX),
        ],
        check=True,
        capture_output=True,
    )
    return {"duration_s": dur, "stab_at_s": stab_at, "body_at_s": body_at, "out": str(CLIP3_MIX)}


def concat_final() -> dict:
    list_file = PROJECT / "_concat_list.txt"
    list_file.write_text(
        "\n".join(
            f"file '{p.resolve().as_posix()}'"
            for p in (CLIP1_MIX, CLIP2, CLIP3_MIX)
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [ff(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(FINAL)],
        check=True,
        capture_output=True,
    )
    return {"clips": [str(CLIP1_MIX), str(CLIP2), str(CLIP3_MIX)], "out": str(FINAL), "duration_s": probe_duration(FINAL)}


def main() -> int:
    for p in (CLIP1, CLIP2, CLIP3, AMBIENT, FOOTSTEPS, STAB, BODY):
        if not p.is_file():
            print(f"Missing {p}", file=sys.stderr)
            return 1

    payload = {
        "status": "success",
        "fade_clip3": fade_clip3(),
        "mix_clip1": mix_clip1(),
        "mix_clip3": mix_clip3(),
        "concat": concat_final(),
    }
    LOG.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    import shutil
    shutil.copy2(LOG, PROJECT / "rin_storyboard_mux.json")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
